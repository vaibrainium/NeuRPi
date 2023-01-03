import datetime
import itertools
import queue
import threading
import time

import numpy as np
import tables
from scipy.stats import pearson3

from NeuRPi.tasks.trial_construct import TrialConstruct
from protocols.RDK.hardware.behavior import Behavior
from protocols.RDK.hardware.hardware_manager import HardwareManager


class RTTask(TrialConstruct):
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

    def __init__(
        self,
        stage_block=None,
        response_block=None,
        stimulus_queue=None,
        managers=None,
        config=None,
        timers=None,
        **kwargs,
    ):
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
        super(RTTask, self).__init__(
            stage_block=stage_block,
            response_block=response_block,
            stimulus_queue=stimulus_queue,
            response_queue=managers["behavior"].response_queue,
        )

        self.config = config
        self.timers = timers

        # Event locks, triggers
        self.stage_block = stage_block
        self.response_block = response_block

        # Initializing managers
        self.session_manager = managers["session"]
        self.hardware_manager = managers["hardware"]

        # Variable parameters
        # Counters
        self.trial_counter = itertools.count(int(kwargs.get("current_trial", 0)))
        self.attempt_counter = itertools.count(int(kwargs.get("current_attempt", 0)))
        self.current_trial = None
        self.current_attempt = None
        self.current_stage = None  # Keeping track of stages so other asynchronous callbacks can execute accordingly
        # Trial interaction variables
        self.trigger = None
        self.target = None
        self.response = None
        self.response_time = None
        self.responded = None
        self.correct = None
        self.valid = None
        self.stimulus_pars = None
        self.intertrial_duration = None
        self.correction_trial = None

        # We make a list of the variables that need to be reset each trial, so it's easier to do
        self.resetting_variables = [
            self.stimulus_pars,
            self.response,
            self.response_time,
            self.responded,
        ]

        # This allows us to cycle through the task by just repeatedly calling self.stages.next()
        stage_list = [
            self.fixation_stage,
            self.stimulus_stage,
            self.reinforcement_stage,
            self.must_respond_to_proceed,
            self.intertrial_stage,
        ]
        self.num_stages = len(stage_list)
        self.stages = itertools.cycle(stage_list)

    def fixation_stage(self):
        # Clear stage block
        self.stage_block.clear()
        # Determine stage parameters
        targets = np.NaN
        duration = self.config.TASK.timings.fixation.value
        self.trigger = {"type": "FIXATE_ON", "targets": targets, "duration": duration}
        stimulus_arguments = {}

        # initiate fixation and start monitoring responses
        self.stimulus_queue.put(("initiate_fixation", stimulus_arguments))
        self.timers["trial"] = time.time()
        self.response_block.set()

        # Get current trial properties
        if not self.correction_trial:
            self.current_trial = next(self.trial_counter)
            self.attempt_counter = itertools.count(int(0))
        else:
            self.current_attempt = next(self.attempt_counter)

        self.stimulus_pars = self.session_manager.next_trial(self.correction_trial)
        data = {
            "DC_timestamp": datetime.datetime.now().isoformat(),
            "trial_num": self.current_trial,
        }
        return data

    def stimulus_stage(self):
        """
        Stage 1: Show stimulus and wait for response trigger on target/distractor input
        Arguments:
            duration (float): Max stimulus_rt phase duration in secs
            targets (list): Possible responses. [-1: left, 0: center. 1: right, np.NaN: Null]
        """
        # Clear stage block
        self.stage_block.clear()
        # Determine stage parameters
        min_viewing_duration = self.task_pars.timings.stimulus.min_viewing
        stimulus_arguments = self.stimulus_pars
        targets = [-1, 1]
        if self.task_pars.training_type.value < 0:
            duration = self.task_pars.training_type.active_passive.passive_rt_mu + (
                pearson3.rvs(
                    self.task_pars.training_type.active_passive.passive_rt_sigma
                )
                * 1.5
            )
        else:
            duration = self.task_pars.timings.stimulus.max_viewing

        # implement minimum stimulus viewing time by not validating responses during this period
        self.trigger = {
            "type": "GO",
            "targets": targets,
            "duration": duration - min_viewing_duration,
        }

        # initiate stimulus and start monitoring responses
        self.stimulus_queue.put(("initiate_stimulus", stimulus_arguments))
        # set respons_block after minimum viewing time
        threading.Timer(min_viewing_duration, self.response_block.set).start()

        data = {
            "DC_timestamp": datetime.datetime.now().isoformat(),
            "trial_num": self.current_trial,
            "response": self.response,
            "response_time": self.response_time,
        }

        self.response_time = (
            self.response_time + self.task_pars.timings.stimulus.min_viewing
        )
        self.stage_block.wait()
        print(
            f"Responded with {self.response} in {self.response_time} secs for target: {self.stimulus_pars['target']}"
        )
        return data

    def reinforcement_stage(self):
        """
        Stage 2: Evaluate choice and deliver reinforcement (reward/punishment) and decide respective intertrial interval

        """
        # Clear stage block
        self.stage_block.clear()
        # Evaluate trial outcome and determine stage parameters
        stimulus_arguments = {}
        if np.isnan(self.response):
            stimulus_arguments["outcome"] = "invalid"
            duration = self.config.TASK.feedback.invalid.time.value
            self.valid, self.correct, self.correction_trial = [0, 0, 1]

            iti_decay = self.config.TASK.feedback.invalid.intertrial
            self.intertrial_duration = self.config.TASK.timings.intertrial.value + (
                iti_decay.base
                * np.exp(
                    iti_decay.power * self.config.TASK.timings.stimulus.min_viewing
                )
            )

            # Starting reinforcement
            self.stimulus_queue.put(
                ("initiate_reinforcement", stimulus_arguments["outcome"])
            )
            threading.Timer(duration, self.stage_block.set).start()

        elif self.stimulus_pars["target"] != self.response:  # Incorrect Trial
            stimulus_arguments["outcome"] = "incorrect"
            duration = self.task_pars.feedback.incorrect.time.value
            self.valid, self.correct, self.correction_trial = [1, 0, 1]
            iti_decay = self.task_pars.feedback.incorrect.intertrial
            self.intertrial_duration = self.task_pars.timings.intertrial.value + (
                iti_decay.base * np.exp(iti_decay.power * self.response_time)
            )
            # Starting reinforcement
            self.stimulus_queue.put(
                ("initiate_reinforcement", stimulus_arguments["outcome"])
            )
            threading.Timer(duration, self.stage_block.set).start()

        elif self.stimulus_pars["target"] == self.response:  # Correct Trial
            stimulus_arguments["outcome"] = "correct"
            duration = self.task_pars.feedback.correct.time.value

            if self.response == -1:  # Left Correct
                self.managers["hardware"].reward_left(
                    self.config.SUBJECT.reward_per_pulse
                )
            elif self.response == 1:  # Right Correct
                self.managers["hardware"].reward_right(
                    self.config.SUBJECT.reward_per_pulse
                )
            self.valid, self.correct, self.correction_trial = [1, 1, 0]
            self.intertrial_duration = self.task_pars.timings.intertrial.value

            # Starting reinforcement
            self.stimulus_queue.put(
                ("initiate_reinforcement", stimulus_arguments["outcome"])
            )
            # threading.Timer(duration, self.stage_block.set).start()
            # Entering must respond phase
            self.trigger = {
                "type": "MUST_GO",
                "targets": self.stimulus_pars["target"],
                "duration": duration,
            }
            self.response_block.set

        data = {
            "DC_timestamp": datetime.datetime.now().isoformat(),
            "trial_num": self.current_trial,
        }
        return data

    def intertrial_stage(self, *args, **kwargs):
        """
        Stage 3: Inter-trial Interval.

        """
        # Clear stage block
        self.stage_block.clear()
        # Setting parametes
        arguments = {}
        duration = self.intertrial_duration
        # Starting intertrial interval
        self.stimulus_queue.put(("initiate_intertrial", arguments))
        threading.Timer(duration, self.stage_block.set).start()
        # performing end of trial analysis
        self.managers["session"].update_EOT()

        data = {
            "DC_timestamp": datetime.datetime.now().isoformat(),
            "trial_num": self.current_trial,
            "TRIAL_END": True,
        }
        return data


if __name__ == "__main__":
    stage_block = threading.Event()
    a = RTTask(stage_block=stage_block)
