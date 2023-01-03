import logging
import multiprocessing as mp
import os
import sys
import threading
from pathlib import Path

from NeuRPi.loggers.logger import init_logger
from NeuRPi.networking import Message, Net_Node, Pilot_Station
from NeuRPi.prefs import prefs


class Pilot:

    logger = None

    # Events for thread handling
    running = None
    stage_block = None
    file_block = None
    quitting = None

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
        self.running = threading.Event()  # Are we running a task?
        self.stage_block = threading.Event()  # Are we waiting on stage triggers?
        self.file_block = threading.Event()  # Are we waiting on file transfer?
        self.quitting = threading.Event()
        self.quitting.clear()

        # initialize listens dictionary
        self.listens = {
            "START": self.l_start,
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
        self.stimulus_manager = None
        self.stimulus_queue = None

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
            self.subject_id = value["subject_id"]
            self.stage_block.clear()

            # Start the task on separate thread and update terminal
            threading.Thread(
                target=self.run_task, args=(self.task_module, value)
            ).start()
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
        self.state = "STOPPING"
        self.update_state()

        self.running.clear()
        self.stage_block.set()

        # TODO: Perform data matching or post task routines

        self.state = "IDLE"
        self.update_state()

    def l_param(self):
        pass

    def run_task(self, task_module, task_params):
        """
        Start running task under new thread

        Initiate the task, and progress through each stage of task with `task.stages.next`

        Send data to terminal after every stage

        Waits for the task to clear `stage_block` between stages

        """

        self.logger.debug("initialing task")
        self.task = task_module(stage_block=self.stage_block, **task_params)
        self.logger.debug("task initialized")

        # Is trial data expected?
        trial_data = False
        if hasattr(self.task, "TrialData"):
            trial_data = True

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

                    # # TODO: Store a local copy
                    # # the task class has a class variable DATA that lets us know which data the row is expecting
                    # if trial_data:
                    #     for k, v in data.items():
                    #         if k in self.task.TrialData.columns.keys():
                    #             row[k] = v
                    # # If the trial is over (either completed or bailed), flush the row
                    # if 'TRIAL_END' in data.keys():
                    #     row.append()
                    #     table.flush()
                    # self.logger.debug('sent data')

                # Waiting for stage block to clear
                self.stage_block.wait()
                self.logger.debug("stage block passed")

                # Exit loop if the running flag is not set.
                if not self.running.is_set():
                    break
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
    try:
        pi = Pilot()
        pi.handshake()

        msg = {
            "subjectID": "test_subject",
            "task_module": "dynamic_coherence",
            "task_phase": "4",
        }
        pi.quitting.wait()
    except KeyboardInterrupt:
        pi.quitting.set()
        sys.exit()


if __name__ == "__main__":
    main()
