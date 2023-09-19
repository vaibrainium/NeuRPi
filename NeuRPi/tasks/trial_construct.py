import datetime
import queue

# import tables
import threading
import time
from itertools import count

import hydra
import numpy as np
from scipy.stats import pearson3

# If need be, work on multithreading later


class TrialConstruct:
    """
    Meta Class for contructing trial phases such as fixation, stimulus_rt, stimulus_delay, response, reinforcement, intertrial

    Arguments:
        fixation: Runs fixation phase of the trial. Repeats phase until agent doesn't respond for given trigger time.
        stimulus_rt: Runs stimulus phase till agent responds till set max time.
        stimulus_delay: Runs stimulus passively for set time. If subject responds before delay period, makes trial invalid.
        response: Waits for agent to respond for set time. Required for stimulus_delay phase.
        reinforcement: Provides reinforcement depending on response.
        intertrial: Inter-trial interval phase.


    """

    def __init__(
        self,
        stage_block,
        msg_to_stimulus,
        response_block,
        response_queue,
        *args,
        **kwargs,
    ):
        """
        Arguments:
            stage_block (threading.Event): Managing stage
            stim_handler (queue.Queue): Queue for sending message to stim_manager
            response_queue (queue.Queue): Queue for checking if response has been made
        """

        # Task Variables
        self.msg_to_stimulus = msg_to_stimulus
        self.response_queue = response_queue
        self.stages = (
            "fixation",
            "stimulus_rt",
            "stimulus_delay",
            "response",
            "reinforcement",
            "intertrial",
        )
        self.stage_block = (
            stage_block  # threading.Event used by the Task to manage stage transitions
        )
        self.response_block = response_block  # threading.Event used by the pilot to manage stage transitions
        self.trigger = {}
        self.must_respond_block = threading.Event()
        self.must_respond_block.clear()
        # self.thread = threading.Thread(
        #     target=self.monitor_response, args=[response_queue], daemon=True
        # )
        # self.thread.start()

    def fixation_monitor(self, target, duration):
        """
        Monitors fixation on target for given duration.
        """
        fixation_success = False
        self.response_block.set()
        while not fixation_success:
            try:
                response = self.response_queue.get(block=True, timeout=duration)
                if response not in target:
                    # fixation failed so repeat
                    # self.stage_block.clear()
                    self.clear_queue()
            except queue.Empty:
                # fixation success
                fixation_success = True
                # self.stage_block.set()
                self.clear_queue()
                self.response_block.clear()
        return fixation_success

    def choice_monitor(self, target, duration):
        """
        Monitors response on target for given duration.
        """
        start = time.time()
        self.response_block.set()
        try:
            response = self.response_queue.get(block=True, timeout=duration)
            if response in target:
                response_time = time.time() - start
        except queue.Empty:
            response = np.nan
            response_time = np.nan
        finally:
            self.clear_queue()
            self.response_block.clear()
            # self.stage_block.set()
        return response, response_time
        

    def must_respond_monitor(self, target):
        """
        Making sure that agent responds to target.
        """
        must_respond_success = False
        self.response_block.set()
        while not must_respond_success:
            try:
                response = self.response_queue.get(block=True)
                if response in target:
                    must_respond_success = True
                    self.clear_queue()
                    self.response_block.clear()
            except queue.Empty:
                pass

        return must_respond_success
                

    def monitor_response(self, response_queue):
        """
        Monitoring response from agent when requested by 'response_block.set()'.
        Monitoring can be either GO or NoGO for requested time. Conditions are passed by
        setting 'self.trigger' dictionary type: NoGO/GO and time: float in ms
        """
        while True:
            self.clear_queue()
            self.response_block.wait()
            monitoring_behavior = True
            responded = False
            self.response = np.nan
            start = time.time()
            wait_time = self.trigger["duration"]  # Converting wait time from ms to sec

            try:
                # When agent is supposed to fixate on one of the targets
                if self.trigger["type"] == "FIXATE_ON":      
                    # alternative for below code
                    while monitoring_behavior:
                        start = time.time()
                        try:
                            self.response = response_queue.get(block=True, timeout=wait_time)
                            if self.response not in self.trigger["targets"]:
                                self.response_block.clear()
                        except queue.Empty:
                            monitoring_behavior = False
                            self.response_block.clear()
                            self.stage_block.set()
                            self.trigger = None
                        finally:
                            self.clear_queue()
                    # OLD WORKING LOGIC
                    # start = time.time()
                    # while monitoring_behavior:
                    #     if time.time() - start > wait_time:
                    #         # fixation time passed
                    #         monitoring_behavior = False
                    #         self.response_block.clear()
                    #         self.stage_block.set()
                    #         self.trigger = None
                    #     else:
                    #         if not response_queue.empty():
                    #             # responded
                    #             responded = response_queue.get()
                    #             # print("RESPONDED DURING FIXATION")
                    #             if responded not in self.trigger["targets"]:
                    #                 # incorrect response
                    #                 self.response_block.clear()
                    #                 self.clear_queue()

                    #                 responded = False
                    #                 self.response_block.set()
                    #                 start = time.time()

                    #                 # monitoring_behavior = False
                    #                 # self.monitor_response(response_queue)

                # When agent is supposed to go to one of the targets
                elif self.trigger["type"] == "GO":            
                    # alternative for below code
                    start = time.time()
                    try:
                        self.response = response_queue.get(block=True, timeout=wait_time)
                        if self.response in self.trigger["targets"]:
                            self.response_time = time.time() - start
                    except queue.Empty:
                        self.response = np.nan
                        self.response_time = np.nan
                    finally:
                        self.clear_queue()
                        self.response_block.clear()
                        self.stage_block.set()
                        monitoring_behavior = False
                    # OLD WORKING LOGIC
                    # start = time.time()
                    # while monitoring_behavior:
                    #     if time.time() - start > wait_time:
                    #         self.clear_queue()
                    #         self.response_block.clear()
                    #         self.stage_block.set()
                    #         monitoring_behavior = False
                    #     elif not response_queue.empty():
                    #         responded = response_queue.get()
                    #         if responded in self.trigger["targets"]:
                    #             self.response = responded
                    #             self.response_time = time.time() - start
                    #             self.clear_queue()
                    #             self.response_block.clear()
                    #             self.stage_block.set()
                    #             monitoring_behavior = False

                # When agent Must respond
                elif self.trigger["type"] == "MUST_GO":
                    self.must_respond_block.clear()
                    self.clear_queue()
                    # alternative for below code
                    while monitoring_behavior:
                        try:
                            self.response = response_queue.get(block=True)
                            if self.response in self.trigger["targets"]:
                                self.clear_queue()
                                self.response_block.clear()
                                self.must_respond_block.set()
                                monitoring_behavior = False
                        except queue.Empty:
                            print("Must respond wait failed")
                    # OLD WORKING LOGIC
                    # while monitoring_behavior:
                    #     if not response_queue.empty():
                    #         responded = response_queue.get()
                    #         if responded in self.trigger["targets"]:
                    #             self.clear_queue()
                    #             self.response_block.clear()
                    #             self.must_respond_block.set()
                    #             monitoring_behavior = False

            except Exception as e:
                print(e)
                raise Warning(
                    f"Problem with response monitoring for {self.trigger['type']}"
                )

    def clear_queue(self):
        while not self.response_queue.empty():
            self.response_queue.get()


if __name__ == "__main__":
    import itertools
    import multiprocessing as mp

    stage_block = threading.Event()
    stage_block.clear()
    stim_handler = queue.Queue()
    response_block = threading.Event()
    response_queue = mp.Queue()
    a = TrialConstruct(
        stage_block=stage_block,
        msg_to_stimulus=stim_handler,
        response_queue=response_queue,
        response_block=response_block,
    )
    stage_list = [a.fixation, a.stimulus_rt, a.intertrial]
    num_stages = len(stage_list)
    stages = itertools.cycle(stage_list)

    while True:
        data = next(stages)()
        time.sleep(0.5)
        stage_block.wait()
        print(time.time() - a.start)

    #     # Has trial ended?
    #     if 'TRIAL_END' in data.keys():
    #         self.running.wait()  # If paused, waiting for running event set?
    #         if self.quitting.is_set():  # is quitting event set?
    #             break  # Won't quit if the task is paused.
    #
    # self.task.stop()
