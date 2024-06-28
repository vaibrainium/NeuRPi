import csv
import multiprocessing as mp
import pickle

import numpy as np
import pandas as pd

# TODO: 1. Use subject_config["session_uuid"] instead of subject name for file naming
# TODO: 5. Make sure graduation is working properly
# TODO: 6. Activate sound on display


class SessionManager:
    """
    Class for managing session structure i.e., trial sequence, graduation, and session level summary.
    """

    def __init__(self, config):
        self.config = config

        # initialize trial variables
        # counters
        self.trial_counters = {
            "attempt": 0,
            "valid": 0,
            "correct": 0,
            "incorrect": 0,
            "noresponse": 0,
            "correction": 0,
        }

        # trial parameters
        self.random_generator_seed = None
        self.is_correction_trial = False
        self.signed_coherence = None
        self.audio_stim = None
        self.audio_volume = 1
        self.audio_loops = 0
        self.target = None
        self.choice = None
        self.response_time = None
        self.valid = None
        self.outcome = None
        self.full_reward_volume = self.config.SUBJECT["rolling_perf"]["reward_volume"]
        self.update_reward_volume()
        self.trial_reward = None  # reward given on current trial
        self.total_reward = 0  # total reward given in session
        self.fixation_duration = None  # self.config.TASK["epochs"]["fixation"]["duration"]
        self.stimulus_duration = None
        self.minimum_viewing_duration = self.config.TASK["epochs"]["stimulus"]["min_viewing"]
        self.passive_viewing_duration = None
        self.maximum_viewing_duration = self.config.TASK["epochs"]["stimulus"]["max_viewing"]
        self.reinforcement_duration = None
        self.delay_duration = None
        self.intertrial_duration = self.config.TASK["epochs"]["intertrial"]["duration"]
        self.trial_ITI_duration = None
        # stage onset variables
        self.fixation_onset = None
        self.stimulus_onset = None
        self.response_onset = None
        self.reinforcement_onset = None
        self.delay_onset = None
        self.intertrial_onset = None
        # behavior dependent function
        self.fixation_duration_function = self.config.TASK["epochs"]["fixation"]["duration"]
        self.passive_viewing_function = self.config.TASK["epochs"]["stimulus"]["passive_viewing"]
        self.reinforcement_duration_function = self.config.TASK["epochs"]["reinforcement"]["duration"]
        self.delay_duration_function = self.config.TASK["epochs"]["delay"]["duration"]
        # initialize session variables
        self.full_coherences = self.config.TASK["stimulus"]["signed_coherences"]["value"]
        self.coh_to_xrange = {coh: i for i, coh in enumerate(self.full_coherences)}
        self.training_type = self.config.TASK["training_type"]["value"]
        # trial block
        self.block_schedule = []
        self.trials_in_block = 0
        self.current_coh_level = self.config.SUBJECT["rolling_perf"]["current_coherence_level"]
        self.repeats_per_block = self.config.TASK["stimulus"]["repeats_per_block"]["value"]
        self.active_coherences = self.config.TASK["stimulus"]["active_coherences"]["value"]
        self.active_coherence_indices = [np.where(self.full_coherences == value)[0][0] for value in self.active_coherences]
        # rolling performance
        self.rolling_history_indices = self.config.SUBJECT["rolling_perf"]["history_indices"]
        self.rolling_history = self.config.SUBJECT["rolling_perf"]["history"]
        self.rolling_accuracy = self.config.SUBJECT["rolling_perf"]["accuracy"]
        self.rolling_window = self.config.TASK["rolling_performance"]["rolling_window"]
        # bias
        self.rolling_bias_index = 0
        self.bias_window = self.config.TASK["bias_correction"]["bias_window"]
        self.rolling_bias = np.zeros(self.bias_window)
        self.passive_bias_correction_threshold = self.config.TASK["bias_correction"]["repeat_threshold"]["passive"]
        self.active_bias_correction_threshold = self.config.TASK["bias_correction"]["repeat_threshold"]["active"]
        # graduation parameters
        self.trials_in_current_level = self.config.SUBJECT["rolling_perf"]["trials_in_current_level"]
        self.next_coh_level = self.current_coh_level
        self.active_coherences = self.config.TASK["stimulus"]["active_coherences"]["value"]
        self.active_coherence_indices = [np.where(self.full_coherences == value)[0][0] for value in self.active_coherences]

        # plot variables
        self.plot_vars = {
            "running_accuracy": [],
            "chose_right": {int(coh): 0 for coh in self.full_coherences},
            "chose_left": {int(coh): 0 for coh in self.full_coherences},
            "psych": {int(coh): np.NaN for coh in self.full_coherences},
            "trial_distribution": {int(coh): 0 for coh in self.full_coherences},
            "response_time_distribution": {int(coh): np.NaN for coh in self.full_coherences},
        }

        session_day = int(self.config.SUBJECT["session"].split("_")[0])
        self.audio_volume = np.clip((1 - ((session_day - 5) * 0.15)), 0, 1)  # volume decreases with number of trained days.
        # list of all variables needed to be reset every trial
        self.trial_reset_variables = [
            self.random_generator_seed,
            self.signed_coherence,
            self.audio_stim,
            self.target,
            self.choice,
            self.response_time,
            self.valid,
            self.outcome,
            self.trial_reward,
            # time related dynamic variables
            self.fixation_duration,
            self.stimulus_duration,
            self.reinforcement_duration,
            self.delay_duration,
            self.trial_ITI_duration,
            # epoch onsets
            self.fixation_onset,
            self.stimulus_onset,
            self.response_onset,
            self.reinforcement_onset,
            self.delay_onset,
            self.intertrial_onset,
        ]

    ####################### pre-session methods #######################
    def update_reward_volume(self):
        # function to update reward volume based on weight and previous session performance
        volume_change = 0
        ## weight based reward adjustment
        # # % baseline weight is below 85% increase reward by 0.1 ul
        # if self.config.SUBJECT["prct_weight"] < 85:
        #     volume_change += 0.1
        # if % baseline weight is below 80% increase reward by another 0.1 ul
        if self.config.SUBJECT["prct_weight"] < 80:
            volume_change += 0.1

        ## reward volume based reward adjustment
        if self.config.SUBJECT["rolling_perf"]["total_reward"] < 700:
            volume_change += 0.1
            if self.config.SUBJECT["rolling_perf"]["total_reward"] < 500:
                volume_change += 0.1

        ## Attempt based reward adjustment
        # if performed more than 200 trials on previous session, decrease reward by 0.1 ul
        if self.config.SUBJECT["rolling_perf"]["total_attempts"] > 200:
            volume_change -= 0.1

        self.full_reward_volume += np.clip(volume_change, -0.2, 0.2)

        ## limiting reward volume between 2 and 3.5
        self.full_reward_volume = np.clip(self.full_reward_volume, 1.5, 3.5)

    ####################### trial epoch methods #######################
    def prepare_fixation_stage(self):
        stage_task_args, stage_stimulus_args = {}, {}
        # resetting trial variables
        for var in self.trial_reset_variables:
            var = None
        # updating random generator seed
        self.random_generator_seed = np.random.randint(0, 1000000)
        # updating trial parameters
        self.prepare_trial_variables()
        # get fixation duratino
        self.fixation_duration = self.fixation_duration_function()
        # prepare args
        stage_stimulus_args = ({},)
        stage_task_args = {"fixation_duration": self.fixation_duration, "monitor_response": [np.NaN], "signed_coherence": self.signed_coherence}
        return stage_task_args, stage_stimulus_args

    def prepare_stimulus_stage(self):
        stage_task_args, stage_stimulus_args = {}, {}
        if self.signed_coherence == 0:
            self.audio_stim = None
        if np.sign(self.signed_coherence) > 0:
            self.audio_stim = "16KHz"
        elif np.sign(self.signed_coherence) < 0:
            self.audio_stim = "8KHz"

        stage_stimulus_args = {
            "coherence": self.signed_coherence,
            "seed": self.random_generator_seed,
            "audio_stim": self.audio_stim,
            "audio_volume": self.audio_volume,
        }

        if self.training_type == 0:  # passive-only training
            self.stimulus_duration = self.passive_viewing_function(self.current_coh_level)
            # TODO: passive should not take any response
            monitor_response = []
            print(f"Passive Stimulus Duration is {self.stimulus_duration}")
        elif self.training_type == 1:  # active-passive training
            self.stimulus_duration = self.passive_viewing_function(self.current_coh_level)
            # monitor_response = [self.target]
            monitor_response = [-1, 1]
            print(f"Passive Stimulus Duration is {self.stimulus_duration}")
        elif self.training_type == 2:  # active training
            self.stimulus_duration = self.maximum_viewing_duration
            monitor_response = [-1, 1]

        stage_task_args = {
            "coherence": self.signed_coherence,
            "target": self.target,
            "stimulus_duration": self.stimulus_duration,
            "minimum_viewing_duration": self.minimum_viewing_duration,
            "monitor_response": monitor_response,
        }
        return stage_task_args, stage_stimulus_args

    def prepare_reinforcement_stage(self, choice, response_time):
        """
        Prepares the reinforcement stage based on the choice and response time.

        Parameters:
        - choice: The choice made during the trial.
        - response_time: The time taken to make the response.

        Returns:
        - A tuple containing stage task arguments and stage stimulus arguments.
        """
        # Initialize arguments
        stage_task_args, stage_stimulus_args = {}, {}
        self.choice = choice
        self.response_time = response_time

        # Determine outcome
        if np.isnan(self.choice):
            self.outcome = np.NaN
        else:
            self.outcome = 1 if self.choice == self.target else 0

        # Determine trial reward and reinforcement duration and set stage stimulus arguments
        if self.outcome == 1:
            self.trial_reward = self.full_reward_volume
            self.reinforcement_duration = self.reinforcement_duration_function["correct"](self.response_time)
            stage_stimulus_args["outcome"] = "correct"
        elif self.outcome == 0:
            self.trial_reward = 0
            self.reinforcement_duration = self.reinforcement_duration_function["incorrect"](self.response_time)
            stage_stimulus_args["outcome"] = "incorrect"
        elif np.isnan(self.choice):
            if self.training_type == 0:
                self.trial_reward = self.full_reward_volume
                self.reinforcement_duration = self.reinforcement_duration_function["correct"](self.response_time)
                stage_stimulus_args["outcome"] = "correct"
            elif self.training_type == 1:
                self.trial_reward = 1
                self.reinforcement_duration = self.reinforcement_duration_function["correct"](self.response_time)
                stage_stimulus_args["outcome"] = "correct"
            elif self.training_type == 2:
                self.trial_reward = 0
                self.reinforcement_duration = self.reinforcement_duration_function["noresponse"](self.response_time)
                stage_stimulus_args["outcome"] = "noresponse"

        # Set stage task arguments
        stage_task_args = {
            "reinforcement_duration": self.reinforcement_duration,
            "trial_reward": self.trial_reward,
            "reward_side": self.target,
        }
        return stage_task_args, stage_stimulus_args

    def prepare_delay_stage(self):
        stage_task_args, stage_stimulus_args = {}, {}
        outcome = {1: "correct", 0: "incorrect", np.NaN: "noresponse"}

        if self.training_type < 2 and np.isnan(self.outcome):
            self.delay_duration = self.delay_duration_function["correct"](self.response_time)
        else:
            self.delay_duration = self.delay_duration_function[outcome.get(self.outcome)](self.response_time)

        stage_task_args = {"delay_duration": self.delay_duration}
        return stage_task_args, stage_stimulus_args

    def prepare_intertrial_stage(self):
        stage_task_args, stage_stimulus_args = {}, {}
        # if 3rd attempt and not correct, then give higher ITI to take rest
        if (self.outcome != 1) and (self.trial_counters["correction"] % 3 == 4):
            self.trial_ITI_duration = 20  # 20 secs ITI for 3 incorrect attempts in a loop for easy condition
        else:
            self.trial_ITI_duration = self.intertrial_duration
        stage_task_args = {"intertrial_duration": self.trial_ITI_duration, "monitor_response": [np.NaN]}
        return stage_task_args, stage_stimulus_args

    ######################### trial-stage methods #########################
    def prepare_trial_variables(self):
        if not self.is_correction_trial:  # if not correction trial
            # is this start of new trial block?
            if self.trials_in_block == 0 or self.trials_in_block == len(self.block_schedule):
                self.trials_in_block = 0
                self.generate_block_schedule()
            self.signed_coherence = self.block_schedule[self.trials_in_block]
            self.target = int(np.sign(self.signed_coherence + np.random.choice([-1e-2, 1e-2])))
            self.trials_in_block += 1  # incrementing within block counter
            self.trials_in_current_level += 1  # incrementing within level counter
            self.trial_counters["correction"] = 0  # resetting correction counter
        else:
            # drawing repeat trial with direction from a normal distribution with mean of against rolling bias
            self.target = int(np.sign(np.random.normal(-np.mean(self.rolling_bias) * 2, 0.4)))
            # Repeat probability to opposite side of bias
            self.signed_coherence = self.target * np.abs(self.signed_coherence)
            print(f"Rolling choices: {self.rolling_bias} with mean {np.mean(self.rolling_bias)} \n" f"Passive bias correction with: {self.signed_coherence}")
            # increment correction trial counter
            self.trial_counters["correction"] += 1

    def generate_block_schedule(self):
        self.block_schedule = np.repeat(self.active_coherences, self.repeats_per_block)
        if self.trial_counters["attempt"] == 0:
            # np.flip(self.block_schedule[np.argsort(np.abs(self.block_schedule))])
            self.block_schedule = self.shuffle_seq(np.repeat([-100, -72, 72, 100], 5), max_repeat=3)
        else:
            np.random.shuffle(self.block_schedule)

            # TODO: active bias correction needed?
            # swap coherence direction to unbiased side if coherence is above active threshold
            # for _, coh in enumerate(
            #     coherences[: self.subject_config["current_coherence_level"]]
            # ):
            #     if np.abs(coh) > self.config.TASK["bias"]["active_correction"]["threshold"]:
            #         self.trial_schedule.remove(
            #             coh * self.subject_config["rolling_bias"]
            #         )  # Removing high coherence from biased direction (-1:left; 1:right)
            #         self.trial_schedule.append(
            #             -coh * self.subject_config["rolling_bias"]
            #         )  # Adding high coherence from unbiased direction.

            max_repeat_signs = 3
            self.block_schedule = self.shuffle_seq(self.block_schedule, max_repeat_signs)

    def shuffle_seq(self, sequence, max_repeat):
        """Shuffle sequence so that no more than max_repeat consecutive elements have same sign"""
        for i in range(len(sequence) - max_repeat + 1):
            subsequence = sequence[i : i + max_repeat]
            if len(set(np.sign(subsequence))) == 1:
                temp_block = sequence[i:]
                np.random.shuffle(temp_block)
                sequence[i:] = temp_block
        return sequence

    ####################### between-trial methods #######################

    def end_of_trial_updates(self):
        # function to finalize current trial and set parameters for next trial
        next_trial_vars = {"is_correction_trial": False}

        self.trial_counters["attempt"] += 1
        if self.outcome == 1:
            if not self.is_correction_trial:  # Not a correction trial
                self.valid = True
                self.trial_counters["valid"] += 1
                self.trial_counters["correct"] += 1
            else:
                self.valid = False
            next_trial_vars["is_correction_trial"] = False

        elif self.outcome == 0:
            if not self.is_correction_trial:
                self.valid = True
                self.trial_counters["valid"] += 1
                self.trial_counters["incorrect"] += 1
            else:
                self.valid = False
            # Determine if a correction trial is needed based on signed coherence
            next_trial_vars["is_correction_trial"] = np.abs(self.signed_coherence) > self.passive_bias_correction_threshold

        elif np.isnan(self.outcome):
            self.valid = False
            self.trial_counters["noresponse"] += 1
            if self.training_type == 0:
                next_trial_vars["is_correction_trial"] = False
            elif self.training_type == 1:
                next_trial_vars["is_correction_trial"] = False
            elif self.training_type == 2:
                next_trial_vars["is_correction_trial"] = True

        # write trial data to file
        self.write_trial_data_to_file()
        self.is_correction_trial = next_trial_vars["is_correction_trial"]

        # if valid update trial variables and send data to terminal
        if self.valid:
            # update rolling bias
            self.rolling_bias[self.rolling_bias_index] = self.choice
            self.rolling_bias_index = (self.rolling_bias_index + 1) % self.bias_window
            # update rolling choice history
            idx = self.rolling_history_indices[str(self.signed_coherence)]
            self.rolling_history[str(self.signed_coherence)][idx] = self.outcome
            self.rolling_accuracy[str(self.signed_coherence)] = np.mean(self.rolling_history[str(self.signed_coherence)])
            self.rolling_history_indices[str(self.signed_coherence)] = (self.rolling_history_indices[str(self.signed_coherence)] + 1) % self.rolling_window

            # update plot parameters
            if self.choice == -1:
                # computing left choices coherence-wise
                self.plot_vars["chose_left"][self.signed_coherence] += 1
            elif self.choice == 1:
                # computing right choices coherence-wise
                self.plot_vars["chose_right"][self.signed_coherence] += 1

            tot_trials_in_coh = self.plot_vars["chose_left"][self.signed_coherence] + self.plot_vars["chose_right"][self.signed_coherence]

            # update running accuracy
            if self.trial_counters["correct"] + self.trial_counters["incorrect"] > 0:
                # self.plot_vars["running_accuracy"].append([self.trial_counters["valid"],
                #                                            round(self.trial_counters["correct"]/ self.trial_counters["valid"] * 100, 2),
                #                                            self.outcome
                #                                            ])
                self.plot_vars["running_accuracy"] = [
                    self.trial_counters["valid"],
                    round(self.trial_counters["correct"] / self.trial_counters["valid"] * 100, 2),
                    self.outcome,
                ]
            # update psychometric array
            self.plot_vars["psych"][self.signed_coherence] = self.plot_vars["chose_right"][self.signed_coherence] / tot_trials_in_coh

            # update total trial array
            self.plot_vars["trial_distribution"][self.signed_coherence] += 1

            # update reaction time array
            if np.isnan(self.plot_vars["response_time_distribution"][self.signed_coherence]):
                self.plot_vars["response_time_distribution"][self.signed_coherence] = self.response_time
            else:
                self.plot_vars["response_time_distribution"][self.signed_coherence] = (((tot_trials_in_coh - 1) * self.plot_vars["response_time_distribution"][self.signed_coherence]) + self.response_time) / tot_trials_in_coh

        trial_data = {
            "is_valid": self.valid,
            "trial_counters": self.trial_counters,
            "reward_volume": self.full_reward_volume,
            "trial_reward": self.trial_reward,
            "total_reward": self.total_reward,
            "plots": {
                "running_accuracy": self.plot_vars["running_accuracy"],
                "psychometric_function": self.plot_vars["psych"],
                "trial_distribution": self.plot_vars["trial_distribution"],
                "response_time_distribution": self.plot_vars["response_time_distribution"],
            },
        }
        return trial_data

    def write_trial_data_to_file(self):
        data = {
            "idx_attempt": self.trial_counters["attempt"],
            "idx_valid": self.trial_counters["valid"],
            "idx_correction": self.trial_counters["correction"],
            "is_correction_trial": self.is_correction_trial,
            "signed_coherence": self.signed_coherence,
            "target": self.target,
            "choice": self.choice,
            "response_time": self.response_time,
            "is_valid": self.valid,
            "outcome": self.outcome,
            "trial_reward": self.trial_reward,
            "fixation_duration": self.fixation_duration,
            "stimulus_duration": self.stimulus_duration,
            "reinforcement_duration": self.reinforcement_duration,
            "delay_duration": self.delay_duration,
            "intertrial_duration": self.trial_ITI_duration,
            "fixation_onset": self.fixation_onset,
            "stimulus_onset": self.stimulus_onset,
            "response_onset": self.response_onset,
            "reinforcement_onset": self.reinforcement_onset,
            "delay_onset": self.delay_onset,
            "intertrial_onset": self.intertrial_onset,
            "stimulus_seed": self.random_generator_seed,
        }
        with open(self.config.FILES["trial"], "a+", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=data.keys())
            if file.tell() == 0:
                writer.writeheader()
            writer.writerow(data)

    def end_of_session_updates(self):
        self.config.SUBJECT["rolling_perf"]["current_coherence_level"] = self.current_coh_level
        self.config.SUBJECT["rolling_perf"]["reward_volume"] = self.full_reward_volume
        self.config.SUBJECT["rolling_perf"]["total_attempts"] = self.trial_counters["attempt"]
        self.config.SUBJECT["rolling_perf"]["total_reward"] = self.total_reward
        self.config.SUBJECT["rolling_perf"]["trials_in_current_level"] = self.trials_in_current_level
        self.config.SUBJECT["rolling_perf"]["history_indices"] = self.rolling_history_indices
        self.config.SUBJECT["rolling_perf"]["history"] = self.rolling_history
        self.config.SUBJECT["rolling_perf"]["accuracy"] = self.rolling_accuracy
        with open(self.config.FILES["rolling_perf_after"], "wb") as file:
            pickle.dump(self.config.SUBJECT["rolling_perf"], file)
        with open(self.config.FILES["rolling_perf"], "wb") as file:
            pickle.dump(self.config.SUBJECT["rolling_perf"], file)
        print("SAVING EOS FILES")
