import csv
import datetime
import itertools
import multiprocessing as mp
import queue
import threading
import time

import numpy as np
from scipy.stats import pearson3

from NeuRPi.prefs import prefs
from NeuRPi.utils.get_config import get_configuration
from protocols.random_dot_motion.data_model.subject import Subject
from protocols.random_dot_motion.hardware.behavior import Behavior
from protocols.random_dot_motion.hardware.hardware_manager import HardwareManager
from protocols.random_dot_motion.tasks.rt_task import RTTask


class SessionManager:
    """
    Class for managing session structure i.e., trial sequence, graduation, and session level summary.
    """

    def __init__(self, config, subject=None):
        self.config = config
        self.subject = subject
        self.coh_to_xactive = None
        self.coh_to_xrange = None
        self.trial_schedule = []
        self.schedule_counter = 0
        self.full_coherences, self.coh_to_xrange = self.get_full_coherences()
        self.subject.prepare_run(self.full_coherences)
        self.subject_pars = self.subject.initiate_parameters(self.full_coherences)
        self.next_coherence_level = self.subject_pars["current_coh_level"]
        self.stimulus_pars = {}

    def get_full_coherences(self):
        """
        Generates full direction-wise coherence array from input coherences list.
        Returns:
            full_coherences (list): List of all direction-wise coherences with adjustment for zero coherence (remove duplicates).
            coh_to_xrange (dict): Mapping dictionary from coherence level to corresponding x values for plotting of psychometric function
        """
        coherences = np.array(self.config.TASK.stimulus._coherences.value)
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
        if 1.5 < self.subject_pars["reward"] < 3:
            if self.subject_pars["current_coherence_level"] < self.next_coherence_level:
                self.subject_pars["reward"] += 0.25
            if self.subject_pars["current_coherence_level"] > self.next_coherence_level:
                self.subject_pars["reward"] -= 0.25
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
        coherences = np.array(self.config.TASK.stimulus._coherences.value)
        repeats_per_block = self.config.TASK.stimulus.repeats_per_block.value
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
            if coh > self.config.TASK.bias.active_correction.threshold:
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
        Return:
            stimulus_pars (dict): returns dict of coherence_index, coherence, and target_direction
        """

        # If correction trial and above passive correction threshold
        if correction_trial:
            coherence = self.stimulus_pars["coherence"]
            if (
                self.stimulus_pars["coherence"]
                > self.config.TASK.bias.passive_correction.threshold
            ):
                # Drawing incorrect trial from normal distribution with high prob to direction
                temp_bias = np.sign(
                    np.random.normal(np.mean(self.subject_pars["rolling_bias"]), 0.5)
                )
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
        self.stimulus_pars["target"] = int(
            np.sign(self.stimulus_pars["coherence"] + np.random.choice([-1e-2, 1e-2]))
        )
        return self.stimulus_pars

    def graduation_check(self):
        # Deciding Coherence level based on rolling performance (50 trials of each coherence)
        accuracy = self.subject.rolling_perf["accuracy"]
        # Bi-directional shift in coherence level
        if self.config.TASK.training_type.graduation_direction.value == 0:
            # If 100% and 70% coherence have accuracy above 70%
            if all(np.array(accuracy[:2]) > 0.7) and all(np.array(accuracy[-2:]) > 0.7):
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

        elif self.config.TASK.training_type.graduation_direction.value == 1:
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

    def update_EOT(self, response, response_time, outcome):
        """
        End of trial updates: Updating end of trial parameters such as psychometric function, chronometric function, total trials, rolling_perf
        bias, rolling_bias
        """
        coh_index, coh = (
            self.stimulus_pars["index"],
            self.stimulus_pars["coherence"],
        )

        # updating rolling bias
        self.subject_pars["rolling_bias"][
            self.subject_pars["rolling_bias_index"]
        ] = response
        self.subject_pars["rolling_bias_index"] = (
            self.subject_pars["rolling_bias_index"] + 1
        ) % self.subject_pars["rolling_bias_window"]

        # uptading rolling performance
        ## update history block
        self.subject.rolling_perf["hist_" + str(coh)][
            self.subject.rolling_perf["index"][coh_index]
        ] = outcome
        ## calculate accuracy
        self.subject.rolling_perf["accuracy"][coh_index] = np.mean(
            self.subject.rolling_perf["hist_" + str(coh)]
        )
        ## update index
        self.subject.rolling_perf["index"][coh_index] = (
            self.subject.rolling_perf["index"][coh_index] + 1
        ) % self.subject.rolling_perf["window"]

        # Updating plot parameters
        if response == -1:
            # computing left choices coherence-wise
            self.config.SUBJECT.psych_left[coh_index] += 1
        elif response == 1:
            # computing right choices coherence-wise
            self.config.SUBJECT.psych_right[coh_index] += 1
        tot_trials_in_coh = (
            self.config.SUBJECT.psych_left[coh_index]
            + self.config.SUBJECT.psych_right[coh_index]
        )

        # update running accuracy
        if (
            self.config.SUBJECT.counters["correct"]
            + self.config.SUBJECT.counters["incorrect"]
            > 0
        ):
            self.config.SUBJECT.running_accuracy.append(
                [
                    self.config.SUBJECT.counters["valid"],
                    self.config.SUBJECT.counters["correct"]
                    / (
                        self.config.SUBJECT.counters["correct"]
                        + self.config.SUBJECT.counters["incorrect"]
                    ),
                    outcome,
                ]
            )

        # update psychometric array
        self.config.SUBJECT.psych[coh_index] = (
            self.config.SUBJECT.psych_right[coh_index] / tot_trials_in_coh
        )

        # update total trial array
        self.config.SUBJECT.trial_distribution[coh_index] += 1

        # update reaction time array
        if np.isnan(self.config.SUBJECT.response_time_distribution[coh_index]):
            self.config.SUBJECT.response_time_distribution[coh_index] = response_time
        else:
            if True:  # self.coh_to_xrange, self.coh_to_xactive
                self.config.SUBJECT.response_time_distribution[coh_index] = (
                    (
                        (tot_trials_in_coh - 1)
                        * self.config.SUBJECT.response_time_distribution[coh_index]
                    )
                    + response_time
                ) / tot_trials_in_coh

    def update_EOS(self):
        """
        End of session updates: Updating all files and session parameters such as rolling performance
        """
        # Rolling performance
        self.subject.rolling_perf[
            "current_coh_level"
        ] = self.config.SUBJECT.current_coh_level
        self.subject.rolling_perf["reward"] = self.config.SUBJECT.reward
        self.subject.rolling_perf[
            "total_attempts"
        ] = self.config.SUBJECT.counters.attempt
        self.subject.rolling_perf["total_reward"] = self.config.SUBJECT.total_reward
        self.subject.save()
        print("SAVING EOS FILES")


class Task:
    """
    Dynamic Training Routine with reaction time trial structure
    """

    def __init__(
        self,
        stage_block=None,
        subject=None,
        task_module=None,
        task_phase=None,
        config=None,
        **kwargs,
    ):

        self.subject = subject
        self.task_module = task_module
        self.task_phase = task_phase
        self.config = config
        self.__dict__.update(kwargs)

        # # Preparing parameters parameters
        # directory = "protocols/RDK/config"
        # filename = "dynamic_coherences_rt.yaml"
        # self.config = get_configuration(directory=directory, filename=filename)

        # Preparing subject
        self.subject = Subject(
            name=self.subject,
            task_module=self.task_module,
            task_phase=self.task_phase,
            config=self.config,
        )

        # Event locks, triggers
        self.stage_block = stage_block
        self.response_block = threading.Event()
        self.response_block.clear()

        self.timers = {
            "session": datetime.datetime.now(),
            "trial": datetime.datetime.now(),
        }
        # # Preparing Managers
        self.managers = {}
        self.managers["hardware"] = HardwareManager()

        self.managers["behavior"] = Behavior(
            hardware_manager=self.managers["hardware"],
            response_block=self.response_block,
            response_log=self.subject.lick,
            timers=self.timers,
        )

        self.managers["session"] = SessionManager(
            subject=self.subject,
            config=self.config,
        )

        self.managers["trial"] = RTTask(
            stage_block=self.stage_block,
            response_block=self.response_block,
            stimulus_queue=self.stimulus_queue,
            managers=self.managers,
            subject=self.subject,
            config=self.config,
            timers=self.timers,
        )

        self.stages = self.managers["trial"].stages

        # Starting required managers
        self.managers["behavior"].start()

    # Reward management from GUI
    def manage_hardware(self, message: dict):
        """Handle hardware request from terminal based on received message"""
        # Reward related changes
        if message["key"] == "reward_left":
            self.managers["hardware"].reward_left(message["value"])
            self.config.SUBJECT.total_reward += message["value"]
            print(f'REWARDED LEFT with {message["value"]}')
        elif message["key"] == "reward_right":
            self.managers["hardware"].reward_right(message["value"])
            self.config.SUBJECT.total_reward += message["value"]
            print(f'REWARDED RIGHT with {message["value"]}')
        elif message["key"] == "toggle_left_reward":
            self.managers["hardware"].toggle_reward("Left")
        elif message["key"] == "toggle_right_reward":
            self.managers["hardware"].toggle_reward("Right")
        elif message["key"] == "update_reward":
            self.config.SUBJECT.reward = message["value"]
            print(f"NEW REWARD VALUE IS {self.config.SUBJECT.reward}")
        elif message["key"] == "caliberate_reward":
            if self.config.SUBJECT.name in ["XXX", "xxx"]:
                self.managers["hardware"].start_caliberation_sequence()

        # Lick related changes
        elif message["key"] == "reset_lick_sensor":
            self.managers["hardware"].reset_lick_sensor()
            print(f"RESETTING LICK SENSOR")
        elif message["key"] == "update_lick_threshold_left":
            self.managers["hardware"].lick_threshold_left = message["value"]
            print(f'UPDATED LEFT LICK THRESHOLD with {message["value"]}')
            print(self.managers["hardware"].lick_threshold_left)
        elif message["key"] == "update_lick_threshold_right":
            self.managers["hardware"].lick_threshold_right = message["value"]
            print(f'UPDATED RIGHT LICK THRESHOLD with {message["value"]}')
            print(self.managers["hardware"].lick_threshold_right)

    def pause_session(self):
        pass

    def end_session(self):
        self.managers["session"].update_EOS()
        self.managers["behavior"].stop()


if __name__ == "__main__":
    value = {
        "task_module": "RDK",
        "task_phase": "rt_dynamic_training",
        "subject": "PSUIM4",
    }

    Task(stage_block=threading.Event(), **value)
