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

            start = time.time()
            wait_time = self.trigger["duration"]  # Converting wait time from ms to sec

            try:
                # When agent is supposed to fixate on one of the targets
                if self.trigger["type"] == "FIXATE_ON":
                    while monitoring_behavior:
                        if time.time() - start > wait_time:
                            monitoring_behavior = False
                            self.response_block.clear()
                            self.stage_block.set()
                            self.trigger = None
                        else:
                            if not response_queue.empty():
                                responded = response_queue.get()
                                if responded in self.trigger["targets"]:
                                    monitoring_behavior = False
                                    self.response_block.clear()
                                    self.stage_block.set()
                                    self.trigger = None
                                else:
                                    # self.response_time = time.time() - start
                                    response_queue.queue.clear()
                                    monitoring_behavior = False
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
                            monitoring_behavior = False
                        if not response_queue.empty():
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
                    while monitoring_behavior:
                        if not response_queue.empty():
                            responded = response_queue.get()
                            if (
                                responded in self.trigger["targets"]
                                and time.time() - start > wait_time
                            ):
                                response_queue.queue.clear()
                                self.response_block.clear()
                                self.stage_block.set()
                                monitoring_behavior = False

            except Exception as e:
                print(e)
                raise Warning(
                    f"Problem with response monitoring for {self.trigger['type']}"
                )

    def fixation(self, duration=0.500, targets=[np.NaN], arguments={}, *args, **kwargs):
        """
        Fixation stage making sure no trigger is set during fixation times.
        Arguments:
            duration (float): Fixation phase duration in secs
            targets (list): Possible targets to wait_on. [-1: left, 0: center. 1: right, np.NaN: Null]
        """
        # Clear the event lock -> defaults to event: false
        self.stage_block.clear()
        self.stimulus_queue.put(("initiate_fixation", arguments))
        self.trigger = {"type": "FIXATE_ON", "targets": targets, "duration": duration}
        self.response_block.set()

    def stimulus_rt(
        self,
        duration=2.000,
        targets=[-1, 1],
        min_viewing_duration=0,
        arguments={},
        *args,
        **kwargs,
    ):
        """
        Show stimulus and wait for response trigger on target/distractor input
        Arguments:
            duration (float): Max stimulus_rt phase duration in secs
            targets (list): Possible responses. [-1: left, 0: center. 1: right, np.NaN: Null]
        """
        # Clear the event lock -> defaults to event: false
        self.stage_block.clear()
        self.stimulus_queue.put(("initiate_stimulus", arguments))
        # Implement minimum stimulus viewing time by not validating responses during this period
        self.trigger = {
            "type": "GO",
            "targets": targets,
            "duration": duration - min_viewing_duration,
        }
        threading.Timer(min_viewing_duration, self.response_block.set).start()

    def stimulus_delay(self, duration=2.000, targets=[np.NaN], arguments={}):
        """
        Show stimulus and make sure subject doesn't respond (waits on target like fixation)
        Arguments:
            duration (float): Max stimulus_rt phase duration in secs
            targets (list): Possible targets to wait_on during stimulus period. [-1: left, 0: center. 1: right, np.NaN: Null]
        """
        # Clear the event lock -> defaults to event: false
        self.stage_block.clear()
        self.stimulus_queue.put(("initiate_stimulus", arguments))
        # Implement minimum stimulus viewing time by not validating responses during this period
        self.trigger = {"type": "WAIT_ON", "targets": targets, "duration": duration}
        self.response_block.set()

    def response_window(self, duration=2.000, targets=[np.NaN], arguments={}):
        """
        Response window for responding to one of the targets. For delay task
        Arguments:
            duration (float): Max wait time for response phase duration in secs
            targets (list): Possible responses. [-1: left, 0: center. 1: right, np.NaN: Null]
        """
        # Clear the event lock -> defaults to event: false
        self.stage_block.clear()
        self.stimulus_queue.put(("initiate_response_window", arguments))
        self.trigger = {"type": "GO", "targets": targets, "duration": duration}
        self.response_block.set()

    def reinforcement(self, duration=0.500, outcome=None, arguments={}):
        """
        Give audio and/or visual reinforcement
        Arguments:
            duration (float): Reinforcement display phase duration in secs
            outcome (str): Correct, Incorrect or Invalid
        """
        # Clear the event lock -> defaults to event: false
        self.stage_block.clear()
        arguments["outcome"] = outcome
        self.stimulus_queue.put(("initiate_reinforcement", arguments))
        threading.Timer(duration, self.stage_block.set).start()

    def must_respond(self, targets, arguments={}):
        """
        Must respond in one of the targets to proceed
        Arguments:
            targets (list): Possible responses for type. [-1: left, 0: center. 1: right]
        """
        # Clear the event lock -> defaults to event: false
        self.stage_block.clear()
        self.stimulus_queue.put(("initiate_must_respond", arguments))
        self.trigger = {"type": "MUST_GO", "targets": targets, "duration": []}
        self.response_block.set()

    def intertrial(self, duration=1.000, arguments={}):
        """
        Stage 3: Inter-trial Interval.
        Arguments:
            duration (float): Max stimulus_rt phase duration in secs
        """
        # Clear the event lock -> defaults to event: false
        self.stage_block.clear()
        self.stimulus_queue.put(("initiate_intertrial", arguments))
        # Setting timer to trigger stage_block event after defined inter-trial interval
        threading.Timer(duration, self.stage_block.set).start()


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
