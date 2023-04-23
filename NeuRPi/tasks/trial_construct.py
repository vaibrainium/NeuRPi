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
        response_block,
        stimulus_queue,
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
        self.stimulus_queue = stimulus_queue
        # self.response_queue = response_queue
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
        self.thread = threading.Thread(
            target=self.monitor_response, args=[response_queue], daemon=True
        )
        self.thread.start()

    def monitor_response(self, response_queue):
        """
        Monitoring response from agent when requested by 'response_block.set()'.
        Monitoring can be either GO or NoGO for requested time. Conditions are passed by
        setting 'self.trigger' dictionary type: NoGO/GO and time: float in ms
        """
        while True:
            response_queue.queue.clear()
            self.response_block.wait()
            monitoring_behavior = True
            responded = False
            self.response = None

            start = time.time()
            wait_time = self.trigger["duration"]  # Converting wait time from ms to sec

            try:
                # When agent is supposed to fixate on one of the targets
                if self.trigger["type"] == "FIXATE_ON":
                    while monitoring_behavior:
                        if time.time() - start > wait_time:
                            # fixation time passed
                            monitoring_behavior = False
                            self.response_block.clear()
                            self.stage_block.set()
                            self.trigger = None
                        else:
                            if not response_queue.empty():
                                # responded
                                responded = response_queue.get()
                                print("RESPONDED")
                                if responded not in self.trigger["targets"]:
                                    # incorrect response
                                    monitoring_behavior = False
                                    response_queue.queue.clear()
                                    self.monitor_response(response_queue)

                # When agent is supposed to wait on one of the targets
                elif self.trigger["type"] == "WAIT_ON":
                    while monitoring_behavior:
                        if time.time() - start > wait_time:
                            monitoring_behavior = False
                        if not response_queue.empty():
                            responded = response_queue.get()
                            if responded not in self.trigger["targets"]:
                                # self.response_time = time.time() - start
                                response_queue.queue.clear()
                                self.response_block.clear()
                                self.stage_block.set()
                                monitoring_behavior = False

                # When agent is supposed to go to one of the targets
                elif self.trigger["type"] == "GO":
                    while monitoring_behavior:
                        if time.time() - start > wait_time:
                            response_queue.queue.clear()
                            self.response_block.clear()
                            self.stage_block.set()
                            monitoring_behavior = False
                        elif not response_queue.empty():
                            responded = response_queue.get()
                            if responded in self.trigger["targets"]:
                                self.response = responded
                                self.response_time = time.time() - start
                                response_queue.queue.clear()
                                self.response_block.clear()
                                self.stage_block.set()
                                monitoring_behavior = False

                # When agent Must respond
                elif self.trigger["type"] == "MUST_GO":
                    self.must_respond_block.clear()
                    response_queue.queue.clear()
                    while monitoring_behavior:
                        if not response_queue.empty():
                            responded = response_queue.get()
                            if responded in self.trigger["targets"]:
                                self.response = responded
                                response_queue.queue.clear()
                                self.response_block.clear()
                                self.must_respond_block.set()
                                monitoring_behavior = False
                    print(f"MONITOR BEHAVIOR {monitoring_behavior}")

            except Exception as e:
                print(e)
                raise Warning(
                    f"Problem with response monitoring for {self.trigger['type']}"
                )



if __name__ == "__main__":
    import itertools

    stage_block = threading.Event()
    stage_block.clear()
    stim_handler = queue.Queue()
    response_queue = queue.Queue()
    a = TrialConstruct(
        stage_block=stage_block,
        stimulus_queue=stim_handler,
        response_queue=response_queue,
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
