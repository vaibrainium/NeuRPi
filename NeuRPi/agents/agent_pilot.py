import importlib
import logging
import multiprocessing as mp
import os
import sys
import threading
import time
from pathlib import Path
import pickle
import types

from NeuRPi.loggers.logger import init_logger
from NeuRPi.networking import Net_Node, Pilot_Station
from NeuRPi.prefs import prefs
from NeuRPi.utils.get_config import get_configuration


class Pilot:
    logger = None

    # Events for thread handling
    running = None
    stage_block = None
    stopping = None

    # networking
    node = None
    networking = None

    def __init__(self): 

        self.name = prefs.get("NAME")
        if prefs.get("LINEAGE") == "CHILD":
            self.child = True
            self.parentid = prefs.get("PARENTID")
        else:
            self.child = False
            self.parentid = "T"

        self.logger = init_logger(self)
        self.logger.debug("pilot logger initialized")

        # Locks, etc. for threading
        self.stage_block = threading.Event()  # Are we waiting on stage triggers?
        self.running = threading.Event()  # Are we running a task?
        self.stopping = threading.Event()
        self.stopping.clear()

        # initialize listens dictionary
        self.listens = {
            "START": self.l_start,
            "STOP": self.l_stop,
            "PARAM": self.l_param,
            "EVENT": self.l_event,
        }

        # initialize station and node
        self.networking = Pilot_Station()
        self.networking.start()
        self.node = Net_Node(
            id="_{}".format(self.name),
            upstream=self.name,
            port=int(prefs.get("MSGPORT")),
            listens=self.listens,
            instance=False,
        )
        self.logger.debug("pilot networking initialized")

        # set and update state
        self.state = "IDLE"  # or 'Running'
        self.update_state()

        # handshake on initialization
        self.ip = self.networking.get_ip()
        if self.varify_hardware_connectivity():
            self.handshake()
            self.logger.debug("handshake sent")
        else: 
            raise TimeoutError("Hardware is not connected. Please check hardware connectivity and try again.")

        self.task = None
        self.stimulus_display = None

        # initialize default variables required for any task
        self.session_info = None
        self.session_config = None
        self.subject_config = None
        self.handware_manager = None
        self.task_manager = None
        self.stimulus_manager = None
        self.display_process = None

        self.modules = None

    ############################### HANDSHAKE FUNCTIONS ########################################        

    def varify_hardware_connectivity(self):
        """
        Check if all required hardwares mentioned in prefs is connected to the rig 
        """
        # TODO: start implementing pre-emptive check on hardware connectivity before sending handshake so that terminal has better idea whether the rig is ready to run the specific task or not
        return True

    def handshake(self):
        hello = {
            "pilot": self.name,
            "ip": self.ip,
            "state": self.state,
            "prefs": prefs.get(),
        }
        self.node.send(self.parentid, "HANDSHAKE", value=hello)

    def update_state(self):
        """
        Send current state to terminal
        """
        self.node.send(self.name, "STATE", self.state, flags={"NOLOG": True})

    ############################### LISTEN FUNCTIONS ########################################

    def l_start(self, value):
        """
        Terminal requested to start running the task

        Args:
            value (dict): protocol parameters
        """

        if self.state == "RUNNING" or self.running.is_set():
            self.logger.warning("Task already running. Cannot start new task")
            return

        # Required parameteres from terminal to start task
        try:
            self.session_info = value["session_info"]
            self.subject_config = value["subject_config"]
            self.session_config = self.convert_str_to_module(value["session_config"])
        except KeyError as e:
            self.logger.exception(f"Missing required parameter: {e}")
            return

        self.import_session_modules()

        try:
            if "Display" in self.session_config.REQUIRED_HARDWARE:
                stimulus_config = self.session_config.STIMULUS.copy()
                value["msg_to_stimulus"] = mp.Queue()
                value["queue_from_stimulus"] = mp.Queue()

                self.display_process = mp.Process(
                    target=self.start_display,
                    kwargs={
                        'StimulusDisplay': self.modules['stimulus'],
                        'config': stimulus_config,
                        'in_queue': value["msg_to_stimulus"],
                        'out_queue': value["queue_from_stimulus"],
                    }
                )
                self.display_process.start()
                # wait for the display to start before starting the task process
                message = value["queue_from_stimulus"].get(timeout=5)
                if message != "display_connected":
                    raise TimeoutError("Display did not start in time")
                else:
                    self.logger.info("Display started")
                
            threading.Thread(target=self.run_task, args=(value,)).start()
            self.state = "RUNNING"
            self.running.set()
            self.update_state()


        except Exception as e:
           self.logger.exception(f"Could not start Task: {e}")
           return

    def l_stop(self, value):
        """
        Terminal requested to stop the task
        Clearing all running events and set stage_block

        Args:
            value: Ignored for now. Might implement in future to match terminal and pilot data
        """
        # Letting terminal know that we are stopping task
        self.running.clear()
        self.stopping.set()

        self.state = "IDLE"
        self.update_state()

    def l_param(self, value):
        """
        Terminal is sending an update.
        """
        # TODO: write code to forward updated task parameters to rig
        pass

    def l_event(self, value):
        """
        Terminal is sending an event passed from task
        """
        if value["key"] == "PAUSE":
            self.running.clear()
            self.state == "PAUSED"
            self.update_state()
        elif value["key"] == "RESUME":
            self.running.set()
            self.state == "RUNNING"
            self.update_state()

        elif value["key"] == "HARDWARE":
            if self.task:
                self.task.manage_hardware(value["value"])

    ############################### SECONDARY FUNCTIONS ########################################
    def convert_str_to_module(self, module_string):

        """
        Convert string to module
        """
        module_name = "session_config"
        session_config = types.ModuleType(module_name)
        exec(module_string, session_config.__dict__)
        return session_config


    def import_session_modules(self):
        """
        Import task module and initialize hardware, stimulus and task managers.
        Required for any task to run on the rig and should be called before starting the task.
        """

        # TODO: In future version, separate the move task phase one level up and keep all required modules inside for easier readability

        # import all required modules
        try:        
            hardware_manager_file = importlib.import_module(f"protocols.{self.session_info.protocol}.hardware.hardware_manager")
            task_manager_file = importlib.import_module(f"protocols.{self.session_info.protocol}.tasks.{self.session_info.experiment}")
            stimulus_manager_file = importlib.import_module(f"protocols.{self.session_info.protocol}.stimulus.{self.session_info.experiment}")
            
            self.modules = {}
            self.modules["task"] = task_manager_file.Task
            self.modules["hardware"] = hardware_manager_file.HardwareManager
            self.modules["stimulus"] = stimulus_manager_file.StimulusDisplay
        except ImportError as e:
            self.logger.exception(f"Could not import module: {e}")
                        
    def start_display(self, StimulusDisplay, config, in_queue, out_queue):
        """
        Current task requires display hardware. Import display module and start display process.
        
        """
        # stimulus_manager_file = importlib.import_module(f"protocols.{self.session_info.protocol}.stimulus.{self.session_info.experiment}")
        # display = stimulus_manager_file.StimulusDisplay(
        display = StimulusDisplay(
            stimulus_configuration=config,
            in_queue=in_queue,
            out_queue=out_queue,
        )
        display.start()

    def run_task(self, task_params):
        """
        start running task under new thread
        initiate the task, and progress through each stage of task with `task.stages.next`
        send data to terminal after every stage
        waits for the task to clear `stage_block` between stages

        """
        self.logger.debug("initialing task")
        self.stage_block.clear()

        self.config = self.session_config
        self.config.SUBJECT = self.subject_config

        self.task = self.modules['task'](
            stage_block=self.stage_block, config=self.config, **task_params
        )
        self.logger.debug("task initialized")

        # TODO: Initialize sending continuous data here
        self.logger.debug("Starting task loop")
        try:
            while True:
                # Calculate next stage data and prepare triggers
                data = next(self.task.stages)()
                self.logger.debug("called stage method")

                # Waiting for stage block to clear
                self.stage_block.wait()
                self.logger.debug("stage block passed")

                if data:
                    data["pilot"] = self.name
                    data["subject"] = self.session_info.subject_name

                    # send data back to terminal
                    self.node.send("T", "DATA", data)

                # pause loop if the running flag is not set and current trial has ended.
                if not self.running.is_set() and "TRIAL_END" in data.keys():
                    # exit loop if stopping flag is set
                    if self.stopping.is_set():
                        self.display_process.kill()       
                        self.task.end_session()  
                        #TODO: Make better arrangement of the code so that files will be sent only on termination of program. Not on crashing
                        try:
                            # sending files to terminal only when successfully finished the task
                            value = {
                                "pilot": self.name,
                                "subject": self.session_info.subject_name,
                                "session_files": {}
                            }
                            for file_name, file_path in self.config.FILES.items():
                                    # if False: #"rolling_perf" in file_name:
                                    #     with open(file_path, "rb") as reader:
                                    #         value["session_files"][file_name] = pickle.load(reader)
                                    # else:
                                with open(file_path, "rb") as reader:
                                    value["session_files"][file_name] = reader.read()
                            self.node.send("T", "SESSION_FILES", value)         
                        except:
                            self.logger.exception("Could not send files to terminal")    
                        break

                    # if paused, wait for running event set?
                    self.running.wait()

        except Exception as e:
            self.logger.exception(
                f"got exception while running task; stopping task\n {e}"
            )
            print("GOT Exception")

        finally:
            self.logger.debug("stopping task")
            try:
                pass
                # self.task.end_session()  
            except Exception as e:
                self.logger.exception(f"got exception while stopping task: {e}")
            del self.task
            self.task = None
            self.logger.debug("task stopped")


def main():
    quitting = threading.Event()
    quitting.clear()
    try:
        pi = Pilot()
        pi.handshake()

        msg = {
            "subjectID": "XXX",
            "protocol": "rt_dynamic_training",
            "experiment": "4",
        }
        quitting.wait()

    except KeyboardInterrupt:
        quitting.set()
        sys.exit()


if __name__ == "__main__":
    # main()

    from omegaconf import OmegaConf

    dicto = OmegaConf.create()
