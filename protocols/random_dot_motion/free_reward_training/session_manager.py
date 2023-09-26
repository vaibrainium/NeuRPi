import csv
import multiprocessing as mp
import numpy as np
import pickle
import pandas as pd

#TODO: 1. Use subject_config["session_uuid"] instead of subject name for file naming
#TODO: 5. Make sure graduation is working properly
#TODO: 6. Activate sound on display


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
        self.target = None
        self.choice = None
        self.response_time = None
        self.valid = None
        self.outcome = None
        self.full_reward_volume = self.config.SUBJECT["rolling_perf"]["reward_volume"]
        self.update_reward_volume()
        self.trial_reward = None # reward given on current trial
        self.total_reward = 0 # total reward given in session
        self.fixation_duration = None # self.config.TASK["epochs"]["fixation"]["duration"]
        self.stimulus_duration = None
        self.minimum_viewing_duration = self.config.TASK["epochs"]["stimulus"]["min_viewing"]
        self.passive_viewing_duration = None
        self.maximum_viewing_duration = self.config.TASK["epochs"]["stimulus"]["max_viewing"]
        self.reinforcement_duration = None
        self.delay_duration = None
        self.intertrial_duration = self.config.TASK["epochs"]["intertrial"]["duration"]
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

        # list of all variables needed to be reset every trial
        self.trial_reset_variables = [
            self.random_generator_seed,
            self.signed_coherence,
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
        ## weight based reward adjustment
        # % baseline weight is below 85% increase reward by 0.1 ul
        if self.config.SUBJECT["prct_weight"] < 85:
            self.full_reward_volume += 0.1
        # if % baseline weight is below 80% increase reward by another 0.1 ul
        if self.config.SUBJECT["prct_weight"] < 80:
            self.full_reward_volume += 0.1

        ## reward volume based reward adjustment
        if self.config.SUBJECT["rolling_perf"]["total_reward"] < 700:
            self.full_reward_volume += 0.1
            if self.config.SUBJECT["rolling_perf"]["total_reward"] < 500:
                self.full_reward_volume += 0.1

        ## Attempt based reward adjustment
        # if performed more than 200 trials on previous session, decrease reward by 0.1 ul
        if self.config.SUBJECT["rolling_perf"]["total_attempts"] > 200:
            self.full_reward_volume -= 0.1 

        ## limiting reward volume between 1.5 and 3
        self.full_reward_volume = np.clip(self.full_reward_volume, 1.5, 3)

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
        stage_stimulus_args = {}, 
        stage_task_args = {"fixation_duration": self.fixation_duration, "monitor_response": [np.NaN], "signed_coherence": self.signed_coherence}
        return stage_task_args, stage_stimulus_args

    def prepare_stimulus_stage(self):
        stage_task_args, stage_stimulus_args = {}, {}
        stage_stimulus_args = {
            "coherence": self.signed_coherence,
            "seed": self.random_generator_seed,
        }

        if self.training_type == 0: # passive-only training
            self.stimulus_duration = self.passive_viewing_function(self.current_coh_level)
            monitor_response = [self.target]
            print(f"Passive Stimulus Duration is {self.stimulus_duration}")
        elif self.training_type == 1: # active-passive training
            self.stimulus_duration = self.passive_viewing_function(self.current_coh_level)
            monitor_response = [-1, 1]
            print(f"Passive Stimulus Duration is {self.stimulus_duration}")
        elif self.training_type == 2: # active training
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
        stage_task_args, stage_stimulus_args = {}, {}
        self.choice = choice
        self.response_time = response_time
        
        # determining validity of the trial
        if not self.is_correction_trial and (not np.isnan(self.choice)): # if this is not a correction trial and there is a response
            self.valid = 1 # trial is valid
        else:
            self.valid = 0 # trial is invalid            

        # determining outcome of the trial
        if np.isnan(self.choice): # if no response
            self.outcome = "noresponse"
        elif self.choice == self.target: # if correct
            self.outcome = "correct"
        elif self.choice != self.target: # if incorrect
            self.outcome = "incorrect"
        stage_stimulus_args["outcome"] =  self.outcome

        # determine reinfocement duration and reward
        self.reinforcement_duration = self.reinforcement_duration_function[self.outcome](self.response_time)
        if self.outcome=="correct":
            # if invalid trial (i.e., correct repeat), give half reward_volume irrespective of training type
            if self.valid:
                self.trial_reward = self.full_reward_volume
                self.trial_reward = max(self.trial_reward, 1) # making sure reward is not below 1ul

            else:
                # If repeat trial give half reward. Should motivate to be more accurate but 
                # might also create bias by giving less reward on repeat trials which is most likely going to be opposite of biased direction
                self.trial_reward = self.full_reward_volume #/ 2
                self.trial_reward = max(self.trial_reward, 1) # making sure reward is not below 1ul
        else:
            self.trial_reward = None

        # making changes to typical reinforcement durations and reward based on training type and trial validity
        # if no response on passive/active-passive training assume correct trial durations and give half reward_volume
        if self.training_type < 2 and self.outcome=="noresponse":
            self.reinforcement_duration = self.reinforcement_duration_function["correct"](self.response_time)
            self.trial_reward = self.full_reward_volume / 2
            self.trial_reward = max(self.trial_reward, 1) # making sure reward is not below 1ul
            # msg to stimulus
            stage_stimulus_args["outcome"] = "correct"
        

        stage_task_args = {
            "reinforcement_duration": self.reinforcement_duration,
            "trial_reward": self.trial_reward,
            "reward_side": self.target,
        }

        return stage_task_args, stage_stimulus_args
    
    def prepare_delay_stage(self):
        stage_task_args, stage_stimulus_args = {}, {}

        if self.training_type < 2 and self.outcome=="noresponse":
            self.delay_duration = self.delay_duration_function["correct"](self.response_time)
        else:
            self.delay_duration = self.delay_duration_function[self.outcome](self.response_time)

        stage_task_args = {"delay_duration": self.delay_duration}
        return stage_task_args, stage_stimulus_args

    def prepare_intertrial_stage(self):
        stage_task_args, stage_stimulus_args = {}, {}
        stage_task_args = {"intertrial_duration": self.intertrial_duration}        
        return stage_task_args, stage_stimulus_args
    
    ######################### trial-stage methods #########################
    def prepare_trial_variables(self):
        if not self.is_correction_trial:    # if not correction trial
            # is this start of new trial block?
            if self.trials_in_block == 0 or self.trials_in_block == len(self.block_schedule):
                self.trials_in_block = 0
                self.generate_block_schedule()
            self.signed_coherence = self.block_schedule[self.trials_in_block]
            self.target = int(np.sign(self.signed_coherence + np.random.choice([-1e-2, 1e-2])))
            self.trials_in_block += 1 # incrementing within block counter
            self.trials_in_current_level += 1 # incrementing within level counter
            self.trial_counters["correction"] = 0 # resetting correction counter
        else:
            # drawing repeat trial with direction from a normal distribution with mean of against rolling bias
            self.target = int(np.sign(np.random.normal(-np.mean(self.rolling_bias), 0.5)))
            # Repeat probability to opposite side of bias
            self.signed_coherence = self.target * np.abs(self.signed_coherence)
            print(f"Rolling choices: {self.rolling_bias} with mean {np.mean(self.rolling_bias)} \n" 
                    f"Passive bias correction with: {self.signed_coherence}")
            # increment correction trial counter
            self.trial_counters["correction"] += 1


    def generate_block_schedule(self):
        self.block_schedule = np.repeat(self.active_coherences, self.repeats_per_block)
        # self.block_schedule = (list(self.active_coherences) * self.repeats_per_block)
        if self.trial_counters["attempt"] == 0:
            self.block_schedule = np.flip(self.block_schedule[np.argsort(np.abs(self.block_schedule))])
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
        """ Shuffle sequence so that no more than max_repeat consecutive elements have same sign"""
        for i in range(len(sequence) - max_repeat):
            subsequence = sequence[i:i + max_repeat+1]
            if len(set(np.sign(subsequence))) == 1:
                temp_block = sequence[i:]
                np.random.shuffle(temp_block)
                sequence[i:] = temp_block
        return sequence


    ####################### between-trial methods #######################
    
    def end_of_trial_updates(self):
        # function to finalize current trial and set parameters for next trial
        # codify trial outcome
        if self.outcome == "correct":
            self.outcome = 1
        elif self.outcome == "incorrect":
            self.outcome = 0
        elif self.outcome == "noresponse":
            self.outcome = np.NaN

        # update trial counters
        # count all attempts and response trials
        self.trial_counters["attempt"] += 1
        if np.isnan(self.outcome):
            self.trial_counters["noresponse"] += 1
        # if trial is valid then update valid, correct and incorrect counters
        if self.valid:
            self.trial_counters["valid"] += 1
            if self.outcome == 1:
                self.trial_counters["correct"] += 1
            elif self.outcome == 0:
                self.trial_counters["incorrect"] += 1

        # check if next trial is correction trial
        self.is_correction_trial = False
        # if incorrect and above passive correction threshold
        if self.outcome == 0 and np.abs(self.signed_coherence) > self.passive_bias_correction_threshold:
            self.is_correction_trial = True
        # if no response and no passive training
        if np.isnan(self.choice) and self.training_type >= 2:
            self.is_correction_trial = True
        
        # # if responded, update rolling bias
        # if not np.isnan(self.choice):
        #     self.rolling_bias[self.rolling_bias_index] = self.choice
        #     self.rolling_bias_index = (self.rolling_bias_index + 1) % self.bias_window

        # write trial data to file
        self.write_trial_data_to_file()
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
            if (self.trial_counters["correct"] + self.trial_counters["incorrect"] > 0):
                # self.plot_vars["running_accuracy"].append([self.trial_counters["valid"], 
                #                                            round(self.trial_counters["correct"]/ self.trial_counters["valid"] * 100, 2),
                #                                            self.outcome
                #                                            ])  
                self.plot_vars["running_accuracy"] = [self.trial_counters["valid"], 
                            round(self.trial_counters["correct"]/ self.trial_counters["valid"] * 100, 2),
                            self.outcome
                            ]
            # update psychometric array
            self.plot_vars["psych"][self.signed_coherence] = (
                self.plot_vars["chose_right"][self.signed_coherence] / tot_trials_in_coh
            )

            # update total trial array
            self.plot_vars["trial_distribution"][self.signed_coherence] += 1

            # update reaction time array
            if np.isnan(self.plot_vars["response_time_distribution"][self.signed_coherence]):
                self.plot_vars["response_time_distribution"][self.signed_coherence] = self.response_time
            else:
                self.plot_vars["response_time_distribution"][self.signed_coherence] = (
                    ((tot_trials_in_coh - 1) * self.plot_vars["response_time_distribution"][self.signed_coherence]) + self.response_time
                ) / tot_trials_in_coh

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
            }
        }
        return trial_data


    def write_trial_data_to_file(self):
        data = {
            "idx_attempt": self.trial_counters["attempt"],
            "idx_valid": self.trial_counters["valid"],
            "idx_correction": self.trial_counters["correction"],
            "is correction trial": self.is_correction_trial,
            "signed coherence": self.signed_coherence,
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
            "intertrial_duration": self.intertrial_duration,
            "fixation_onset": self.fixation_onset,
            "stimulus_onset": self.stimulus_onset,
            "response_onset": self.response_onset,
            "reinforcement_onset": self.reinforcement_onset,
            "delay_onset": self.delay_onset,
            "intertrial_onset": self.intertrial_onset,
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

