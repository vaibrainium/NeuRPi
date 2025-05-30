import csv
import pickle
from collections import deque
from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional, Union

import numpy as np


class TrialOutcome(Enum):
    CORRECT = "correct"
    INCORRECT = "incorrect"
    NO_RESPONSE = "noresponse"
    INVALID = "invalid"


@dataclass
class TrialData:
    """Container for trial-specific data."""

    seed: Optional[int] = None
    signed_coherence: Optional[float] = None
    target: Optional[int] = None
    choice: Optional[int] = None
    response_time: Optional[float] = None
    valid: Optional[bool] = None
    outcome: Optional[Union[str, int, float]] = None
    reward: Optional[float] = None

    # Timing data
    fixation_duration: Optional[float] = None
    stimulus_duration: Optional[float] = None
    reinforcement_duration: Optional[float] = None
    intertrial_duration: Optional[float] = None

    # Stage onsets
    fixation_onset: Optional[float] = None
    stimulus_onset: Optional[float] = None
    response_onset: Optional[float] = None
    reinforcement_onset: Optional[float] = None
    intertrial_onset: Optional[float] = None

    def reset(self):
        """Reset all fields to None."""
        for field in self.__dataclass_fields__:
            setattr(self, field, None)


class BiasCorrection:
    """Handles bias correction logic."""

    def __init__(self, config):
        self.bias_window = config.TASK["bias_correction"]["bias_window"]
        self.rolling_bias = deque([0] * self.bias_window, maxlen=self.bias_window)
        self.passive_threshold = config.TASK["bias_correction"]["passive"]["coherence_threshold"]
        self.active_probability = config.TASK["bias_correction"]["active"]["correction_strength"]
        self.active_threshold = config.TASK["bias_correction"]["active"]["abs_bias_threshold"]
        self.in_active_block = False

    def update_bias(self, choice: int):
        """Update rolling bias with new choice."""
        self.rolling_bias.append(choice)

    def get_current_bias(self) -> float:
        """Get current mean bias."""
        return np.nanmean(self.rolling_bias)

    def needs_active_correction(self) -> bool:
        """Check if active bias correction is needed."""
        return (not self.in_active_block and
                abs(self.get_current_bias()) >= self.active_threshold)

    def start_active_correction(self) -> int:
        """Start active correction and return correction direction."""
        self.in_active_block = True
        correction_direction = -np.sign(self.get_current_bias())
        self.rolling_bias.extend([0] * self.bias_window)
        return correction_direction

    def needs_passive_correction(self, signed_coherence: float) -> bool:
        """Check if passive correction is needed for given coherence."""
        return abs(signed_coherence) > self.passive_threshold


class BlockScheduler:
    """Handles trial scheduling and block generation."""

    def __init__(self, config):
        self.active_coherences = config.TASK["stimulus"]["signed_coherences"]["value"]
        self.repeats_per_block = config.TASK["stimulus"]["repeats_per_block"]["value"]
        self.schedule_structure = config.TASK["stimulus"]["schedule_structure"]["value"]
        self.schedule = deque()
        self.block_number = 0

    def generate_standard_block(self):
        """Generate a standard block schedule."""
        self.block_number += 1
        schedule = np.repeat(self.active_coherences, self.repeats_per_block)

        if self.schedule_structure == "interleaved":
            schedule = self._shuffle_with_constraint(schedule)

        seed_schedule = [(np.random.randint(0, 1_000_000), coh) for coh in schedule]
        self.schedule = deque(seed_schedule)

    def generate_active_correction_block(self, correction_direction: int, probability: float):
        """Generate active bias correction block."""
        self.block_number += 1
        block_length = self._get_active_block_length()

        # Generate coherence values and directions
        coherences = np.random.choice([100, 72], size=block_length)
        num_correction = int(block_length * probability)
        num_non_correction = block_length - num_correction

        directions = np.concatenate([
            np.full(num_correction, correction_direction),
            np.full(num_non_correction, -correction_direction),
        ])
        np.random.shuffle(directions)

        schedule = coherences * directions
        seed_schedule = [(np.random.randint(0, 1_000_000), coh) for coh in schedule]
        self.schedule = deque(seed_schedule)

    def _get_active_block_length(self) -> int:
        """Get length for active correction block using exponential distribution."""
        values = np.arange(7, 14)
        lambda_val = 1.0
        probabilities = np.exp(-lambda_val * (values - 4))
        probabilities /= probabilities.sum()
        return np.random.choice(values, p=probabilities)

    def _shuffle_with_constraint(self, sequence: np.ndarray, max_repeat: int = 3) -> np.ndarray:
        """Shuffle sequence preventing more than max_repeat consecutive same signs."""
        sequence = np.array(sequence)
        for i in range(len(sequence) - max_repeat + 1):
            subseq = sequence[i:i + max_repeat]
            if len(np.unique(np.sign(subseq))) == 1:
                temp_block = sequence[i:].copy()
                np.random.shuffle(temp_block)
                sequence[i:] = temp_block
        return sequence

    def get_next_trial(self) -> tuple[int, float]:
        """Get next trial parameters."""
        return self.schedule.popleft()

    def add_correction_trial(self, seed: int, coherence: float, bias: float):
        """Add correction trial to schedule."""
        if self.schedule_structure == "interleaved":
            new_target = int(np.sign(np.random.normal(-bias * 2, 0.4)))
            new_coherence = new_target * abs(coherence)
            self.schedule.append((np.random.randint(0, 1_000_000), new_coherence))
        else:
            self.schedule.append((np.random.randint(0, 1_000_000), coherence))

    def add_repeat_trial(self, seed: int, coherence: float):
        """Add repeat trial to front of schedule."""
        self.schedule.appendleft((seed, coherence))

    def is_empty(self) -> bool:
        """Check if schedule is empty."""
        return len(self.schedule) == 0


class PerformanceTracker:
    """Tracks performance metrics and plotting variables."""

    def __init__(self, coherences: np.ndarray):
        self.coherences = coherences
        self.reset_stats()

    def reset_stats(self):
        """Reset all tracking statistics."""
        self.running_accuracy = []
        self.chose_right = {float(coh): 0 for coh in self.coherences}
        self.chose_left = {float(coh): 0 for coh in self.coherences}
        self.psych = {float(coh): np.nan for coh in self.coherences}
        self.trial_distribution = {float(coh): 0 for coh in self.coherences}
        self.response_time_distribution = {float(coh): np.nan for coh in self.coherences}

    def update_choice_counts(self, choice: int, coherence: float):
        """Update choice counts for psychometric analysis."""
        if choice == -1:
            self.chose_left[coherence] += 1
        elif choice == 1:
            self.chose_right[coherence] += 1

    def update_psychometric(self, coherence: float):
        """Update psychometric function data."""
        total_trials = self.chose_left[coherence] + self.chose_right[coherence]
        if total_trials > 0:
            self.psych[coherence] = round(self.chose_right[coherence] / total_trials, 2)

    def update_response_time(self, coherence: float, response_time: float):
        """Update running average of response times."""
        total_trials = self.chose_left[coherence] + self.chose_right[coherence]
        current_rt = self.response_time_distribution[coherence]

        if np.isnan(current_rt):
            self.response_time_distribution[coherence] = round(response_time, 2)
        else:
            new_rt = (current_rt * (total_trials - 1) + response_time) / total_trials
            self.response_time_distribution[coherence] = round(new_rt, 2)

    def update_accuracy(self, valid_count: int, correct_count: int, outcome: Union[str, float]):
        """Update running accuracy statistics."""
        if valid_count > 0:
            accuracy = round(correct_count / valid_count * 100, 2)
            self.running_accuracy = [valid_count, accuracy, outcome]

    def increment_trial_count(self, coherence: float):
        """Increment trial count for given coherence."""
        self.trial_distribution[coherence] += 1


class SessionManager:
    """Manages session structure, trial sequence, and performance tracking."""

    def __init__(self, config):
        self.config = config

        # Initialize components
        self.trial_data = TrialData()
        self.bias_correction = BiasCorrection(config)
        self.scheduler = BlockScheduler(config)
        self.performance = PerformanceTracker(config.TASK["stimulus"]["signed_coherences"]["value"])

        # Trial counters
        self.trial_counters = {
            "attempt": 0, "valid": 0, "correct": 0,
            "incorrect": 0, "noresponse": 0, "correction": 0,
        }

        # Reward tracking
        self.reward_volume = config.TASK["reward"].get("volume", 2)
        self.total_reward = 0.0

        # Timing configuration
        self._setup_timing_functions(config)

        # Trial flags
        self.is_correction_trial = False
        self.is_repeat_trial = False

    def _setup_timing_functions(self, config):
        """Setup timing-related functions and parameters."""
        self.minimum_viewing_duration = config.TASK["epochs"]["stimulus"]["min_viewing"]
        self.maximum_viewing_duration = config.TASK["epochs"]["stimulus"]["max_viewing"]
        self.knowledge_of_results_duration = config.TASK["epochs"]["reinforcement"]["knowledge_of_results"]["duration"]

        self.fixation_duration_function = config.TASK["epochs"]["fixation"]["duration"]
        self.reinforcement_duration_function = config.TASK["epochs"]["reinforcement"]["duration"]
        self.intertrial_duration_function = config.TASK["epochs"]["intertrial"]["duration"]
        self.must_consume_reward = config.TASK["reward"]["must_consume"]

    # Stage preparation methods
    def prepare_fixation_stage(self) -> tuple[dict[str, Any], dict[str, Any]]:
        """Prepare fixation stage parameters."""
        self._prepare_next_trial()

        self.trial_data.fixation_duration = self.fixation_duration_function()

        task_args = {
            "fixation_duration": self.trial_data.fixation_duration,
            "response_to_check": [-1, 1],
            "signed_coherence": self.trial_data.signed_coherence,
        }
        stimulus_args = {}

        return task_args, stimulus_args

    def prepare_stimulus_stage(self) -> tuple[dict[str, Any], dict[str, Any]]:
        """Prepare stimulus stage parameters."""
        self.trial_data.stimulus_duration = self.maximum_viewing_duration

        stimulus_args = {
            "coherence": self.trial_data.signed_coherence,
            "seed": self.trial_data.seed,
            "audio_stim": "onset_tone",
        }

        task_args = {
            "coherence": self.trial_data.signed_coherence,
            "target": self.trial_data.target,
            "stimulus_duration": self.trial_data.stimulus_duration,
            "minimum_viewing_duration": self.minimum_viewing_duration,
            "response_to_check": [-1, 1],
        }

        return task_args, stimulus_args

    def prepare_reinforcement_stage(self, choice: Optional[int],
                                  response_time: Optional[float]) -> tuple[dict[str, Any], dict[str, Any]]:
        """Prepare reinforcement stage parameters."""
        self.trial_data.choice = choice
        self.trial_data.response_time = response_time

        outcome, reward = self._determine_outcome_and_reward(choice)
        self.trial_data.outcome = outcome
        self.trial_data.reward = reward

        # Get reinforcement duration
        if outcome not in self.reinforcement_duration_function:
            msg = f"Reinforcement duration function for outcome '{outcome}' is not defined."
            raise KeyError(msg)

        self.trial_data.reinforcement_duration = self.reinforcement_duration_function[outcome](response_time)

        stimulus_args = {"outcome": outcome}
        task_args = {
            "reinforcement_duration": self.trial_data.reinforcement_duration,
            "trial_reward": reward,
            "reward_side": self.trial_data.target,
        }

        if self.knowledge_of_results_duration:
            task_args["flash_led"] = {
                "direction": self.trial_data.target,
                "duration": self.knowledge_of_results_duration,
            }

        if reward > 0:
            task_args["wait_for_consumption"] = self.must_consume_reward

        return task_args, stimulus_args

    def prepare_intertrial_stage(self) -> tuple[dict[str, Any], dict[str, Any]]:
        """Prepare intertrial stage parameters."""
        self.trial_data.intertrial_duration = self.intertrial_duration_function[
            self.trial_data.outcome
        ](self.trial_data.response_time, self.trial_data.signed_coherence)

        task_args = {"intertrial_duration": self.trial_data.intertrial_duration}

        if self.trial_data.reward > 0:
            task_args["wait_for_consumption"] = self.must_consume_reward

        return task_args, {}

    def _prepare_next_trial(self):
        """Prepare parameters for the next trial."""
        self.trial_data.reset()

        if self.bias_correction.needs_active_correction():
            self._start_active_bias_correction()
        else:
            self._handle_standard_trial()

    def _start_active_bias_correction(self):
        """Start active bias correction block."""
        correction_direction = self.bias_correction.start_active_correction()
        self.scheduler.generate_active_correction_block(
            correction_direction, self.bias_correction.active_probability,
        )
        self._get_next_trial_params()

    def _handle_standard_trial(self):
        """Handle standard trial generation."""
        if self.trial_counters["attempt"] == 0 or self.scheduler.is_empty():
            self.bias_correction.in_active_block = False
            self.scheduler.generate_standard_block()

        self._get_next_trial_params()
        self.trial_counters["correction"] = 0

    def _get_next_trial_params(self):
        """Get parameters for next trial from scheduler."""
        self.trial_data.seed, self.trial_data.signed_coherence = self.scheduler.get_next_trial()
        # Add small random offset to prevent exactly zero coherence
        self.trial_data.target = int(np.sign(
            self.trial_data.signed_coherence + np.random.choice([-1e-2, 1e-2]),
        ))

    def _determine_outcome_and_reward(self, choice: Optional[int]) -> tuple[str, float]:
        """Determine trial outcome and reward based on choice."""
        if choice is None or np.isnan(choice):
            return TrialOutcome.INVALID.value, 0
        if choice == 0:
            return TrialOutcome.NO_RESPONSE.value, 0
        if choice == self.trial_data.target:
            return TrialOutcome.CORRECT.value, self.reward_volume
        return TrialOutcome.INCORRECT.value, 0

    def end_of_trial_updates(self) -> dict[str, Any]:
        """Process end of trial updates and return trial data."""
        # Convert outcome to numeric
        outcome_map = {
            TrialOutcome.CORRECT.value: 1,
            TrialOutcome.INCORRECT.value: 0,
            TrialOutcome.NO_RESPONSE.value: np.nan,
            TrialOutcome.INVALID.value: np.nan,
        }
        self.trial_data.outcome = outcome_map.get(self.trial_data.outcome, np.nan)

        self.trial_counters["attempt"] += 1

        # Determine next trial flags
        next_trial_flags = self._process_trial_outcome()

        # Write trial data
        self.write_trial_data_to_file()

        # Update flags for next trial
        self._update_trial_flags(next_trial_flags)

        # Update statistics if trial was valid
        if self.trial_data.valid:
            self._update_performance_stats()

        return self._build_trial_summary()

    def _process_trial_outcome(self) -> dict[str, bool]:
        """Process trial outcome and update counters."""
        next_trial_flags = {"is_correction_trial": False, "is_repeat_trial": False}

        if self.bias_correction.in_active_block:
            self.trial_data.valid = False
            next_trial_flags["is_repeat_trial"] = (self.trial_data.outcome != 1)

        elif self.trial_data.outcome == 1:  # Correct
            self.trial_data.valid = True
            self.trial_counters["valid"] += 1
            self.trial_counters["correct"] += 1

        elif self.trial_data.outcome == 0:  # Incorrect
            self.trial_data.valid = True
            self.trial_counters["valid"] += 1
            self.trial_counters["incorrect"] += 1
            next_trial_flags["is_correction_trial"] = self.bias_correction.needs_passive_correction(
                self.trial_data.signed_coherence,
            )

        else:  # No response or invalid
            self.trial_data.valid = False
            if self.is_correction_trial:
                next_trial_flags["is_correction_trial"] = True

            if self.trial_data.choice == 0:
                self.trial_counters["noresponse"] += 1
                if self.bias_correction.needs_passive_correction(self.trial_data.signed_coherence):
                    next_trial_flags["is_correction_trial"] = True
                    next_trial_flags["is_repeat_trial"] = True
            else:
                next_trial_flags["is_repeat_trial"] = True

        return next_trial_flags

    def _update_trial_flags(self, flags: dict[str, bool]):
        """Update trial flags and schedule corrections/repeats."""
        self.is_correction_trial = False  # flags["is_correction_trial"] - disabled per original
        self.is_repeat_trial = flags["is_repeat_trial"]

        if flags["is_correction_trial"]:
            self.scheduler.add_correction_trial(
                self.trial_data.seed,
                self.trial_data.signed_coherence,
                self.bias_correction.get_current_bias(),
            )

        if flags["is_repeat_trial"]:
            self.scheduler.add_repeat_trial(
                self.trial_data.seed,
                self.trial_data.signed_coherence,
            )

    def _update_performance_stats(self):
        """Update performance tracking statistics."""
        # Update bias tracking
        self.bias_correction.update_bias(self.trial_data.choice)
        print(f"Rolling Bias: {self.bias_correction.rolling_bias}")

        coherence = self.trial_data.signed_coherence

        # Update performance metrics
        self.performance.update_choice_counts(self.trial_data.choice, coherence)
        self.performance.update_psychometric(coherence)
        self.performance.update_response_time(coherence, self.trial_data.response_time)
        self.performance.update_accuracy(
            self.trial_counters["valid"],
            self.trial_counters["correct"],
            self.trial_data.outcome,
        )
        self.performance.increment_trial_count(coherence)

    def _build_trial_summary(self) -> dict[str, Any]:
        """Build trial summary data for return."""
        return {
            "is_valid": self.trial_data.valid,
            "trial_counters": self.trial_counters,
            "block_number": self.scheduler.block_number,
            "reward_volume": round(self.reward_volume, 2),
            "trial_reward": round(self.trial_data.reward, 2) if self.trial_data.reward is not None else None,
            "total_reward": round(self.total_reward, 2),
            "plots": {
                "running_accuracy": self.performance.running_accuracy,
                "psychometric_function": self.performance.psych,
                "trial_distribution": self.performance.trial_distribution,
                "response_time_distribution": self.performance.response_time_distribution,
            },
        }

    def write_trial_data_to_file(self):
        """Write trial data to CSV file."""
        data = {
            "idx_attempt": self.trial_counters["attempt"],
            "idx_valid": self.trial_counters["valid"],
            "block_number": self.scheduler.block_number,
            "idx_correction": self.trial_counters["correction"],
            "is_correction_trial": self.is_correction_trial,
            "is_repeat_trial": self.is_repeat_trial,
            "in_active_bias_correction_block": self.bias_correction.in_active_block,
            "signed_coherence": self.trial_data.signed_coherence,
            "target": self.trial_data.target,
            "choice": self.trial_data.choice,
            "response_time": self.trial_data.response_time,
            "is_valid": self.trial_data.valid,
            "outcome": self.trial_data.outcome,
            "trial_reward": self.trial_data.reward,
            "fixation_duration": self.trial_data.fixation_duration,
            "stimulus_duration": self.trial_data.stimulus_duration,
            "reinforcement_duration": self.trial_data.reinforcement_duration,
            "intertrial_duration": self.trial_data.intertrial_duration,
            "fixation_onset": self.trial_data.fixation_onset,
            "stimulus_onset": self.trial_data.stimulus_onset,
            "response_onset": self.trial_data.response_onset,
            "reinforcement_onset": self.trial_data.reinforcement_onset,
            "intertrial_onset": self.trial_data.intertrial_onset,
            "stimulus_seed": self.trial_data.seed,
        }

        with open(self.config.FILES["trial"], "a", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=data.keys())
            if file.tell() == 0:
                writer.writeheader()
            writer.writerow(data)

    def end_of_session_updates(self):
        """Save session data and update rolling performance metrics."""
        self.config.SUBJECT["rolling_perf"]["reward_volume"] = self.reward_volume
        self.config.SUBJECT["rolling_perf"]["total_attempts"] = self.trial_counters["attempt"]
        self.config.SUBJECT["rolling_perf"]["total_reward"] = self.total_reward

        with open(self.config.FILES["rolling_perf_after"], "wb") as file:
            pickle.dump(self.config.SUBJECT["rolling_perf"], file)
        with open(self.config.FILES["rolling_perf"], "wb") as file:
            pickle.dump(self.config.SUBJECT["rolling_perf"], file)
        print("SAVING EOS FILES")

    def update_reward_volume(self):
        """Update reward volume from config."""
        self.reward_volume = self.config.TASK["reward"].get("volume", 2)
