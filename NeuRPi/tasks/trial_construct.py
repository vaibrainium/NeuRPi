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
        self.choice = None
        self.response_time = None
        self.response_queue = response_queue
        self.stage_block = stage_block  # threading.Event used by the Task to manage stage transitions
        self.response_block = response_block  # threading.Event used by the pilot to manage stage transitions
        self.response_block.clear()
        self.trigger = {}
        self.must_respond_block = threading.Event()
        self.must_respond_block.clear()

        self.thread = threading.Thread(target=self.monitor_response, daemon=True)
        self.thread.start()

    def fixation_monitor(self, target, duration):
        """
        Monitors fixation on target for given duration.
        """
        fixation_success = False
        while not fixation_success:
            try:
                response = self.response_queue.get(block=True, timeout=duration)
                if response not in target:
                    # fixation failed so repeat
                    self.clear_queue()
            except queue.Empty:
                # fixation success
                fixation_success = True
                self.clear_queue()
                self.response_block.clear()
        return fixation_success

    def choice_monitor(self, target, duration):
        """
        Monitors response on target for given duration.
        """
        monitor_duration = duration
        start = time.time()
        remaining_duration = monitor_duration - (time.time() - start)
        while remaining_duration > 0:
            try:
                response = self.response_queue.get(block=True, timeout=remaining_duration)
                if response in target:
                    response_time = time.time() - start
                    break
                else:
                    remaining_duration = monitor_duration - (time.time() - start)

            except queue.Empty:
                response = np.nan
                response_time = np.nan
                break
        
        self.clear_queue()
        self.response_block.clear()
        return [response, response_time]
        

    def must_respond_monitor(self, target):
        """
        Making sure that agent responds to target.
        """
        must_respond_success = False
        self.must_respond_block.clear()
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
                
    def monitor_response(self):
        while True:
            self.trigger = None
            self.clear_queue()
            self.must_respond_block.clear()
            self.response_block.wait()
            try:
                if self.trigger['type'] == "FIXATE":
                    self.fixation_monitor(self.trigger['targets'], self.trigger['duration'])
                    self.stage_block.set()
                elif self.trigger['type'] == "GO":
                    self.choice, self.response_time = self.choice_monitor(self.trigger['targets'], self.trigger['duration'])
                    self.stage_block.set()
                elif self.trigger['type'] == "MUST_RESPOND":
                    self.must_respond_monitor(self.trigger['targets'])
                    self.must_respond_block.set()
            except Exception as e:
                print(e)
                raise Warning(f"Problem with response monitoring for {self.trigger['type']}")

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
