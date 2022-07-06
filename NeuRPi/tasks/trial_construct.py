import queue
from itertools import count
# import tables
import threading
import hydra
import datetime, time
import numpy as np
from scipy.stats import pearson3


# If need be, work on multithreading later

class TrialConstruct(object):
    """
    Meta Class for contructing trial phases such as fixation, stimulus_rt, stimulus_delay, response, reinforcement, intertrial

    Phases:
        fixation: Runs fixation phase of the trial. Repeats phase until agent doesn't respond for given trigger time.
        stimulus_rt: Runs stimulus phase till agent responds till set max time.
        stimulus_delay: Runs stimulus passively for set time. If subject responds before delay period, makes trial invalid.
        response: Waits for agent to respond for set time. Required for stimulus_delay phase.
        reinforcement: Provides reinforcement depending on response.
        intertrial: Inter-trial interval phase.

        Trial_Data (class): Data table description:
            class TrialData(tables.IsDescription):
                trial_num             = tables.Int32Col(),
                target                = tables.StringCol(1)
                response              = tables.StringCol(1)
                correct               = tables.Int32Col(),
                valid                 = tables.Int32Col()
                stim_onset_timestamp  = tables.StringCol(26)

    """

    def __init__(self, stage_block, response_block, stimulus_handler, response_handler, *args, **kwargs):
        """
        Arguments:
            stage_block (threading.Event): Managing stage
            stim_handler (queue.Queue): Queue for sending message to stim_manager
            response_handler (queue.Queue): Queue for checking if response had been made
        """

        # Task Variables
        self.stimulus_handler = stimulus_handler
        # self.response_handler = response_handler
        self.stages = ('fixation', 'stimulus_rt', 'stimulus_delay', 'response', 'reinforcement', 'intertrial')
        self.stage_block = stage_block  # threading.Event used by the Task to manage stage transitions
        self.response_block = response_block  # threading.Event used by the pilot to manage stage transitions
        self.trigger = {}

        self.trial_counter = count(int(kwargs.get('current_trial', 0)))
        self.current_trial = int(kwargs.get('current_trial', 0))
        self.response = None
        self.response_time = None

        self.thread = threading.Thread(target=self.monitor_response, args=[response_handler], daemon=True).start()

    def get_configuration(self, directory=None, filename=None):
        '''
        Getting configuration from respective config.yaml file.

        Arguments:
            directory (str): Path to configuration directory relative to root directory (as Protocols/../...)
            filename (str): Specific file name of the configuration file
        '''
        path = '../../' + directory
        hydra.initialize(version_base=None, config_path=path)
        return hydra.compose(filename, overrides=[])

    def monitor_response(self, response_handler):
        """
        Monitoring response from agent when requested by 'response_block.set()'.
        Monitoring can be either GO or NoGO for requested time. Conditions are passed by
        setting 'self.trigger' dictionary type: NoGO/GO and time: float in ms
        """
        while True:
            response_handler.queue.clear()
            self.response_block.wait()
            monitor_behavior = True
            self.response = np.NaN
            self.response_time = np.NaN

            start = time.time()
            wait_time = self.trigger['duration']  # Converting wait time from ms to sec
            try:
                # When agent is supposed to fixate on one of the targets
                if self.trigger['type'] == 'FIXATE_ON':
                    while monitor_behavior:
                        if time.time() - start > wait_time:
                            monitor_behavior = False
                        if not response_handler.empty():
                            self.response = response_handler.get()
                            if self.response not in self.trigger['targets']:
                                self.response_time = time.time() - start
                                response_handler.queue.clear()
                                monitor_behavior = False
                                # self.monitor_response(response_handler)
                    if self.response in self.trigger['targets']:
                        self.response_block.clear()
                        self.stage_block.set()
                        self.trigger = None

                # When agent is supposed to wait on one of the targets
                elif self.trigger['type'] == 'WAIT_ON':
                    while monitor_behavior:
                        if time.time() - start > wait_time:
                            monitor_behavior = False
                        if not response_handler.empty():
                            self.response = response_handler.get()
                            if self.response not in self.trigger['targets']:
                                self.response_time = time.time() - start
                                response_handler.queue.clear()
                                self.response_block.clear()
                                self.stage_block.set()
                                monitor_behavior = False

                # When agent is supposed to go to one of the targets
                elif self.trigger['type'] == 'GO':
                    while monitor_behavior:
                        if time.time() - start > wait_time:
                            monitor_behavior = False
                        if not response_handler.empty():
                            self.response = response_handler.get()
                            if self.response in self.trigger['targets']:
                                self.response_time = time.time() - start
                                response_handler.queue.clear()
                                self.response_block.clear()
                                self.stage_block.set()
                                monitor_behavior = False

                # When agent Must respond
                elif self.trigger['type'] == 'MUST_GO':
                    while monitor_behavior:
                        if not response_handler.empty():
                            self.response = response_handler.get()
                            if self.response in self.trigger['targets']:
                                self.response_time = time.time() - start
                                response_handler.queue.clear()
                                self.response_block.clear()
                                self.stage_block.set()
                                monitor_behavior = False

            except:
                raise Warning(f"Problem with response monitoring for {self.trigger['type']}")


    def fixation(self, duration=0.500, targets=[np.NaN], arguments={}, *args, **kwargs):
        """
        Fixation stage making sure no trigger is set during fixation times.
        Arguments:
            duration (float): Fixation phase duration in secs
            targets (list): Possible targets to wait_on. [-1: left, 0: center. 1: right, np.NaN: Null]
        """
        # Clear the event lock -> defaults to event: false
        self.stage_block.clear()
        self.stimulus_handler.put(('initiate_fixation', arguments))
        self.trigger = {'type': 'FIXATE_ON', 'targets': targets, 'duration': duration}
        self.response_block.set()

    def stimulus_rt(self, duration=2.000, targets=[-1, 1], min_viewing_duration=0, arguments={}, *args, **kwargs):
        """
        Show stimulus and wait for response trigger on target/distractor input
        Arguments:
            duration (float): Max stimulus_rt phase duration in secs
            targets (list): Possible responses. [-1: left, 0: center. 1: right, np.NaN: Null]
        """
        print(arguments['coherence'])
        # Clear the event lock -> defaults to event: false
        self.stage_block.clear()
        self.stimulus_handler.put(('initiate_stimulus', arguments))
        # Implement minimum stimulus viewing time by not validating responses during this period
        self.trigger = {'type': 'GO', 'targets': targets, 'duration': duration - min_viewing_duration}
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
        self.stimulus_handler.put(('initiate_stimulus', arguments))
        # Implement minimum stimulus viewing time by not validating responses during this period
        self.trigger = {'type': 'WAIT_ON', 'targets': targets, 'duration': duration}
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
        self.stimulus_handler.put(('initiate_response_window', arguments))
        self.trigger = {'type': 'GO', 'targets': targets, 'duration': duration}
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
        arguments['outcome'] = outcome
        self.stimulus_handler.put(('initiate_reinforcement', arguments))
        threading.Timer(duration, self.stage_block.set).start()

    def must_respond(self, targets, arguments={}):
        """
        Must respond in one of the targets to proceed
        Arguments:
            targets (list): Possible responses for type. [-1: left, 0: center. 1: right]
        """
        # Clear the event lock -> defaults to event: false
        self.stage_block.clear()
        self.stimulus_handler.put(('initiate_must_respond', arguments))
        self.trigger = {'type': 'MUST_GO', 'targets': targets, 'duration': []}
        self.response_block.set()

    def intertrial(self, duration=1.000, arguments={}):
        """
        Stage 3: Inter-trial Interval.
        Arguments:
            duration (float): Max stimulus_rt phase duration in secs
        """
        # Clear the event lock -> defaults to event: false
        self.stage_block.clear()
        self.stimulus_handler.put(('initiate_intertrial', arguments))
        # Setting timer to trigger stage_block event after defined inter-trial interval
        threading.Timer(duration, self.stage_block.set).start()


if __name__ == '__main__':
    import itertools

    stage_block = threading.Event()
    stage_block.clear()
    stim_handler = queue.Queue()
    response_handler = queue.Queue()
    a = TrialConstruct(stage_block=stage_block, stimulus_handler=stim_handler, response_handler=response_handler)
    stage_list = [a.fixation, a.stimulus_rt, a.intertrial]
    num_stages = len(stage_list)
    stages = itertools.cycle(stage_list)

    while True:
        data = next(stages)()
        time.sleep(.5)
        stage_block.wait()
        print(time.time() - a.start)

    #     # Has trial ended?
    #     if 'TRIAL_END' in data.keys():
    #         self.running.wait()  # If paused, waiting for running event set?
    #         if self.quitting.is_set():  # is quitting event set?
    #             break  # Won't quit if the task is paused.
    #
    # self.task.stop()
