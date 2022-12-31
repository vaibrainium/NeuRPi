import datetime
import itertools
import queue
import threading
import time
from copy import copy, deepcopy

import numpy as np
from scipy.stats import pearson3

from NeuRPi.prefs import prefs
from NeuRPi.tasks.trial_construct import TrialConstruct
from NeuRPi.utils.get_config import get_configuration
from protocols.RDK.data_model.subject import Subject
from protocols.RDK.hardware.behavior import Behavior
from protocols.RDK.hardware.hardware_manager import HardwareManager
from protocols.RDK.stimulus.display_manager import DisplayManager as BaseDisplayManager
from protocols.RDK.stimulus.random_dot_kinematogram import (
    RandomDotKinematogram as BaseRDKManager,
)
from protocols.RDK.tasks.rt_task import RTTask


class RDKManager(BaseRDKManager):
    """
    Class for managing stimulus structure i.e., shape, size and location of the stimuli

    Inhereting from base random dot kinematogram class and builds upon it with all new required methods
    """

    def __init__(self):
        super(RDKManager, self).__init__()
        pass


class DisplayManager(BaseDisplayManager):
    """
    Class for managing stimulus display
    """

    def __init__(self):
        super(DisplayManager, self).__init__()
        pass


class SessionManager:
    """
    Class for managing session structure i.e., trial sequence, graduation, and session level summary.
    """

    def __init__(self, config, subject=None):
        self.config = config
        self.task_pars = self.config.TASK_PARAMETERS
        self.subject = subject
        self.coh_to_xactive = None
        self.coh_to_xrange = None
        self.trial_schedule = []
        self.schedule_counter = 0
        self.full_coherences, self.coh_to_xrange = self.get_full_coherences()
        self.subject.prepare_run(self.full_coherences)
        self.subject_pars = self.subject.initiate_subject_parameters(
            self.full_coherences
        )
        self.next_coherence_level = self.subject_pars["current_coh_level"]
        self.stimulus_pars = {}

    def get_full_coherences(self):
        """
        Generates full direction-wise coherence array from input coherences list.
        Returns:
            full_coherences (list): List of all direction-wise coherences with adjustment for zero coherence (remove duplicates).
            coh_to_xrange (dict): Mapping dictionary from coherence level to corresponding x values for plotting of psychometric function
        """
        coherences = np.array(self.task_pars.stimulus._coherences.value)
        self.full_coherences = sorted(np.concatenate([coherences, -coherences]))
        if (
            0 in coherences
        ):  # If current full coherence contains zero, then remove one copy to avoid 2x 0 coh trials
            self.full_coherences.remove(0)
        self.coh_to_xrange = {
            coh: i for i, coh in enumerate(self.full_coherences)
        }  # mapping active coherences to x values for plotting purposes
        return self.full_coherences, self.coh_to_xrange

    def set_coherence_level(self):
        # Setting reward per pulse
        if 1.5 < self.subject_pars["reward_per_pulse"] < 3:
            if self.subject_pars["current_coherence_level"] < self.next_coherence_level:
                self.subject_pars["reward_per_pulse"] += 0.1
            if self.subject_pars["current_coherence_level"] > self.next_coherence_level:
                self.subject_pars["reward_per_pulse"] -= 0.1
        # Setting coherence level
        self.subject_pars["current_coherence_level"] = self.next_coherence_level
        # Setting mean reaction time for passive trials
        self.subject_pars["passive_rt_mu"] = 10 * (
            self.subject_pars["current_coherence_level"] - 1
        )
        # Setting active coherence indices
        self.subject_pars["active_coherences_indices"] = np.unique(
            np.concatenate(
                [
                    np.arange(0, self.subject_pars["current_coherence_level"]),
                    np.arange(
                        len(self.full_coherences)
                        - self.subject_pars["current_coherence_level"],
                        len(self.full_coherences),
                    ),
                ]
            )
        )  # Taking indices of currently active coherences to plot psychometric functions

    def generate_trials_schedule(self, *args, **kwargs):
        """
        Generating a block of trial to maintain psudo-random coherence selection with asserting all coherences are shown
        equally.
        Arguments:
        Returns:
            trials_scheduled (list): Schedule for next #(level*repeats) trials with psudo-random shuffling.
            coh_to_xactive (dict): Mapping dictionary from coherence to active x index value for plotting
        """
        # Resetting within trial_schedule counter
        self.schedule_counter = 0
        self.set_coherence_level()
        # Generate array of active signed-coherences based on current coherence level
        coherences = np.array(self.task_pars.stimulus._coherences.value)
        repeats_per_block = self.task_pars.stimulus.repeats_per_block.value
        active_coherences = sorted(
            np.concatenate(
                [
                    coherences[: self.subject_pars["current_coherence_level"]],
                    -coherences[: self.subject_pars["current_coherence_level"]],
                ]
            )
        )  # Signed coherence
        if 0 in active_coherences:
            active_coherences.remove(0)  # Removing one zero from the list
        self.coh_to_xactive = {
            key: self.coh_to_xrange[key] for key in active_coherences
        }  # mapping active coherences to active x values for plotting purposes
        self.trial_schedule = (
            active_coherences * repeats_per_block
        )  # Making block of Reps(3) trials per coherence

        # Active bias correction block by having unbiased side appear more
        for _, coh in enumerate(
            coherences[: self.subject_pars["current_coherence_level"]]
        ):
            if coh > self.task_pars.bias.active_correction.threshold:
                self.trial_schedule.remove(
                    coh * self.subject_pars["rolling_bias"]
                )  # Removing high coherence from biased direction (-1:left; 1:right)
                self.trial_schedule.append(
                    -coh * self.subject_pars["rolling_bias"]
                )  # Adding high coherence from unbiased direction.

        np.random.shuffle(self.trial_schedule)
        return self.trial_schedule, self.coh_to_xactive

    def next_trial(self, correction_trial):
        """
        Generate next trial based on trials_schedule. If not correction trial, increament trial index by one.
        If correction trial (passive/soft bias correction), choose next trial as probability to unbiased direction based on rolling bias.
        Arguments:
            correction_trial (bool): Is this a correction trial?
            rolling_bias (int): Rolling bias on last #x trials.
                                Below 0.5 means left bias, above 0.5 mean right bias
        Return:
            stimulus_pars (dict): returns dict of coherence_index, coherence, target_direction and
        """

        # If correction trial and above passive correction threshold
        if correction_trial:
            coherence = self.stimulus_pars["coherence"]
            if (
                self.stimulus_pars["coherence"]
                > self.task_pars.bias.passive_correction.threshold
            ):
                # Drawing incorrect trial from normal distribution with high prob to direction
                self.rolling_Bias = 0.5
                temp_bias = np.sign(np.random.normal(np.mean(self.rolling_Bias), 0.5))
                # Repeat probability to opposite side of bias
                coherence = int(-temp_bias) * np.abs(self.stimulus_pars["coherence"])

        else:
            # Generate new trial schedule if at the end of schedule
            if self.schedule_counter == 0 or self.schedule_counter == len(
                self.trial_schedule
            ):
                self.graduation_check()
                self.generate_trials_schedule()
            coherence = self.trial_schedule[self.schedule_counter]
            self.schedule_counter += 1  # Incrementing within trial_schedule counter

        self.stimulus_pars["index"] = self.coh_to_xrange[coherence]
        self.stimulus_pars["coherence"] = coherence
        self.stimulus_pars["target"] = np.sign(
            self.stimulus_pars["coherence"] + np.random.choice([-1e-2, 1e-2])
        )

        return self.stimulus_pars

    def graduation_check(self):
        # Deciding Coherence level based on rolling performance (50 trials of each coherence)
        accuracy = self.subject.rolling_perf["accuracy"]
        # Bi-directional shift in coherence level
        if self.config.TASK_PARAMETERS.training_type.graduation_direction.value == 0:
            # If 100% and 70% coherence have accuracy above 70%
            if all(np.array(accuracy[:2] > 0.7)) and all(np.array(accuracy[-2:] > 0.7)):
                # Increase coherence level to 3 i.e., introduce 36% coherence
                self.next_coherence_level = 3
                # If 100%, 70% and 36% coherence have accuracy above 70%
                if accuracy[2] > 0.7 and accuracy[-3] > 0.7:
                    # Increase coherence level to 3 i.e., introduce 36% coherence
                    self.next_coherence_level = 4
                    self.subject.rolling_perf["trial_counter_after_4th"] += 1

                    # 200 trials after 4th level
                    if self.subject.rolling_perf["trial_counter_after_4th"] > 200:
                        self.next_coherence_level = 5
                    # 400 trials after 4th level
                    if self.subject.rolling_perf["trial_counter_after_4th"] > 400:
                        self.next_coherence_level = 6
                    # 600 trials after 4th level
                    if self.subject.rolling_perf["trial_counter_after_4th"] > 600:
                        pass
                else:
                    self.subject.rolling_perf["trial_counter_after_4th"] = 0

        elif self.config.TASK_PARAMETERS.training_type.graduation_direction.value == 1:
            # If 100% and 70% coherence have accuracy above 70%
            if self.subject_pars["current_coherence_level"] > 3 or (
                all(np.array(accuracy[:2] > 0.7)) and all(np.array(accuracy[-2:] > 0.7))
            ):
                # Increase coherence level to 3 i.e., introduce 36% coherence
                self.next_coherence_level = 3
                # If 100%, 70% and 36% coherence have accuracy above 70%
                if self.subject_pars["current_coherence_level"] > 4 or (
                    accuracy[2] > 0.7 and accuracy[-3] > 0.7
                ):
                    # Increase coherence level to 3 i.e., introduce 36% coherence
                    self.next_coherence_level = 4
                    self.subject.rolling_perf["trial_counter_after_4th"] += 1
                    # 200 trials after 4th level
                    if self.subject.rolling_perf["trial_counter_after_4th"] > 200:
                        self.next_coherence_level = 5
                    # 400 trials after 4th level
                    if self.subject.rolling_perf["trial_counter_after_4th"] > 400:
                        self.next_coherence_level = 6
                    # 600 trials after 4th level
                    if self.subject.rolling_perf["trial_counter_after_4th"] > 600:
                        pass

    def update_EOT(self, correction_trial):
        """
        End of trial updates: Updating end of trial parameters such as psychometric function, chronometric function, total trials, rolling_perf
        bias, rolling_bias
        """
        if not correction_trial:
            self.subject.rolling_perf["index"][self.stimulus_pars["index"]] = (
                self.subject.rolling_perf["index"][self.stimulus_pars["index"]] + 1
            ) % self.subject.rolling_perf["window"]

    def update_EOS(self, total_trials, total_reward):
        """
        End of session updates: Updating all files and session parameters such as rolling performance
        """
        # Rolling performance
        self.subject.rolling_perf["current_coherence_level"] = self.subject_pars[
            "current_coherence_level"
        ]
        self.subject.rolling_perf["reward_per_pulse"] = self.subject_pars[
            "reward_per_pulse"
        ]
        self.subject.rolling_perf["total_trials"] = total_trials
        self.subject.rolling_perf["total_reward"] = total_reward
        self.subject.save()


class TrialRoutine(TrialConstruct):
    """
    Class for running trial structure i.e., how each trial should progress given `SessionManager`. Here we will run reaction time task.

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
        config=None,
        SessionManager=None,
        stimulus_handler=None,
        stage_block=None,
        **kwargs,
    ) -> None:
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
        # Gathering all parameters
        self.config = config
        self.task_pars = config.TASK_PARAMETERS
        # Event locks and triggers
        self.stage_block = stage_block
        self.response_block = threading.Event()
        self.response_block.clear()

        self.courier = queue.Queue()

        # Instantiate all objects
        self.session_manager = SessionManager(self.task_pars)
        self.hardware_manager = HardwareManager(self.config.HARDWARE)
        self.behavior = Behavior(
            hardware_manager=self.hardware_manager,
            stage_block=self.stage_block,
            response_block=self.response_block,
        )
        self.behavior.start()
        super(TrialRoutine, self).__init__(
            stage_block=self.stage_block,
            response_block=self.response_block,
            stimulus_handler=stimulus_handler,
            response_handler=self.behavior.response_handler,
        )

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
        self.stimulus_pars = None
        self.intertrial_duration = None

        # We make a list of the variables that need to be reset each trial, so it's easier to do
        self.resetting_variables = [self.response, self.response_time]

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
        self.trial_timer = time.time()
        self.fixation_duration = self.task_pars.timings.fixation.value
        self.fixation(duration=self.fixation_duration)
        # Get current trial properties
        if not self.correction_trial:
            self.current_trial = next(self.trial_counter)
        self.stimulus_pars = self.session_manager.next_trial(self.correction_trial)
        data = {
            "DC_timestamp": datetime.datetime.now().isoformat(),
            "trial_num": self.current_trial,
        }
        return data

    def stimulus_stage(self):
        """
        Stage 1: Show stimulus and wait for response trigger on target/distractor input
        Returns:
            data (dict):
            {
            }
        """
        print(2)
        # Set triggers, set display and start timer
        if self.task_pars.training_type.value < 2:
            self.stimulus_duration = (
                self.task_pars.training_type.active_passive.passive_rt_mu
                + (
                    pearson3.rvs(
                        self.task_pars.training_type.active_passive.passive_rt_sigma
                    )
                    * 1.5
                )
            )
        else:
            self.stimulus_duration = self.task_pars.timings.stimulus.max_viewing

        self.stimulus_rt(
            duration=self.stimulus_duration,
            min_viewing_duration=self.task_pars.timings.stimulus.min_viewing,
            arguments=self.stimulus_pars,
        )

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
        Shows stimulus (in this case, visual stimulus) for certain time after response has been made or response window is passed. This stage reinforces the stimulus-choice association.

        """

    def must_respond_to_proceed(self):
        """
        Returns:
            data (dict):
            {
            }
        """
        print(4)
        # Agent must consume reward before proceeding
        if self.correct:
            self.stage_block.clear()
            self.must_respond(targets=[self.stimulus_pars["target"]])
            # self.stage_block.wait()
        data = {
            "DC_timestamp": datetime.datetime.now().isoformat(),
            "trial_num": self.current_trial,
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
        print(5)
        self.intertrial(duration=self.intertrial_duration)
        self.trial_manager.update_EOT()

        data = {
            "DC_timestamp": datetime.datetime.now().isoformat(),
            "trial_num": self.current_trial,
            "TRIAL_END": True,
        }
        self.stage_block.wait()
        return data


class dynamic_training_rt:
    """
    Dynamic Training Routine
    """

    def __init__(self, stage_block, **kwargs):
        self.subject_id = None
        self.task_module = None
        self.task_phase = None
        self.__dict__.update(kwargs)

        import hydra

        directory = "protocols/RDK/config"
        filename = "dynamic_coherences.yaml"
        config = get_configuration(directory=directory, filename=filename)

        subject = Subject(
            name=self.subject_id,
            task_module=self.task_module,
            task_phase=self.task_phase,
            config=config,
        )

        a = SessionManager(config=config, subject=subject)
        a.subject.rolling_perf["accuracy"][:2] = 0.8
        a.subject.rolling_perf["accuracy"][-2:] = 0.8
        coherence = a.next_trial(None)
        coherence = a.next_trial(1)
        pass

    # TrialRoutine(
    #     config=config,
    #     session_manager=SessionManager,
    #     stimulus_handler=None,
    #     stage_block=stage_block,
    # )
    # a = SessionManager(config=config)
    # a.generate_trials_schedule()
    # a.next_trial()
    # pass

    # subject = Subject("PSUIM4", task_module="RDK", task_phase="dynamic_training")
    # pass
    # pass


if __name__ == "__main__":
    dynamic_training_rt(stage_block=threading.Event())
