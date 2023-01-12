import importlib
import logging
import multiprocessing as mp
import os
import sys
import threading
import time
from pathlib import Path

from NeuRPi.loggers.logger import init_logger
from NeuRPi.networking import Message, Net_Node, Pilot_Station
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
            "PAUSE": self.l_pause,
            "RESUME": self.l_resume,
            "STOP": self.l_stop,
            "PARAM": self.l_param,
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
        self.handshake()
        self.logger.debug("handshake sent")

        self.task = None
        self.stimulus_display = None

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

    def l_start(self, value):
        """
        Terminal requested to start running the task

        Args:
            value (dict): protocol parameters
        """

        if self.state == "RUNNING" or self.running.is_set():
            self.logger.warning("Task already running. Cannot start new task")
            return
        self.logger.info(f"Starting task: {value['task_module']}")

        self.state = "RUNNING"
        self.running.set()
        try:
            self.task_module = value["task_module"]
            self.task_phase = value["task_phase"]
            self.subject_id = value["subject_id"]

            # Importing protocol function/class object using importlib
            task = importlib.import_module(
                "protocols." + self.task_module + ".tasks." + self.task_phase
            )

            self.stage_block.clear()

            # additing stimulus display queue
            value["stimulus_queue"] = mp.Manager().Queue()
            # Start display on separate process and wait for three secs for display initiation
            self.stimulus_display = mp.Process(target=self.start_display, args=(value,))
            self.stimulus_display.start()
            time.sleep(2)
            # Start the task on separate thread and update terminal
            threading.Thread(target=self.run_task, args=(task, value)).start()
            self.update_state()

        except Exception as e:
            self.state = "IDLE"
            self.logger.exception(f"Could not start the task: {e}")

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

    def l_param(self):
        pass

    def l_pause(self):
        """
        Remove `self.running` event flag
        """
        self.running.clear()

    def l_resume(self):
        """
        Resume task by setting `self.running` event
        """
        self.running.set()

    def start_display(self, task_params):
        """
        Import relevant stimulus configuration
        Import and start stimulus_display class relevant for requested task
        """
        display_module = (
            "protocols."
            + task_params["task_phase"]
            + ".stimulus."
            + task_params["task_phase"]
        )
        display_module = importlib.import_module(display_module)
        Stimulus_Display = display_module.Stimulus_Display
        directory = "protocols/" + task_params["task_module"] + "/config"
        stim_config = get_configuration(directory=directory, filename="stimulus")
        display = Stimulus_Display(
            stimulus_configuration=stim_config.STIMULUS,
            stimulus_courier=task_params["stimulus_queue"],
        )
        display.start()

    def run_task(self, task, task_params):
        """
        Start running task under new thread

        Initiate the task, and progress through each stage of task with `task.stages.next`

        Send data to terminal after every stage

        Waits for the task to clear `stage_block` between stages

        """

        self.logger.debug("initialing task")
        self.task = task(stage_block=self.stage_block, **task_params)
        self.logger.debug("task initialized")

        # TODO: Initialize sending continuous data here
        self.logger.debug("Starting task loop")
        try:
            while True:
                # Calculate next stage data and prepare triggers
                data = next(self.task.stages())()
                self.logger.debug("called stage method")

                if data:
                    data["pilot"] = self.name
                    data["subject_id"] = self.subject_id

                    # send data back to terminal
                    self.node.send("T", "DATA", data)

                # Waiting for stage block to clear
                self.stage_block.wait()
                self.logger.debug("stage block passed")

                # pause loop if the running flag is not set and current trial has ended.
                if not self.running.is_set() and "TRIAL_END" in data.keys():
                    # exit loop if stopping flag is set
                    if self.stopping.is_set():
                        task.end_session()
                        self.stimulus_display.terminate()
                        break

                    # if paused, wait for running event set?
                    self.running.wait()

        except Exception as e:
            self.logger.exception(
                f"got exception while running task; stopping task\n {e}"
            )

        finally:
            self.logger.debug("stopping task")
            try:
                self.task.end()
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
            "subjectID": "PSUIM4",
            "task_module": "dynamic_coherence_rt",
            "task_phase": "4",
        }
        quitting.wait()

    except KeyboardInterrupt:
        quitting.set()
        sys.exit()


if __name__ == "__main__":
    main()
