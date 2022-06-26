import queue

from NeuRPi.tasks.trial_construct import TrialConstruct
from Protocols.RDK.hardware.hardware_manager import HardwareManager
from Protocols.RDK.tasks.training_behavior import Behavior
import numpy as np
import itertools
import tables
import threading
import datetime
from scipy.stats import pearson3
import time


class RDK(TrialConstruct):
    """
    Two-alternative force choice task for random dot motion tasks
    **Stages**
    * **fixation** - fixation time for baseline
    * **stimulus** - Stimulus display
    * **reinforcement** - deliver reward/punishment
    * **intertrial** - waiting period between two trials
    Attributes:
        stim: Current stimulus (coherence)
        target ("L","R"): Correct response
        distractor ("L", "R"): Incorrect response
        response ("L", "R"): Response to discrimination
        correct (0, 1): Current trial was correct/incorrect
        correction_trial (bool): If using correction trial was
        trial_counter (from itertools.count): What is the currect trial was
        discrim_playiong (bool): In the stimulus playing?
        bailed (0, 1): Invalid trial
        current_stage (int): As each is reached, update for asynchronous event reference
    """

    STAGE_NAMES = ["fixation", "stimulus", "reinforcement", "intertrial"]

    class TrialData(tables.IsDescription):
        trial_num = tables.Int32Col()
        target = tables.StringCol(1)
        response = tables.StringCol(1)
        correct = tables.Int32Col()
        correction = tables.Int32Col()
        RQ_timestamp = tables.StringCol(26)
        DC_timestamp = tables.StringCol(26)
        bailed = tables.Int32Col()

    def __init__(self, trial_manager=None, stage_block=None, **kwargs):

        """
        Args:
            stage_block (:class:`threading.Event`): Signal when task stages complete.
            rollling_perf (dict): Dictionary for keeping track of rolling performance over multiple sessions.
            stim (dict): Stimuli like::
                "sitm": {
                    "L": [{"type": "Tone", ...}],
                    "R": [{"type": "Tone", ...}]
                }
            reward (float): duration of solenoid open in ms
            req_reward (bool): Whether to give a water reward in the center port for requesting trials
            punish_stim (bool): Do a white noise punishment stimulus
            punish_dur (float): Duration of white noise in ms
            correction (bool): Should we do correction trials?
            correction_pct (float):  (0-1), What proportion of trials should randomly be correction trials?
            bias_mode (False, "thresholded_linear"): False, or some bias correction type (see :class:`.managers.Bias_Correction` )
            bias_threshold (float): If using a bias correction mode, what threshold should bias be corrected for?
            current_trial (int): If starting at nonzero trial number, which?
            stim_light (bool): Should the LED be turned blue while the stimulus is playing?
            **kwargs:
        """
        # Get configuration for this task -> self.config
        self.config = self.get_configuration(directory='Protocols/RDK/config', filename='dynamic_coherences')
        self.task_pars = self.config.TASK_PARAMETERS  # Get all task parameters

        # Event locks, triggers
        self.stage_block = threading.Event()
        self.stage_block.clear()
        self.response_block = threading.Event()
        self.response_block.clear()

        self.stim_handler = queue.Queue()
        super(RDK, self).__init__(self.stage_block, self.stim_handler)

        # Initializing managers
        self.trial_manager = trial_manager(self.task_pars)
        self.hardware_manager = HardwareManager(self.config)
        self.behavior = Behavior(hardware_manager=self.hardware_manager, stage_block=self.stage_block,
                                 response_block=self.response_block, response_handler=self.response_handler)
        self.behavior.start()

        # Variable parameters
        self.current_stage = None  # Keeping track of stages so other asynchronous callbacks can execute accordingly
        self.target = None
        self.response = None
        self.bailed = None
        self.correct = None
        self.response_time = None
        self.correction_trial = None
        self.valid = None
        self.start = None
        self.fixation_duration = None
        self.stimulus_duration = None
        self.intertrial_duration = None

        # We make a list of the variables that need to be reset each trial, so it's easier to do
        self.resetting_variables = [self.response, self.response_time]

        # This allows us to cycle through the task by just repeatedly calling self.stages.next()
        stage_list = [self.fixation, self.stimulus_rt, self.intertrial]
        self.num_stages = len(stage_list)
        self.stages = itertools.cycle(stage_list)

        self.run()

    def run(self):

        while True:
            self.start = time.time()
            print(self.current_trial, time.time() - self.start, 'Fixation Started')
            data = self.fixation_stage()

            print(self.current_trial, time.time() - self.start, 'Stimulus Started')
            data = self.stimulus_stage()

            print(self.current_trial, time.time() - self.start, 'Reinforcement Started')
            data = self.reinforcement_stage()

            if self.correct:
                print(self.current_trial, time.time() - self.start, 'Waiting for reward Consumption')
                data = self.must_respond_to_proceed()

            print(self.current_trial, time.time() - self.start, 'Intertrial Started')
            data = self.intertrial_stage()

    def fixation_stage(self):
        self.fixation_duration = self.task_pars.timings.fixation.value
        self.fixation(duration=self.fixation_duration)
        # Get current trial properties
        if not self.correction_trial:
            self.current_trial = next(self.trial_counter)
        self.trial_manager.next_trial(self.correction_trial)
        data = {
            'DC_timestamp': datetime.datetime.now().isoformat(),
            'trial_num': self.current_trial,
        }
        self.stage_block.wait()
        return data

    def stimulus_stage(self):
        """
        Stage 1: Show stimulus and wait for response trigger on target/distractor input
        Returns:
            data (dict):
            {
            }
        """
        # Set triggers, set display and start timer
        if self.task_pars.training_type.value < 0:
            self.stimulus_duration = self.task_pars.training_type.active_passive.passive_rt_mu + \
                                     (pearson3.rvs(self.task_pars.training_type.active_passive.passive_rt_sigma) * 1.5)
        else:
            self.stimulus_duration = self.task_pars.timings.stimulus.max_value

        self.stimulus_rt(duration=self.stimulus_duration)

        data = {
            'DC_timestamp': datetime.datetime.now().isoformat(),
            'trial_num': self.current_trial,
            'response': self.response,
            'response_time': self.response_time
        }
        self.stage_block.wait()
        self.response_time = self.response_time + self.task_pars.timings.stimulus.min_viewing
        print(f'Responded with {self.response} in {self.response_time} secs')
        return data

    def reinforcement_stage(self):
        """
        Stage 2: Evaluate choice and deliver reinforcement (reward/punishment) and respective intertrial interval
        Returns:
            data (dict):
            {
            }
        """
        if np.isnan(self.response):  # Invalid Trial
            self.reinforcement(outcome='Invalid', duration=self.task_pars.feedback.correct.time.value)
            self.valid, self.correct, self.correction_trial = [0, 0, 1]
            iti_decay = self.task_pars.feedback.invalid.intertrial
            self.intertrial_duration = self.task_pars.timings.intertrial + (
                        iti_decay.base * np.exp(iti_decay.power * self.task_pars.timings.stimulus.min_viewing))

        elif self.stim_pars['target'] != self.response:  # Incorrect Trial
            self.reinforcement(outcome='Incorrect', duration=self.task_pars.feedback.correct.time.value)
            self.valid, self.correct, self.correction_trial = [1, 0, 1]
            iti_decay = self.task_pars.feedback.incorrect.intertrial
            self.intertrial_duration = self.task_pars.timings.intertrial + (
                        iti_decay.base * np.exp(iti_decay.power * self.response_time))

        elif self.stim_pars['target'] == self.response:  # Correct Trial
            self.reinforcement(outcome='Correct', duration=self.task_pars.feedback.correct.time.value)
            if self.response == -1:  # Left Correct
                self.hardware_manager.reward_left(volume=2)
            elif self.response == 1:  # Right Correct
                self.hardware_manager.reward_left(volume=2)
            self.valid, self.correct, self.correction_trial = [1, 1, 0]
            self.intertrial_duration = self.task_pars.timings.intertrial
        self.stage_block.wait()
        data = {
            'DC_timestamp': datetime.datetime.now().isoformat(),
            'trial_num': self.current_trial,
        }
        return data

    def must_respond_to_proceed(self):
        """
        Returns:
            data (dict):
            {
            }
        """
        # Agent must consume reward before proceeding
        self.must_respond(direction=[self.target])
        data = {
            'DC_timestamp': datetime.datetime.now().isoformat(),
            'trial_num': self.current_trial,
        }
        return data

    def intertrial_stage(self, *args, **kwargs):
        """
        Stage 3: Inter-trial Interval.
        Returns:
            data (dict):
            {
            }
        """

        self.intertrial(duration=self.intertrial_duration)
        self.trial_manager.update_EOT()

        data = {
            'DC_timestamp': datetime.datetime.now().isoformat(),
            'trial_num': self.current_trial,
            'TRIAL_END': True
        }
        self.stage_block.wait()
        return data



if __name__ == '__main__':
    pass