import csv
import pickle
from collections import deque
from typing import Any, Optional, Union

import numpy as np


class SessionManager:
    """Class for managing session structure i.e., trial sequence, graduation, and session level summary."""

    def __init__(self, config):
        self.config = config

        # Trial counters initialization
        self.trial_counters = {
            "attempt": 0,
            "valid": 0,
            "correct": 0,
            "incorrect": 0,
            "noresponse": 0,
            "correction": 0,
        }

        # Trial parameters
        self.trial_seed: Optional[int] = None
        self.is_correction_trial: bool = False
        self.is_repeat_trial: bool = False
        self.signed_coherence: Optional[float] = None
        self.target: Optional[int] = None
        self.choice: Optional[int] = None
        self.response_time: Optional[float] = None
        self.valid: Optional[bool] = None
        self.outcome: Optional[Union[str, int, float]] = None

        self.reward_volume: Optional[float] = None
        self.trial_reward: Optional[float] = None
        self.total_reward: float = 0.0
        self.must_consume_reward: bool = self.config.TASK["reward"]["must_consume"]
        self.update_reward_volume()

        # Timing parameters
        self.fixation_duration: Optional[float] = None
        self.stimulus_duration: Optional[float] = None
        self.minimum_viewing_duration: float = self.config.TASK["epochs"]["stimulus"]["min_viewing"]
        self.maximum_viewing_duration: float = self.config.TASK["epochs"]["stimulus"]["max_viewing"]
        self.kor_duration: Optional[float] = self.config.TASK["epochs"]["reinforcement"]["knowledge_of_results"]["duration"]
        self.kor_mode: Optional[list] = self.config.TASK["epochs"]["reinforcement"]["knowledge_of_results"]["mode"]
        self.reinforcement_duration: Optional[float] = None
        self.intertrial_duration: Optional[float] = None

        # Stage onset timestamps
        self.fixation_onset: Optional[float] = None
        self.stimulus_onset: Optional[float] = None
        self.response_onset: Optional[float] = None
        self.reinforcement_onset: Optional[float] = None
        self.intertrial_onset: Optional[float] = None

        # Behavioral timing functions
        self.fixation_duration_function = self.config.TASK["epochs"]["fixation"]["duration"]
        self.reinforcement_duration_function = self.config.TASK["epochs"]["reinforcement"]["duration"]
        self.intertrial_duration_function = self.config.TASK["epochs"]["intertrial"]["duration"]

        # Session variables
        self.full_coherences = self.config.TASK["stimulus"]["signed_coherences"]["value"]
        self.active_coherences = self.full_coherences  # Could be different subset
        self.active_coherence_indices = [np.where(self.full_coherences == val)[0][0] for val in self.active_coherences]
        self.coh_to_xrange = {coh: i for i, coh in enumerate(self.full_coherences)}

        # Block schedule and trials counter within block
        self.block_schedule: deque = deque()
        self.block_number: int = 0
        self.repeats_per_block: int = self.config.TASK["stimulus"]["repeats_per_block"]["value"]
        self.schedule_structure: str = self.config.TASK["stimulus"]["schedule_structure"]["value"]

        # Bias correction variables
        self.bias_window = self.config.TASK["bias_correction"]["bias_window"]
        self.rolling_bias = deque(maxlen=self.bias_window)
        self.rolling_bias.extend([0] * self.bias_window)
        self.passive_bias_correction_threshold = self.config.TASK["bias_correction"]["passive"]["coherence_threshold"]
        self.in_active_bias_correction_block: bool = False
        self.active_bias_correction_probability = self.config.TASK["bias_correction"]["active"]["correction_strength"]
        self.active_bias_correction_threshold = self.config.TASK["bias_correction"]["active"]["abs_bias_threshold"]

        # Plot variables for performance tracking
        self.plot_vars = {
            "running_accuracy": [],
            "chose_right": {int(coh): 0 for coh in self.full_coherences},
            "chose_left": {int(coh): 0 for coh in self.full_coherences},
            "psych": {int(coh): np.nan for coh in self.full_coherences},
            "trial_distribution": {int(coh): 0 for coh in self.full_coherences},
            "response_time_distribution": {int(coh): np.nan for coh in self.full_coherences},
        }

    ####################### pre-session methods #######################
    def update_reward_volume(self):
        self.reward_volume = self.config.TASK["reward"].get("volume", 2)

    def reset_trial_variables(self):
        """Reset all trial variables to None or their initial state."""
        self.trial_seed = None
        self.signed_coherence = None
        self.target = None
        self.choice = None
        self.response_time = None
        self.valid = None
        self.outcome = None
        self.trial_reward = None
        self.fixation_duration = None
        self.stimulus_duration = None
        self.reinforcement_duration = None
        self.intertrial_duration = None
        self.fixation_onset = None
        self.stimulus_onset = None
        self.response_onset = None
        self.reinforcement_onset = None
        self.intertrial_onset = None

    ####################### trial epoch methods #######################
    def prepare_fixation_stage(self) -> tuple[dict[str, Any], dict[str, Any]]:
        """Prepare parameters for fixation stage."""
        self.prepare_trial_variables()

        self.fixation_duration = self.fixation_duration_function()
        stage_task_args = {
            "fixation_duration": self.fixation_duration,
            "response_to_check": [-1, 1],
            "signed_coherence": self.signed_coherence,
        }
        stage_stimulus_args = ({},)
        return stage_task_args, stage_stimulus_args

    def prepare_stimulus_stage(self) -> tuple[dict[str, Any], dict[str, Any]]:
        """Prepare parameters for stimulus presentation stage."""
        self.stimulus_duration = self.maximum_viewing_duration
        response_to_check = [-1, 1]
        stage_stimulus_args = {
            "coherence": self.signed_coherence,
            "seed": self.trial_seed,
            "audio_stim": "onset_tone",
        }
        stage_task_args = {
            "coherence": self.signed_coherence,
            "target": self.target,
            "stimulus_duration": self.stimulus_duration,
            "minimum_viewing_duration": self.minimum_viewing_duration,
            "response_to_check": response_to_check,
        }
        return stage_task_args, stage_stimulus_args

    def prepare_reinforcement_stage(self, choice: Optional[int], response_time: Optional[float]) -> tuple[dict[str, Any], dict[str, Any]]:
        """Prepare parameters for reinforcement stage based on choice and response time."""
        self.choice = choice
        self.response_time = response_time
        stage_task_args, stage_stimulus_args = {}, {}

        self.outcome, self.trial_reward = self._determine_outcome_and_reward(self.choice)

        # Get reinforcement duration for this outcome
        if self.outcome not in self.reinforcement_duration_function:
            msg = f"Reinforcement duration function for outcome '{self.outcome}' is not defined."
            raise KeyError(msg)
        self.reinforcement_duration = self.reinforcement_duration_function[self.outcome](self.response_time)

        stage_stimulus_args = {"outcome": self.outcome}
        # Build task args
        stage_task_args = {
            "reinforcement_duration": self.reinforcement_duration,
            "trial_reward": self.trial_reward,
            "reward_side": self.target,
        }

        if self.kor_duration:
            stage_task_args["flash_led"] = {
                "reinforcer_mode": self.kor_mode,
                "reinforcer_direction": self.choice,
                "duration": self.kor_duration,
            }

        if self.trial_reward > 0:
            stage_task_args["wait_for_consumption"] = self.must_consume_reward

        return stage_task_args, stage_stimulus_args

    def prepare_intertrial_stage(self):
        """Prepare parameters for intertrial stage."""
        stage_task_args, stage_stimulus_args = {}, {}
        self.intertrial_duration = self.intertrial_duration_function[self.outcome](self.response_time, self.signed_coherence)

        stage_task_args = {"intertrial_duration": self.intertrial_duration}
        if self.trial_reward > 0:
            stage_task_args["wait_for_consumption"] = self.must_consume_reward

        return stage_task_args, stage_stimulus_args

    ######################### trial-stage methods #########################
    def _start_active_bias_correction_block(self):
        self.block_number += 1
        self.in_active_bias_correction_block = True
        correction_direction = -np.sign(np.nanmean(self.rolling_bias))
        self.rolling_bias.extend([0] * self.bias_window)
        self.generate_active_correction_block_schedule(correction_direction, prob=self.active_bias_correction_probability)
        self.trial_seed, self.signed_coherence = self.block_schedule.popleft()
        self.target = int(np.sign(self.signed_coherence + np.random.choice([-1e-2, 1e-2])))

    def _handle_standard_block(self):
        if self.trial_counters["attempt"] == 0 or len(self.block_schedule) == 0:
            self.block_number += 1
            self.in_active_bias_correction_block = False
            self.generate_block_schedule()

        self.trial_seed, self.signed_coherence = self.block_schedule.popleft()
        self.target = int(np.sign(self.signed_coherence + np.random.choice([-1e-2, 1e-2])))
        self.trial_counters["correction"] = 0

    def prepare_trial_variables(self):
        """Prepare parameters for next trial based on current flags and bias."""
        self.reset_trial_variables()
        if not self.in_active_bias_correction_block and np.abs(np.nanmean(self.rolling_bias)) >= self.active_bias_correction_threshold:
            self._start_active_bias_correction_block()
        else:
            self._handle_standard_block()

    def generate_block_schedule(self):
        schedule = np.repeat(self.active_coherences, self.repeats_per_block)
        if self.schedule_structure == "interleaved":
            schedule = self.shuffle_seq(schedule)
        seed_schedule = [(np.random.randint(0, 1_000_000), coh) for coh in schedule]
        self.block_schedule = deque(seed_schedule)

    def generate_active_correction_block_schedule(self, correction_direction, prob):
        block_length = self.get_active_trial_block_length()

        # Randomly select coherence values (100 or 72) for active bias correction
        correction_coherences = np.random.choice([100, 72], size=block_length)

        # Determine how many trials are correction vs non-correction
        num_correction = int(block_length * prob)
        num_noncorrection = block_length - num_correction
        # Create direction schedule (e.g., +1 or -1)
        directions = np.concatenate(
            [
                np.full(num_correction, correction_direction),
                np.full(num_noncorrection, -correction_direction),
            ]
        )

        # Shuffle both directions and coherence values together
        np.random.shuffle(directions)  # Ensures mixed correction/non-correction
        schedule = correction_coherences * directions

        seed_schedule = [(np.random.randint(0, 1_000_000), coh) for coh in schedule]
        self.block_schedule = deque(seed_schedule)

    def get_active_trial_block_length(self):
        values = np.arange(7, 14)
        lambda_val = 1.0
        probabilities = np.exp(-lambda_val * (values - 4))
        probabilities /= probabilities.sum()
        chosen_value = np.random.choice(values, p=probabilities)
        return chosen_value

    def shuffle_seq(self, sequence: Union[np.ndarray, list[float]], max_repeat: int = 3) -> np.ndarray:
        """Shuffle sequence so that no more than max_repeat consecutive elements have same sign."""
        sequence = np.array(sequence)
        for i in range(len(sequence) - max_repeat + 1):
            subseq = sequence[i : i + max_repeat]
            if len(np.unique(np.sign(subseq))) == 1:  # all same sign
                temp_block = sequence[i:].copy()
                np.random.shuffle(temp_block)
                sequence[i:] = temp_block
        return sequence

    def _determine_outcome_and_reward(self, choice):
        if choice is None or np.isnan(choice):
            return "invalid", 0
        if choice == 0:
            return "noresponse", 0
        if choice == self.target:
            return "correct", self.reward_volume
        return "incorrect", 0

    ####################### between-trial methods #######################
    def _handle_correct_trial(self):
        self.valid = True
        self.trial_counters["valid"] += 1
        self.trial_counters["correct"] += 1

    def _handle_incorrect_trial(self):
        self.valid = True
        self.trial_counters["valid"] += 1
        self.trial_counters["incorrect"] += 1

    def _handle_noresponse_or_invalid(self, next_trial_vars):
        self.valid = False
        if self.is_correction_trial:
            next_trial_vars["is_correction_trial"] = True

        if self.choice == 0:
            self.trial_counters["noresponse"] += 1
            if np.abs(self.signed_coherence) > self.passive_bias_correction_threshold:
                next_trial_vars["is_correction_trial"] = True
                next_trial_vars["is_repeat_trial"] = True
        else:
            next_trial_vars["is_repeat_trial"] = True

    def _update_post_trial_stats(self):
        # Update rolling bias circular buffer
        self.rolling_bias.append(self.choice)
        print(f"Rolling Bias: {self.rolling_bias}")
        signed_coh = self.signed_coherence

        # Update choice counts for psychometric plotting
        chose_left = self.plot_vars["chose_left"]
        chose_right = self.plot_vars["chose_right"]
        if self.choice == -1:
            chose_left[signed_coh] += 1
        elif self.choice == 1:
            chose_right[signed_coh] += 1

        tot_trials = chose_left[signed_coh] + chose_right[signed_coh]

        # Update running accuracy if valid trials exist
        valid_trials = self.trial_counters.get("valid", 0)
        if valid_trials > 0:
            correct_trials = self.trial_counters.get("correct", 0)
            accuracy = round(correct_trials / valid_trials * 100, 2)
            self.plot_vars["running_accuracy"] = [valid_trials, accuracy, self.outcome]

        # Update psychometric function (fraction choosing right)
        psych_val = round(chose_right[signed_coh] / tot_trials, 2) if tot_trials > 0 else 0.0
        self.plot_vars["psych"][signed_coh] = psych_val

        # Update trial distribution count
        self.plot_vars["trial_distribution"][signed_coh] += 1

        # Helper function to update running average
        def running_avg(old_avg, new_val, n):
            return (old_avg * (n - 1) + new_val) / n

        # Update response time running average for the signed coherence
        rt_dist = self.plot_vars["response_time_distribution"]
        current_rt = rt_dist[signed_coh]

        if np.isnan(current_rt):
            rt_dist[signed_coh] = round(self.response_time, 2)
        else:
            new_rt = running_avg(current_rt, self.response_time, tot_trials)
            rt_dist[signed_coh] = round(new_rt, 2)

    def end_of_trial_updates(self):
        """Finalize current trial and prepare flags for next trial."""
        # Map string outcome to numeric
        outcome_map = {
            "correct": 1,
            "incorrect": 0,
            "noresponse": np.nan,
            "invalid": np.nan,
        }
        self.outcome = outcome_map.get(self.outcome, np.nan)

        self.trial_counters["attempt"] += 1
        next_trial_vars = {"is_correction_trial": False, "is_repeat_trial": False}

        if self.in_active_bias_correction_block:
            self.valid = False
            next_trial_vars["is_repeat_trial"] = self.outcome != 1
        elif self.outcome == 1:
            self._handle_correct_trial()
            next_trial_vars["is_correction_trial"] = False

        elif self.outcome == 0:
            self._handle_incorrect_trial()
            # Correction trial if signed coherence above threshold
            next_trial_vars["is_correction_trial"] = np.abs(self.signed_coherence) > self.passive_bias_correction_threshold

        else:  # NaN outcome
            self._handle_noresponse_or_invalid(next_trial_vars)

        # write trial data to file
        self.write_trial_data_to_file()

        # Handle next trial variables based on previous trial outcome
        self.is_correction_trial = False  # next_trial_vars["is_correction_trial"]
        self.is_repeat_trial = next_trial_vars["is_repeat_trial"]
        if next_trial_vars["is_correction_trial"]:
            if self.schedule_structure == "interleaved":
                new_target = int(np.sign(np.random.normal(-np.nanmean(self.rolling_bias) * 2, 0.4)))
                new_signed_coh = new_target * np.abs(self.signed_coherence)
                self.block_schedule.append((np.random.randint(0, 1_000_000), new_signed_coh))
            elif self.schedule_structure == "blocked":
                self.block_schedule.append((np.random.randint(0, 1_000_000), self.signed_coherence))
        if next_trial_vars["is_repeat_trial"]:
            self.block_schedule.appendleft((self.trial_seed, self.signed_coherence))

        # if valid update trial variables and send data to controller
        if self.valid:
            self._update_post_trial_stats()

        trial_data = {
            "is_valid": self.valid,
            "trial_counters": self.trial_counters,
            "block_number": self.block_number,
            "reward_volume": round(self.reward_volume, 2),
            "trial_reward": round(self.trial_reward, 2) if self.trial_reward is not None else None,
            "total_reward": round(self.total_reward, 2),
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
            "block_number": self.block_number,
            "idx_correction": self.trial_counters["correction"],
            "is_correction_trial": self.is_correction_trial,
            "is_repeat_trial": self.is_repeat_trial,
            "in_active_bias_correction_block": self.in_active_bias_correction_block,
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
            "intertrial_duration": self.intertrial_duration,
            "fixation_onset": self.fixation_onset,
            "stimulus_onset": self.stimulus_onset,
            "response_onset": self.response_onset,
            "reinforcement_onset": self.reinforcement_onset,
            "intertrial_onset": self.intertrial_onset,
            "stimulus_seed": self.trial_seed,
        }
        with open(self.config.FILES["trial"], "a", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=data.keys())
            if file.tell() == 0:
                writer.writeheader()
            writer.writerow(data)

    def end_of_session_updates(self):
        self.config.SUBJECT["rolling_perf"]["reward_volume"] = self.reward_volume
        self.config.SUBJECT["rolling_perf"]["total_attempts"] = self.trial_counters["attempt"]
        self.config.SUBJECT["rolling_perf"]["total_reward"] = self.total_reward
        with open(self.config.FILES["rolling_perf_after"], "wb") as file:
            pickle.dump(self.config.SUBJECT["rolling_perf"], file)
        with open(self.config.FILES["rolling_perf"], "wb") as file:
            pickle.dump(self.config.SUBJECT["rolling_perf"], file)
        print("SAVING EOS FILES")


if __name__ == "__main__":
    import config

    full_coherences = config.TASK["stimulus"]["signed_coherences"]["value"]
    reward_volume = config.TASK["rolling_performance"]["reward_volume"]
    rolling_window = config.TASK["rolling_performance"]["rolling_window"]
    rolling_perf = {
        "rolling_window": rolling_window,
        "history": {int(coh): list(np.zeros(rolling_window).astype(int)) for coh in full_coherences},
        "history_indices": {int(coh): 49 for coh in full_coherences},
        "accuracy": {int(coh): 0 for coh in full_coherences},
        # "current_coherence_level": current_coherence_level,
        "trials_in_current_level": 0,
        "total_attempts": 0,
        "total_reward": 0,
        "reward_volume": reward_volume,
    }

    config.SUBJECT = {
        # Subject and task identification
        "name": "test",
        "baseline_weight": 20,
        "start_weight": 19,
        "prct_weight": 95,
        "protocol": "random_dot_motion",
        "experiment": "rt_directional_training",
        "session": "1_1",
        "session_uuid": "XXXX",
        "rolling_perf": rolling_perf,
    }

    sm = SessionManager(config)

    sm.prepare_fixation_stage()
    print(sm.block_schedule)

    sm.prepare_stimulus_stage()
    sm.prepare_reinforcement_stage(1, 3)
    print(f"Outcome: {sm.outcome}")

    sm.prepare_intertrial_stage()

    sm.end_of_trial_updates()
    print(f"Outcome: {sm.outcome}")

    sm.prepare_fixation_stage()
    print(f"Is correction Trial: {sm.is_correction_trial}")
