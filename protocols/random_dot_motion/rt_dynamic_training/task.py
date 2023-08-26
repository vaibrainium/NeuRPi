import csv
import datetime
import itertools
import multiprocessing as mp
import queue
import threading
import time
from pathlib import Path
import numpy as np
from scipy.stats import pearson3
import pickle

from NeuRPi.prefs import prefs
from protocols.random_dot_motion.core.hardware.behavior import Behavior
from protocols.random_dot_motion.core.hardware.hardware_manager import \
    HardwareManager
from protocols.random_dot_motion.core.task.rt_task import RTTask

#TODO: 1. Use subject_config["session_uuid"] instead of subject name for file naming
#TODO: 2. Make reward adjustment for all invalid trials including repeat trials
#TODO: 5. Make sure graduation is working properly
#TODO: 6. Activate sound on display


class SessionManager:
    """
    Class for managing session structure i.e., trial sequence, graduation, and session level summary.
    """
    def __init__(self, config, subject_config):
        self.config = config
        self.subject_config = subject_config
        self.coh_to_xactive = None
        self.coh_to_xrange = None

        # initialize trial variables
        # counters
        self.attempt_counter = itertools.count()
        self.valid_counter = itertools.count()
        self.correct_counter = itertools.count()
        self.incorrect_counter = itertools.count()
        self.noresponse_counter = itertools.count()
        self.correction_counter = itertools.count()
        # trial parameters
        self.random_generator_seed = None
        self.is_correction_trial = False
        self.signed_coherence = None
        self.target = None
        self.choice = None
        self.response_time = None
        self.outcome = None
        self.reward_volume = self.config.SUBJECT["rolling_perf"]["reward_volume"]
        self.fixation_duration = self.config.TASK["epochs"]["fixation"]["duration"]
        self.stimulus_duration = None
        self.minimum_viewing_duration = self.config.TASK["epochs"]["stimulus"]["min_viewing"]
        self.passive_viewing_duration = None
        self.maximum_viewing_duration = self.config.TASK["epochs"]["stimulus"]["max_viewing"]
        self.reinforcement_duration = self.config.TASK["epochs"]["reinforcement"]["duration"]
        self.intertrial_duration = None
        # behavior dependent function
        self.passive_viewing_function = self.config.TASK["epochs"]["stimulus"]["passive_viewing"]
        self.intertrial_duration_function = self.config.TASK["epochs"]["intertrial"]["duration"]

        # initialize session variables
        self.full_coherences = self.config.TASK["stimulus"]["signed_coherences"]["value"]
        self.coh_to_xrange = {coh: i for i, coh in enumerate(self.full_coherences)}
        self.training_type = self.config.TASK["training_type"]["value"]
        # trial block
        self.block_schedule = []
        self.trials_in_block = itertools.count()
        self.current_coh_level = self.config.SUBJECT["rolling_perf"]["current_coherence_level"]
        self.repeats_per_block = self.config.TASK["stimulus"]["repeats_per_block"]["value"]
        self.active_coherences = self.config.TASK["stimulus"]["active_coherences"]["value"]
        self.active_coherence_indices = [np.where(self.full_coherences == value)[0][0] for value in self.active_coherences]
        # rolling performance
        self.rolling_bias = np.zeros(self.config.TASK["bias_correction"]["rolling_window"])
        self.rolling_history = self.config.SUBJECT["rolling_perf"]["history"]["value"]
        self.rolling_accuracy = self.config.SUBJECT["rolling_perf"]["accuracy"]["value"]
        # bias
        self.passive_bias_correction_threshold = self.config.TASK["bias_correction"]["repeat_threshold"]["passive"]
        self.active_bias_correction_threshold = self.config.TASK["bias_correction"]["repeat_threshold"]["active"]
        self.bias_window = self.config.TASK["bias_correction"]["window"]["value"]
        # TODO: To fully adapt line below to current data, we need to change variable name in rolling_perf for all subjects
        self.trials_in_current_level = itertools.count(self.config.SUBJECT["rolling_perf"]["trial_counter_after_4th"])
        self.next_coh_level = self.current_coh_level
        # graduation parameters
        self.active_coherences_by_level = self.config.GRADUATION["coherences"]["value"]
        self.active_coherences = self.active_coherences_by_level[self.current_coh_level]
        self.active_coherence_indices = [np.where(self.full_coherences == value)[0][0] for value in self.active_coherences]
        self.graduation_direction = self.config.GRADUATION["direction"]["value"]
        self.accuracy_thresholds = self.config.GRADUATION["accuracy"]["thresholds"]["value"]
        self.trials_threshold = self.config.GRADUATION["trials_threshold"]["value"]

        # list of all variables needed to be reset every trial
        self.trial_reset_variables = [
            self.random_generator_seed,
            self.signed_coherence,
            self.target,
            self.choice,
            self.response_time,
            self.outcome,
            self.stimulus_duration,
            self.intertrial_duration,  
        ]

    ####################### trial epoch methods #######################
    def prepare_fixation_epoch(self):
        # resetting trial variables
        for var in self.trial_reset_variables:
            var = None
        # updating attempt counter and random generator seed
        self.attempt_counter = next(self.attempt_counter)
        self.random_generator_seed = np.random.randint(0, 1000000)
        # updating trial parameters
        self.prepare_trial_variables()       
        # prepare args
        epoch_display_args = {}, 
        epoch_task_args = {"fixation_duration": self.fixation_duration, "monitor_response": [np.NaN], "signed_coherece": self.signed_coherence}
        return epoch_task_args, epoch_display_args

    def prepare_stimulus_epoch(self):
        epoch_display_args = {
            "coherence": self.signed_coherence,
            "seed": self.random_generator_seed,
        }

        if self.training_type == 0: # passive-only training
            self.stimulus_duration = self.passive_viewing_function(self.current_coh_level)
            monitor_response = [self.target]
        elif self.training_type == 1: # active-passive training
            self.stimulus_duration = self.passive_viewing_function(self.current_coh_level)
            monitor_response = [-1, 1]
        elif self.training_type == 2: # active training
            self.stimulus_duration = self.maximum_viewing_duration
            monitor_response = [-1, 1]
        
        epoch_task_args = {
            "coherence": self.signed_coherence,
            "target": self.target,
            "stimulus_duration": self.stimulus_duration,
            "minimum_viewing_duration": self.minimum_viewing_duration,
            "monitor_response": monitor_response,
        }
        return epoch_task_args, epoch_display_args


    def prepare_reinforcement_epoch(self, choice, response_time):
        START REINFORCEMENT WORK
        # TODO: START REINFORCEMENT WORK
        
        if not choice:
            valid, correct, incorrect, noresponse = 0, 0, 0, 1
        elif choice == self.target:
            valid, correct, incorrect, noresponse = 1, 1, 0, 0
        elif choice != self.target:
            valid, correct, incorrect, noresponse = 1, 0, 1, 0

        if self.training_type < 2: # passive/active-passive training
            if choice == self.target:
                valid, correct, incorrect, noresponse = 1, 1, 0, 0
        elif self.training_type == 2: # active training
            if choice == self.target:
                valid, correct, incorrect, noresponse = 1, 1, 0, 0
            elif choice != self.target:
                valid, correct, incorrect, noresponse = 1, 0, 1, 0

            pass
        # determine valid/invalid and correct/incorrect variables based on performance
        if np.isnan(self.choice):
        #     valid, correct = 0, 0
        #     if self.config.TASK["training_type"]["value"] < 2: # if passive training
        #         correct = 1
        # elif self.stimulus_pars["target"] == self.choice:
        #     valid, correct = 1, 1
        #     if self.correction_trial:
        #         valid = 0
        # elif self.stimulus_pars["target"] != self.choice:
        #     valid, correct = 1, 0
        #     if self.correction_trial:
        #         valid = 0


        # if np.isnan(self.choice):
        #     if not self.correction_trial:
        #         self.subject_config["counters"]["noresponse"] += 1
        #     stimulus_arguments["outcome"] = "invalid"
        #     self.valid = 0
        #     self.correct = 0
        #     # If active training
        #     if self.config.TASK["training_type"]["value"] == 2:
        #         self.reinforcement_duration = self.managers["session"].get_reinforcement_duration(outcome="invalid")

        #     # If passive training
        #     else:
        #         self.correct = 1
        #         if self.stimulus_pars["target"] == -1:  # Left Correct
        #             self.managers["hardware"].reward_left(
        #                 self.subject_config["reward_volume"] * 0.5
        #             )
        #         elif self.stimulus_pars["target"] == 1:  # Right Correct
        #             self.managers["hardware"].reward_right(
        #                 self.subject_config["reward_volume"] * 0.5
        #             )
        #         self.subject_config["total_reward"] += (
        #             self.subject_config["reward_volume"] * 0.5
        #         )

        #         self.reinforcement_duration = self.managers["session"].get_reinforcement_duration(outcome="correct")
        #         self.intertrial_duration = self.managers["session"].get_intertrial_duration(outcome="correct")

        #         # Entering must respond phase
        #         self.trigger = {
        #             "type": "MUST_GO",
        #             "targets": [self.stimulus_pars["target"]],
        #             "duration": self.reinforcement_duration,
        #         }
        #         self.response_block.set()

        # # If incorrect trial
        # elif self.stimulus_pars["target"] != self.choice:
        #     if not self.correction_trial:
        #         self.subject_config["counters"]["incorrect"] += 1
        #         self.valid = 1
        #     else:
        #         self.valid = 0
        #     stimulus_arguments["outcome"] = "incorrect"
        #     self.correct = 0

        #     self.reinforcement_duration = self.managers["session"].get_reinforcement_duration(outcome="incorrect")
        #     self.intertrial_duration = self.managers["session"].get_intertrial_duration(
        #         outcome="incorrect", response_time=self.response_time)

        # # If correct trial
        # elif self.stimulus_pars["target"] == self.choice:
        #     if not self.correction_trial:
        #         self.subject_config["counters"]["correct"] += 1
        #         self.valid = 1
        #     else: 
        #         self.valid = 0
        #     self.correct = 1
        #     stimulus_arguments["outcome"] = "correct"
        #     if self.stimulus_pars["target"] == -1:  # Left Correct
        #         self.managers["hardware"].reward_left(self.subject_config["reward_volume"])
        #     elif self.stimulus_pars["target"] == 1:  # Right Correct
        #         self.managers["hardware"].reward_right(
        #             self.subject_config["reward_volume"]
        #         )
        #     self.subject_config["total_reward"] += self.subject_config["reward_volume"]
            



        return self.reinforcement_duration[outcome]

    def prepare_intertrial_stage(self, outcome, response_time=None):
        return self.intertrial_duration_function[outcome](response_time)

    def end_of_trial_updates(self):
        # function to finalize current trial and set parameters for next trial
        # TODO finalize if correction is required by setting self.is_correction_trial
        pass
        # TODO determine and update valid, correct, incorrect, noresponse counter


        #     """
        # End of trial updates: Updating end of trial parameters such as psychometric function, chronometric function, total trials, rolling_perf
        # bias, rolling_bias
        # """
        # coh_index, coh = (
        #     self.stimulus_pars["index"],
        #     self.stimulus_pars["coherence"],
        # )

        # # updating rolling bias
        # self.subject_config["rolling_bias"][
        #     self.subject_config["rolling_bias_index"]
        # ] = choice
        # self.subject_config["rolling_bias_index"] = (
        #     self.subject_config["rolling_bias_index"] + 1
        # ) % self.subject_config["rolling_bias_window"]

        # # uptading rolling performance
        # ## update history block
        # self.subject_config["rolling_perf"]["hist_" + str(coh)][
        #     self.subject_config["rolling_perf"]["index"][coh_index]
        # ] = outcome
        # ## calculate accuracy
        # self.subject_config["rolling_perf"]["accuracy"][coh_index] = np.mean(
        #     self.subject_config["rolling_perf"]["hist_" + str(coh)]
        # )
        # ## update index
        # self.subject_config["rolling_perf"]["index"][coh_index] = (
        #     self.subject_config["rolling_perf"]["index"][coh_index] + 1
        # ) % self.subject_config["rolling_perf"]["window"]

        # # Updating plot parameters
        # if choice == -1:
        #     # computing left choices coherence-wise
        #     self.subject_config["psych_left"][coh_index] += 1
        # elif choice == 1:
        #     # computing right choices coherence-wise
        #     self.subject_config["psych_right"][coh_index] += 1
        # tot_trials_in_coh = (
        #     self.subject_config["psych_left"][coh_index]
        #     + self.subject_config["psych_right"][coh_index]
        # )

        # # update running accuracy
        # if (
        #     self.subject_config["counters"]["correct"]
        #     + self.subject_config["counters"]["incorrect"]
        #     > 0
        # ):
        #     self.subject_config["running_accuracy"].append(
        #         [
        #             self.subject_config["counters"]["valid"],
        #             self.subject_config["counters"]["correct"]
        #             / (
        #                 self.subject_config["counters"]["correct"]
        #                 + self.subject_config["counters"]["incorrect"]
        #             ),
        #             outcome,
        #         ]
        #     )

        # # update psychometric array
        # self.subject_config["psych"][coh_index] = (
        #     self.subject_config["psych_right"][coh_index] / tot_trials_in_coh
        # )

        # # update total trial array
        # self.subject_config["trial_distribution"][coh_index] += 1

        # # update reaction time array
        # if np.isnan(self.subject_config["response_time_distribution"][coh_index]):
        #     self.subject_config["response_time_distribution"][coh_index] = response_time
        # else:
        #     if True:  # self.coh_to_xrange, self.coh_to_xactive
        #         self.subject_config["response_time_distribution"][coh_index] = (
        #             (
        #                 (tot_trials_in_coh - 1)
        #                 * self.subject_config["response_time_distribution"][coh_index]
        #             )
        #             + response_time
        #         ) / tot_trials_in_coh





    ######################### trial-block methods #########################
    
    def prepare_trial_variables(self):
        if not self.is_correction_trial:    # if not correction trial
            # is this start of new trial block?
            if self.trials_in_block == 0 or self.trials_in_block == len(self.block_schedule):
                self.trials_in_block = 0
                self.graduation_check()
                self.generate_block_schedule()
            self.signed_coherence = self.block_schedule[self.trials_in_block]
            self.target = int(np.sign(self.signed_coherence + np.random.choice([-1e-2, 1e-2])))
            self.trials_in_block += 1 # incrementing within block counter
            self.correction_counter = itertools.count() # resetting correction counter
        else:
            # is passive correction is needed?
            if np.abs(self.signed_coherence) > self.passive_bias_correction_threshold:
                # drawing repeat trial with direction from a normal distribution with mean of against rolling bias
                self.target = int(np.sign(np.random.normal(-np.mean(self.rolling_bias), 0.5)))
                # Repeat probability to opposite side of bias
                self.signed_coherence = self.target * np.abs(self.signed_coherence)
                print(f"Correcting {np.mean(self.rolling_bias)} bias with {self.signed_coherence}")
            # increment correction trial counter
            self.correction_counter = next(self.correction_counter) 

    def graduation_check(self):
        # deciding next_coherence level based on rolling accuracy. 
        # forward level change
        #TODO: swap the logic between "if" and "while" to make it more straightforward
        while self.next_coh_level < len(self.accuracy_thresholds):
            if all(self.rolling_accuracy >= self.accuracy_thresholds[self.current_coh_level]) and (
                self.trials_in_current_level >= self.accuracy_thresholds[self.next_coh_level]
            ):
                self.next_coh_level = self.current_coh_level + 1
                self.subject_config["rolling_perf"]["trial_counter_after_4th"] = 0
            else:
                break
        # backward level change
        if self.graduation_direction == 0:   
            while self.next_coh_level > 1:
                if any(self.rolling_accuracy < self.accuracy_thresholds[self.next_coh_level - 1]):
                    self.next_coh_level = self.current_coh_level - 1
                    self.subject_config["rolling_perf"]["trial_counter_after_4th"] = 0
                else:
                    break

        if self.next_coh_level != self.current_coh_level:
            self.update_coherence_level()

    def update_coherence_level(self):
        # update reward volume based on coherence level change
        if self.next_coh_level > self.current_coh_level: # if level increased
            self.reward_volume += 0.3
        elif self.next_coh_level < self.current_coh_level: # if level decreased
            self.reward_volume -= 0.3
        # setting reward volume withing 1.5 to 3 range
        np.clip(self.reward_volume, 1.5, 3)
        # updating current coherence level
        self.current_coh_level = self.next_coh_level
        self.active_coherences = self.active_coherences_by_level[self.current_coh_level]
        self.active_coherence_indices = [np.where(self.full_coherences == value)[0][0] for value in self.active_coherences]

    def generate_block_schedule(self):
        self.block_schedule = (list(self.active_coherences) * self.repeats_per_block)

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


    ####################### between-trial methods #######################
    def update_EOT(self, choice, response_time, outcome):
        """
        End of trial updates: Updating end of trial parameters such as psychometric function, chronometric function, total trials, rolling_perf
        bias, rolling_bias
        """
        coh_index, coh = (
            self.stimulus_pars["index"],
            self.stimulus_pars["coherence"],
        )

        # updating rolling bias
        self.subject_config["rolling_bias"][
            self.subject_config["rolling_bias_index"]
        ] = choice
        self.subject_config["rolling_bias_index"] = (
            self.subject_config["rolling_bias_index"] + 1
        ) % self.subject_config["rolling_bias_window"]

        # uptading rolling performance
        ## update history block
        self.subject_config["rolling_perf"]["hist_" + str(coh)][
            self.subject_config["rolling_perf"]["index"][coh_index]
        ] = outcome
        ## calculate accuracy
        self.subject_config["rolling_perf"]["accuracy"][coh_index] = np.mean(
            self.subject_config["rolling_perf"]["hist_" + str(coh)]
        )
        ## update index
        self.subject_config["rolling_perf"]["index"][coh_index] = (
            self.subject_config["rolling_perf"]["index"][coh_index] + 1
        ) % self.subject_config["rolling_perf"]["window"]

        # Updating plot parameters
        if choice == -1:
            # computing left choices coherence-wise
            self.subject_config["psych_left"][coh_index] += 1
        elif choice == 1:
            # computing right choices coherence-wise
            self.subject_config["psych_right"][coh_index] += 1
        tot_trials_in_coh = (
            self.subject_config["psych_left"][coh_index]
            + self.subject_config["psych_right"][coh_index]
        )

        # update running accuracy
        if (
            self.subject_config["counters"]["correct"]
            + self.subject_config["counters"]["incorrect"]
            > 0
        ):
            self.subject_config["running_accuracy"].append(
                [
                    self.subject_config["counters"]["valid"],
                    self.subject_config["counters"]["correct"]
                    / (
                        self.subject_config["counters"]["correct"]
                        + self.subject_config["counters"]["incorrect"]
                    ),
                    outcome,
                ]
            )

        # update psychometric array
        self.subject_config["psych"][coh_index] = (
            self.subject_config["psych_right"][coh_index] / tot_trials_in_coh
        )

        # update total trial array
        self.subject_config["trial_distribution"][coh_index] += 1

        # update reaction time array
        if np.isnan(self.subject_config["response_time_distribution"][coh_index]):
            self.subject_config["response_time_distribution"][coh_index] = response_time
        else:
            if True:  # self.coh_to_xrange, self.coh_to_xactive
                self.subject_config["response_time_distribution"][coh_index] = (
                    (
                        (tot_trials_in_coh - 1)
                        * self.subject_config["response_time_distribution"][coh_index]
                    )
                    + response_time
                ) / tot_trials_in_coh

    def update_EOS(self):
        """
        End of session updates: Updating all files and session parameters such as rolling performance
        """
        # Rolling performance
        self.subject_config["rolling_perf"][
            "current_coherence_level"
        ] = self.subject_config["current_coherence_level"]
        self.subject_config["rolling_perf"]["reward_volume"] = self.subject_config["reward_volume"]
        self.subject_config["rolling_perf"][
            "total_attempts"
        ] = self.subject_config["counters"]["attempt"]
        self.subject_config["rolling_perf"]["total_reward"] = self.subject_config["total_reward"]

        with open(self.config.FILES["rolling_perf_after"], "wb") as file:
            pickle.dump(self.subject_config["rolling_perf"], file)
        with open(self.config.FILES["rolling_perf"], "wb") as file:
            pickle.dump(self.subject_config["rolling_perf"], file)

        print("SAVING EOS FILES")


class Task:
    """
    Dynamic Training Routine with reaction time trial structure
    """

    def __init__(
        self,
        stage_block=None,
        protocol=None,
        experiment=None,
        config=None,
        **kwargs,
    ):
        self.protocol = protocol
        self.experiment = experiment
        self.config = config
        self.__dict__.update(kwargs)

        self.subject_config = self.config.SUBJECT

        # Preparing storage files
        self.config.FILES = {}
        data_path = Path(prefs.get("DATADIR"), self.subject_config["name"], self.subject_config["protocol"], self.subject_config["experiment"], self.subject_config["session"])
        
        # since main storage is on server, we will rewrite the directory if already exists assuming that data is already on the server.
        if data_path.exists() and data_path.is_dir():
            # If it exists, delete it and its contents
            for item in data_path.iterdir():
                if item.is_file():
                    item.unlink()  # Delete files
                elif item.is_dir():
                    item.rmdir()   # Delete subdirectories
        data_path.mkdir(parents=True, exist_ok=True) # Recreate the directory




        for file_id, file in self.config.DATAFILES.items():
            self.config.FILES[file_id] = Path(data_path, self.subject_config["name"] + file)
        self.config.FILES["rolling_perf_before"] = Path(data_path, "rolling_perf_before.pkl")
        self.config.FILES["rolling_perf_before"].write_bytes(
            pickle.dumps(self.subject_config["rolling_perf"])
        )
        self.config.FILES["rolling_perf_after"] = Path(data_path, "rolling_perf_after.pkl")
        self.config.FILES["rolling_perf"] = Path(data_path.parent, "rolling_perf.pkl")

        # Event locks, triggers
        self.stage_block = stage_block
        self.response_block = mp.Event()
        self.response_block.clear()
        self.response_queue = mp.Queue()

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
            response_log=self.config.FILES["lick"],
            response_queue=self.response_queue,
            timers=self.timers,
        )

        self.managers["session"] = SessionManager(
            config=self.config,
            subject_config=self.subject_config,
        )

        self.managers["trial"] = RTTask(
            stage_block=self.stage_block,
            response_block=self.response_block,
            response_queue=self.response_queue,
            msg_to_stimulus=self.msg_to_stimulus,
            managers=self.managers,
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
            self.subject_config["total_reward"] += message["value"]
            print(f'REWARDED LEFT with {message["value"]}')
        elif message["key"] == "reward_right":
            self.managers["hardware"].reward_right(message["value"])
            self.subject_config["total_reward"] += message["value"]
            print(f'REWARDED RIGHT with {message["value"]}')
        elif message["key"] == "toggle_left_reward":
            self.managers["hardware"].toggle_reward("Left")
        elif message["key"] == "toggle_right_reward":
            self.managers["hardware"].toggle_reward("Right")
        elif message["key"] == "update_reward":
            self.subject_config["reward_volume"] = message["value"]
            print(f"NEW REWARD VALUE IS {self.subject_config['reward_volume']}")
        elif message["key"] == "calibrate_reward":
            if self.subject_config["name"] in ["XXX", "xxx"]:
                self.managers["hardware"].start_calibration_sequence()

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
        "protocol": "RDK",
        "experiment": "rt_dynamic_training",
        "subject": "PSUIM4",
    }

    Task(stage_block=threading.Event(), **value)
