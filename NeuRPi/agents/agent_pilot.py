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
            self.config = self.convert_str_to_module(value["session_config"])
            self.config.SUBJECT = value["subject_config"]

            # import task module
            task_module = importlib.import_module(f"protocols.{self.session_info.protocol}.{self.session_info.experiment}.task")
            self.stage_block.clear()
            self.task = task_module.Task(stage_block=self.stage_block, config=self.config, **value)
            init_successful = self.task.initialize()
            if not init_successful:
                self.logger.error("Task initialization failed")
            else:
                self.logger.debug("task initialized")
                self.state = "INITIALIZED"
                self.update_state()
                threading.Thread(target=self.run_task, args=(value,)).start()
        except KeyError as e:
            self.state = "ERROR"
            self.update_state()
            self.logger.exception(f"Missing required parameter: {e}")
        except Exception as e:
            self.state = "ERROR"
            self.update_state()
            self.logger.exception(f"Could not initialize task: {e}")

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
                self.task.handle_terminal_request(value["value"])

    ############################### SECONDARY FUNCTIONS ########################################
    def convert_str_to_module(self, module_string):
        """
        Convert string to module
        """
        module_name = "session_config"
        session_config = types.ModuleType(module_name)
        exec(module_string, session_config.__dict__)
        return session_config

    def run_task(self, value):
        """
        start running task under new thread
        initiate the task, and progress through each stage of task with `task.stages.next`
        send data to terminal after every stage
        waits for the task to clear `stage_block` between stages

        """
        self.logger.debug("Starting task loop")
        self.state = "RUNNING"
        self.running.set()
        self.update_state()

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
                        self.stopping.clear()
                        self.task.end()
                        try:
                            # sending files to terminal only when successfully finished the task
                            value = {"pilot": self.name, "subject": self.session_info.subject_name, "session_files": {}}
                            for file_name, file_path in self.config.FILES.items():
                                with open(file_path, "rb") as reader:
                                    value["session_files"][file_name] = reader.read()
                            self.node.send("T", "SESSION_FILES", value, flags={"NOLOG": True})
                        except:
                            self.logger.exception("Could not send files to terminal")
                        break

                    # if paused, wait for running event set?
                    self.running.wait()

        except Exception as e:
            self.logger.exception(f"got exception while running task; stopping task\n {e}")
            print("GOT Exception")

        finally:
            self.logger.debug("stopping task")
            try:
                pass
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
