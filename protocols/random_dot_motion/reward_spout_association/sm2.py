import csv
import logging
import pickle
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

import numpy as np


@dataclass
class TrialCounters:
    """Data class to hold trial counters with validation."""

    attempt: int = 0
    valid: int = 0
    correct: int = 0
    incorrect: int = 0
    noresponse: int = 0
    correction: int = 0

    def increment(self, counter_name: str) -> None:
        """Safely increment a counter."""
        if hasattr(self, counter_name):
            setattr(self, counter_name, getattr(self, counter_name) + 1)
        else:
            msg = f"Unknown counter: {counter_name}"
            raise ValueError(msg)

    def to_dict(self) -> dict[str, int]:
        """Convert to dictionary for serialization."""
        return {
            "attempt": self.attempt,
            "valid": self.valid,
            "correct": self.correct,
            "incorrect": self.incorrect,
            "noresponse": self.noresponse,
            "correction": self.correction,
        }


@dataclass
class BiasTracker:
    """Manages bias calculation and correction logic."""

    window_size: int
    threshold: float
    _rolling_responses: deque = field(init=False)

    def __post_init__(self):
        self._rolling_responses = deque(maxlen=self.window_size)
        # Initialize with zeros
        self._rolling_responses.extend([0] * self.window_size)

    @property
    def current_bias(self) -> float:
        """Calculate current bias from rolling window."""
        return float(np.nanmean(self._rolling_responses))

    def add_response(self, choice: int) -> None:
        """Add a new response to the rolling window."""
        self._rolling_responses.append(choice)

    def get_allowed_responses(self) -> list[int]:
        """Get list of allowed responses based on current bias."""
        bias = self.current_bias
        if abs(bias) > self.threshold:
            return [-int(np.sign(bias))]
        return [-1, 1]


class SessionManager:
    """
    Manages session structure including trial sequence, graduation, and session-level summary.

    Improvements made:
    - Better error handling and validation
    - Separated concerns with helper classes
    - More robust file operations
    - Type hints for better code clarity
    - Logging instead of print statements
    - Property-based access for computed values
    """

    def __init__(self, config):
        self.config = config
        self.logger = self._setup_logger()

        # Initialize trial management components
        self.trial_counters = TrialCounters()
        self._initialize_trial_parameters()
        self._initialize_bias_tracker()

        # Session state
        self.choice: Optional[int] = None
        self.total_reward: float = 0.0

    def _setup_logger(self) -> logging.Logger:
        """Set up logging for the session manager."""
        logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)
        return logger

    def _initialize_trial_parameters(self) -> None:
        """Initialize trial-level parameters from config."""
        try:
            task_config = self.config.TASK
            self.trial_reward = task_config["reward"].get("volume", 4)
            self.knowledge_of_results_duration = task_config["knowledge_of_results"]["duration"]
            self.intertrial_duration = task_config["intertrial"]["duration"]
        except KeyError as e:
            msg = f"Missing required config parameter: {e}"
            raise ValueError(msg)

    def _initialize_bias_tracker(self) -> None:
        """Initialize bias tracking system."""
        try:
            bias_config = self.config.TASK["bias_correction"]
            self.bias_tracker = BiasTracker(
                window_size=bias_config["window"],
                threshold=bias_config["threshold"],
            )
        except KeyError as e:
            msg = f"Missing bias correction config: {e}"
            raise ValueError(msg)

    @property
    def current_bias(self) -> float:
        """Get current bias value."""
        return self.bias_tracker.current_bias

    @property
    def responses_to_check(self) -> list[int]:
        """Get allowed responses based on current bias."""
        return self.bias_tracker.get_allowed_responses()

    # ==================== Trial Epoch Methods ====================

    def prepare_trial_vars(self) -> None:
        """Prepare variables for the upcoming trial."""
        # This method now uses the property-based approach
        # No explicit preparation needed as responses_to_check is computed on-demand
        self.logger.debug(f"Trial prepared. Allowed responses: {self.responses_to_check}")

    def prepare_reinforcement_stage(self, choice: int) -> dict[str, Any]:
        """
        Prepare reinforcement stage parameters.

        Args:
            choice: The choice made by the subject (-1 or 1)

        Returns:
            Dictionary containing task arguments for reinforcement stage

        """
        if choice not in [-1, 1]:
            msg = f"Invalid choice value: {choice}. Must be -1 or 1."
            raise ValueError(msg)

        self.choice = choice
        self.bias_tracker.add_response(choice)

        task_args = {
            "trial_reward": self.trial_reward,
            "knowledge_of_results_duration": self.knowledge_of_results_duration,
            "intertrial_duration": self.intertrial_duration,
        }

        self.logger.debug(f"Reinforcement stage prepared. Choice: {choice}, Bias: {self.current_bias:.3f}")
        return task_args

    # ==================== Between-Trial Methods ====================

    def end_of_trial_updates(self) -> dict[str, Any]:
        """
        Finalize current trial and prepare for next trial.

        Returns:
            Dictionary containing trial summary data

        """
        self.trial_counters.increment("attempt")

        # Update total reward (assuming positive reward for valid trials)
        if self.choice is not None:
            self.total_reward += self.trial_reward

        # Write trial data to file
        try:
            self._write_trial_data_to_file()
        except Exception as e:
            self.logger.exception(f"Failed to write trial data: {e}")
            raise

        trial_data = {
            "trial_counters": self.trial_counters.to_dict(),
            "choice": self.choice,
            "reward_volume": self.trial_reward,
            "total_reward": self.total_reward,
            "current_bias": self.current_bias,
        }

        self.logger.info(f"Trial {self.trial_counters.attempt} completed. "
                        f"Choice: {self.choice}, Total reward: {self.total_reward:.2f}")

        return trial_data

    def _write_trial_data_to_file(self) -> None:
        """Write trial data to CSV file with error handling."""
        if self.choice is None:
            self.logger.warning("No choice recorded for this trial")
            return

        trial_data = {
            "idx_attempt": self.trial_counters.attempt,
            "choice": self.choice,
            "trial_reward": self.trial_reward,
            "intertrial_duration": self.intertrial_duration,
            "knowledge_of_results_duration": self.knowledge_of_results_duration,
            "current_bias": self.current_bias,
            "total_reward": self.total_reward,
        }

        file_path = Path(self.config.FILES["trial"])

        # Ensure directory exists
        file_path.parent.mkdir(parents=True, exist_ok=True)

        # Check if file exists to determine if header is needed
        write_header = not file_path.exists() or file_path.stat().st_size == 0

        try:
            with open(file_path, "a", newline="", encoding="utf-8") as file:
                writer = csv.DictWriter(file, fieldnames=trial_data.keys())
                if write_header:
                    writer.writeheader()
                writer.writerow(trial_data)
        except Exception as e:
            self.logger.exception(f"Error writing to trial file {file_path}: {e}")
            raise

    def end_of_session_updates(self) -> None:
        """Perform end-of-session updates and save session data."""
        try:
            # Update rolling performance data
            rolling_perf = self.config.SUBJECT["rolling_perf"]
            rolling_perf.update({
                "reward_volume": self.trial_reward,
                "total_attempts": self.trial_counters.attempt,
                "total_reward": self.total_reward,
                "final_bias": self.current_bias,
            })

            # Save performance data to files
            self._save_performance_data(rolling_perf)

            self.logger.info("End of session updates completed successfully")
            self.logger.info(f"Session summary - Total attempts: {self.trial_counters.attempt}, "
                           f"Total reward: {self.total_reward:.2f}, Final bias: {self.current_bias:.3f}")

        except Exception as e:
            self.logger.exception(f"Error during end of session updates: {e}")
            raise

    def _save_performance_data(self, rolling_perf: dict[str, Any]) -> None:
        """Save performance data to pickle files."""
        files_to_save = [
            self.config.FILES["rolling_perf_after"],
            self.config.FILES["rolling_perf"],
        ]

        for file_path in files_to_save:
            try:
                # Ensure directory exists
                Path(file_path).parent.mkdir(parents=True, exist_ok=True)

                with open(file_path, "wb") as file:
                    pickle.dump(rolling_perf, file)

                self.logger.debug(f"Performance data saved to {file_path}")

            except Exception as e:
                self.logger.exception(f"Failed to save performance data to {file_path}: {e}")
                raise

    # ==================== Utility Methods ====================

    def get_session_summary(self) -> dict[str, Any]:
        """Get a comprehensive summary of the current session."""
        return {
            "trial_counters": self.trial_counters.to_dict(),
            "total_reward": self.total_reward,
            "current_bias": self.current_bias,
            "trial_reward": self.trial_reward,
            "allowed_responses": self.responses_to_check,
        }

    def reset_session(self) -> None:
        """Reset session state for a new session."""
        self.trial_counters = TrialCounters()
        self._initialize_bias_tracker()
        self.choice = None
        self.total_reward = 0.0
        self.logger.info("Session reset completed")
