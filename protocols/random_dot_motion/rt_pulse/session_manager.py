import csv
import multiprocessing as mp
import numpy as np
import pickle
import pandas as pd


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
        self.fixation_duration = None
        self.stimulus_duration = None
        self.minimum_viewing_duration = self.config.TASK["epochs"]["stimulus"]["min_viewing"]
        self.maximum_viewing_duration = self.config.TASK["epochs"]["stimulus"]["max_viewing"]
        self.reinforcement_duration = None
        self.delay_duration = None
        self.intertrial_duration = self.config.TASK["epochs"]["intertrial"]["duration"]
        # pulse variables
        self.pulse_probabilities = self.config.TASK["stimulus"]["pulse_probabilities"]["value"]
        self.pulse_onset = None
        self.pulse_duration = self.config.TASK["stimulus"]["pulse_duration"]["value"]
        self.pulse_coherence = None
        # stage onset variables
        self.fixation_onset = None
        self.stimulus_onset = None
        self.response_onset = None
        self.reinforcement_onset = None
        self.delay_onset = None
        self.intertrial_onset = None
        # behavior dependent function
        self.fixation_duration_function = self.config.TASK["epochs"]["fixation"]["duration"]
        self.reinforcement_duration_function = self.config.TASK["epochs"]["reinforcement"]["duration"]
        self.delay_duration_function = self.config.TASK["epochs"]["delay"]["duration"]
        # initialize session variables
        self.full_coherences = self.config.TASK["stimulus"]["signed_coherences"]["value"]
        self.active_coherences = self.full_coherences #self.config.TASK["stimulus"]["active_coherences"]["value"]
        self.active_coherence_indices = [np.where(self.full_coherences == value)[0][0] for value in self.active_coherences]
        self.coh_to_xrange = {coh: i for i, coh in enumerate(self.full_coherences)}
        # trial block
        self.block_schedule = []
        self.trials_in_block = 0
        self.repeats_per_block = self.config.TASK["stimulus"]["repeats_per_block"]["value"]
        # bias
        self.rolling_bias_index = 0
        self.bias_window = self.config.TASK["bias_correction"]["bias_window"]
        self.rolling_bias = np.zeros(self.bias_window)
        self.passive_bias_correction_threshold = self.config.TASK["bias_correction"]["repeat_threshold"]["passive"]
        self.active_bias_correction_threshold = self.config.TASK["bias_correction"]["repeat_threshold"]["active"]
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
            # pulse variables
            self.pulse_coherence,
            self.pulse_onset,
        ]

    ####################### pre-session methods #######################
    def update_reward_volume(self):
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
        # get fixation duration
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
            "pulse": self.generate_pulse_sequence(),
        }
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
            self.trial_reward = self.full_reward_volume
        else:
            self.trial_reward = None

        stage_task_args = {
            "reinforcement_duration": self.reinforcement_duration,
            "trial_reward": self.trial_reward,
            "reward_side": self.target,
            "FRR_reward": None,
        }
        return stage_task_args, stage_stimulus_args
    
    def prepare_delay_stage(self):
        stage_task_args, stage_stimulus_args = {}, {}
        self.delay_duration = self.delay_duration_function[self.outcome](self.response_time, self.signed_coherence)

        stage_task_args = {"delay_duration": self.delay_duration}
        return stage_task_args, stage_stimulus_args

    def prepare_intertrial_stage(self):
        stage_task_args, stage_stimulus_args = {}, {}
        stage_task_args = {"intertrial_duration": self.intertrial_duration, "monitor_response": [np.NaN]}              
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

    def generate_pulse_sequence(self):
        pulse_prob = self.pulse_probabilities[self.signed_coherence]
        cumulative_a = np.cumsum(pulse_prob)
        index = np.argmax(cumulative_a >= np.random.uniform())

        if index < 3:
            self.pulse_coherence = -100
        elif index < 6:
            self.pulse_coherence = 100
        else:
            self.pulse_coherence = self.signed_coherence
        
        if index % 3 == 0:
            self.pulse_onset = self.config.TASK["stimulus"]["pulse_onset"]['value']["early"]
        elif index % 3 == 1:
            self.pulse_onset = self.config.TASK["stimulus"]["pulse_onset"]['value']["middle"]
        else:
            self.pulse_onset = self.config.TASK["stimulus"]["pulse_onset"]['value']["late"]

        pulse = [(int(self.pulse_onset), self.pulse_coherence), (int(self.pulse_onset)+int(self.pulse_duration), self.signed_coherence)]
        
        return pulse


    def generate_block_schedule(self):
        self.block_schedule = np.repeat(self.active_coherences, self.repeats_per_block)
        if self.trial_counters["attempt"] == 0:
            # self.block_schedule = np.flip(self.block_schedule[np.argsort(np.abs(self.block_schedule))])
            self.block_schedule = self.shuffle_seq(np.repeat([-100, -72, 72, 100], 5), max_repeat=3) 
        else:
            np.random.shuffle(self.block_schedule)
            max_repeat_signs = 3
            self.block_schedule = self.shuffle_seq(self.block_schedule, max_repeat_signs)

    def shuffle_seq(self, sequence, max_repeat):
        """ Shuffle sequence so that no more than max_repeat consecutive elements have same sign"""
        for i in range(len(sequence) - max_repeat+1):
            subsequence = sequence[i:i + max_repeat]
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

        # write trial data to file
        self.write_trial_data_to_file()
        # if valid update trial variables and send data to terminal
        if self.valid:
            # update rolling bias
            self.rolling_bias[self.rolling_bias_index] = self.choice
            self.rolling_bias_index = (self.rolling_bias_index + 1) % self.bias_window

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
                self.plot_vars["running_accuracy"] = [self.trial_counters["valid"], 
                                            round(self.trial_counters["correct"]/ self.trial_counters["valid"] * 100, 2),
                                            self.outcome
                                            ]
            # update psychometric array
            self.plot_vars["psych"][self.signed_coherence] = round(self.plot_vars["chose_right"][self.signed_coherence] / tot_trials_in_coh, 2)

            # update total trial array
            self.plot_vars["trial_distribution"][self.signed_coherence] += 1

            # update reaction time array
            if np.isnan(self.plot_vars["response_time_distribution"][self.signed_coherence]):
                self.plot_vars["response_time_distribution"][self.signed_coherence] = round(self.response_time, 2)
            else:
                self.plot_vars["response_time_distribution"][self.signed_coherence] = round((
                    ((tot_trials_in_coh - 1) * self.plot_vars["response_time_distribution"][self.signed_coherence]) + self.response_time
                ) / tot_trials_in_coh,
                2)

        trial_data = {
            "is_valid": self.valid,
            "trial_counters": self.trial_counters,
            "reward_volume": round(self.full_reward_volume, 2),
            "trial_reward": round(self.trial_reward, 2) if self.trial_reward is not None else None,
            "total_reward": round(self.total_reward, 2),
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
            "intertrial_duration": self.intertrial_duration,
            "fixation_onset": self.fixation_onset,
            "stimulus_onset": self.stimulus_onset,
            "response_onset": self.response_onset,
            "reinforcement_onset": self.reinforcement_onset,
            "delay_onset": self.delay_onset,
            "intertrial_onset": self.intertrial_onset,
            "stimulus_seed": self.random_generator_seed,
            "pulse_onset": self.pulse_onset,
            "pulse_duration": self.pulse_duration,
            "pulse_coherence": self.pulse_coherence,
        }
        with open(self.config.FILES["trial"], "a+", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=data.keys())
            if file.tell() == 0:
                writer.writeheader()
            writer.writerow(data)

    def end_of_session_updates(self):
        self.config.SUBJECT["rolling_perf"]["reward_volume"] = self.full_reward_volume
        self.config.SUBJECT["rolling_perf"]["total_attempts"] = self.trial_counters["attempt"]
        self.config.SUBJECT["rolling_perf"]["total_reward"] = self.total_reward
        with open(self.config.FILES["rolling_perf_after"], "wb") as file:
            pickle.dump(self.config.SUBJECT["rolling_perf"], file)
        with open(self.config.FILES["rolling_perf"], "wb") as file:
            pickle.dump(self.config.SUBJECT["rolling_perf"], file)
        print("SAVING EOS FILES")

