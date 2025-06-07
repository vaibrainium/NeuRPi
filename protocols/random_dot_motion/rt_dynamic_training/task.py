"""
Enhanced Dynamic Training Task with improved parallel processing.

This module provides an improved version of the dynamic training task using
the enhanced ParallelManager for better process management, error handling,
and monitoring capabilities.
"""

import datetime
import itertools
import pickle
import sys
import threading
from pathlib import Path
from typing import Any, Protocol

import numpy as np

from neurpi.prefs import prefs
from neurpi.utils.parallel_manager import ParallelManager, ProcessConfig
from protocols.random_dot_motion.core.hardware.behavior import Behavior
from protocols.random_dot_motion.core.hardware.hardware_manager import HardwareManager
from protocols.random_dot_motion.core.task.rt_task import RTTask

from .session_manager import SessionManager
from .stimulus_manager import StimulusManager

# Constants
DEFAULT_MONITOR_INTERVAL = 1.0
MAX_TEST_ITERATIONS = 100
STIMULUS_PROCESS_PRIORITY = 1
BEHAVIOR_PROCESS_PRIORITY = 2

# Process configuration
PROCESS_START_TIMEOUT = 10.0
DISPLAY_CONNECTION_TIMEOUT = 5.0
PROCESS_STOP_TIMEOUT = 10.0
MAX_RESTART_ATTEMPTS = 3
RESTART_DELAY = 2.0

# Error messages
BEHAVIOR_START_ERROR = "Failed to start behavior process"
STIMULUS_START_ERROR = "Failed to start stimulus process"
STIMULUS_TIMEOUT_ERROR = "Stimulus process did not start in time"
DISPLAY_TIMEOUT_ERROR = "Display did not connect in time"
CONFIG_VALIDATION_ERROR = "Configuration validation failed"
FILE_OPERATION_ERROR = "File operation failed"
PROCESS_COMMUNICATION_ERROR = "Process communication failed"


class ConfigValidationError(Exception):
    """Custom exception for configuration validation errors."""

    def __init__(self, missing_attribute: str):
        msg = f"Config missing required attribute: {missing_attribute}"
        super().__init__(msg)


class ProcessStartError(Exception):
    """Custom exception for process startup failures."""

    def __init__(self, process_name: str, details: str = ""):
        msg = f"Failed to start {process_name} process"
        if details:
            msg += f": {details}"
        super().__init__(msg)


class ProcessTimeoutError(Exception):
    """Custom exception for process timeout errors."""

    def __init__(self, process_name: str, operation: str = "startup"):
        msg = f"{process_name.capitalize()} process {operation} timeout"
        super().__init__(msg)


class FileOperationError(Exception):
    """Custom exception for file operation failures."""

    def __init__(self, operation: str, file_path: str = "", details: str = ""):
        msg = f"File {operation} failed"
        if file_path:
            msg += f" for {file_path}"
        if details:
            msg += f": {details}"
        super().__init__(msg)


class ConfigProtocol(Protocol):
    """Protocol defining the expected structure of config objects."""

    SUBJECT: dict[str, Any]
    STIMULUS: dict[str, Any]
    DATAFILES: dict[str, str]
    FILES: dict[str, Path]


class Task:
    """Dynamic Training Routine with reaction time trial structure using enhanced ParallelManager."""

    def __init__(
        self,
        stage_block=None,
        protocol="random_dot_motion",
        experiment="rt_dynamic_training",
        task_config=None,
        **kwargs,
    ):
        self.protocol = protocol
        self.experiment = experiment        # Validate and assign config
        if task_config is None:
            missing_attr = "config"
            raise ConfigValidationError(missing_attr)
        self._validate_config(task_config)
        self.config: ConfigProtocol = task_config

        self.__dict__.update(kwargs)

        # Initialize enhanced parallel manager
        self.parallel_manager = ParallelManager(monitor_interval=DEFAULT_MONITOR_INTERVAL)

        # Event locks, triggers and queues (now managed by ParallelManager)
        self.stage_block = stage_block
        self.response_block = self.parallel_manager.communication.create_event("response_block")
        self.response_block.clear()
        self.response_queue = self.parallel_manager.communication.create_queue("response_queue")

        # Communication queues for stimulus process
        self.msg_to_stimulus = self.parallel_manager.communication.create_queue("msg_to_stimulus")
        self.msg_from_stimulus = self.parallel_manager.communication.create_queue("msg_from_stimulus")

        self.timers = {
            "session": datetime.datetime.now(tz=datetime.timezone.utc),
            "trial": datetime.datetime.now(tz=datetime.timezone.utc),
        }

        # Preparing session files
        self.prepare_session_files()

        # Preparing Managers
        self.managers = {}
        self.managers["hardware"] = HardwareManager()
        self.managers["hardware"].start_session(session_id=self.config.SUBJECT["session_uuid"])
        self.managers["session"] = SessionManager(config=self.config)
        self.managers["trial"] = RTTask(
            stage_block=self.stage_block,
            response_block=self.response_block,
            response_queue=self.response_queue,
            msg_to_stimulus=self.msg_to_stimulus,
            managers=self.managers,
            config=self.config,
            timers=self.timers,
        )
        self.stages = self.managers["trial"].stages        # Register processes with enhanced ParallelManager
        self._register_processes()

    def _validate_config(self, config: Any) -> None:
        """Validate that config has all required attributes."""
        required_attrs = ["SUBJECT", "STIMULUS", "DATAFILES"]
        for attr in required_attrs:
            if not hasattr(config, attr):
                raise ConfigValidationError(attr)

    def _register_processes(self):
        """Register stimulus and behavior processes with ParallelManager."""
        # Register stimulus process
        stimulus_config = ProcessConfig(
            name="stimulus_manager",
            target_func=self._stimulus_process_wrapper,
            args=(self.config.STIMULUS,),
            kwargs={},
            daemon=True,
            auto_restart=True,
            max_restarts=3,
            restart_delay=2.0,
            timeout=30.0,
            priority=1,
            in_queue=self.msg_to_stimulus,
            out_queue=self.msg_from_stimulus,
        )
        self.parallel_manager.register_process("stimulus", stimulus_config)

        # Register behavior process
        behavior_config = ProcessConfig(
            name="behavior_manager",
            target_func=self._behavior_process_wrapper,
            args=(),
            kwargs={
                "hardware_manager": self.managers["hardware"],
                "response_log": self.config.FILES["lick"],
                "timers": self.timers,
            },
            daemon=True,
            auto_restart=True,            max_restarts=3,
            restart_delay=1.0,
            timeout=30.0,
            priority=2,  # Higher priority for behavior process
        )
        self.parallel_manager.register_process("behavior", behavior_config)

    @staticmethod
    def _stimulus_process_wrapper(stimulus_configuration, **enhanced_kwargs):
        """Wrapper for stimulus process compatible with ParallelManager."""
        in_queue = enhanced_kwargs.get("in_queue")
        out_queue = enhanced_kwargs.get("out_queue")
        stop_event = enhanced_kwargs.get("stop_event")
        logger = enhanced_kwargs.get("logger")

        try:
            if logger:
                logger.info("Starting stimulus manager process")
            else:
                print("Starting stimulus manager process")

            # Create stimulus manager instance
            stimulus_manager = StimulusManager(
                stimulus_configuration=stimulus_configuration,
                in_queue=in_queue,
                out_queue=out_queue,
            )

            # Start the stimulus manager
            stimulus_manager.start()

            # Keep running until stop event is set
            if stop_event:
                while not stop_event.is_set():
                    stop_event.wait(timeout=0.1)

        except Exception:
            if logger:
                logger.exception("Error in stimulus process")
            else:
                print("Error in stimulus process")
            raise
        finally:
            if logger:
                logger.info("Stimulus manager process shutting down")
            else:
                print("Stimulus manager process shutting down")

    @staticmethod
    def _behavior_process_wrapper(hardware_manager=None, response_log=None, timers=None, **enhanced_kwargs):
        """Wrapper for behavior process compatible with ParallelManager."""
        response_block = enhanced_kwargs.get("response_block")
        response_queue = enhanced_kwargs.get("response_queue")
        stop_event = enhanced_kwargs.get("stop_event")
        logger = enhanced_kwargs.get("logger")

        try:
            if logger:
                logger.info("Starting behavior manager process")
            else:
                print("Starting behavior manager process")

            # Create behavior instance
            behavior = Behavior(
                hardware_manager=hardware_manager,
                response_block=response_block,
                response_log=response_log,
                response_queue=response_queue,
                timers=timers,
            )

            # Start the behavior manager
            behavior.start()  # Assuming Behavior has a start method

            # Keep running until stop event is set
            if stop_event:
                while not stop_event.is_set():
                    stop_event.wait(timeout=0.1)

        except Exception:
            if logger:
                logger.exception("Error in behavior process")
            else:
                print("Error in behavior process")
            raise
        finally:
            if logger:
                logger.info("Behavior manager process shutting down")
            else:
                print("Behavior manager process shutting down")

    def initialize(self):
        """Starting required processes using enhanced ParallelManager."""
        init_successful = True
        try:
            # Start behavior process first (higher priority)
            if not self.parallel_manager.start_process("behavior"):
                raise RuntimeError("Failed to start behavior process")

            # Start stimulus process
            if not self.parallel_manager.start_process("stimulus"):
                raise RuntimeError("Failed to start stimulus process")

            # Wait for stimulus to start and send confirmation
            success, message = self.parallel_manager.wait_for_message(
                "stimulus",
                message_type="startup",
                timeout=10.0,
            )

            if not success:
                raise TimeoutError("Stimulus process did not start in time")

            # Check for display connection message
            success, message = self.parallel_manager.wait_for_message(
                "stimulus",
                timeout=5.0,
            )

            if success and isinstance(message, str) and message == "display_connected":
                print("Display started successfully")
            else:
                # Try to receive the message directly from the queue for backward compatibility
                try:
                    message = self.msg_from_stimulus.get(timeout=5)
                    if message == "display_connected":
                        print("Display started successfully")
                    else:
                        raise ValueError(f"Unexpected message: {message}")
                except Exception:
                    raise TimeoutError("Display did not connect in time")

        except Exception as e:
            print(f"Error in starting processes: {e}")
            init_successful = False
            # Cleanup on failure
            self.parallel_manager.stop_all_processes()
            raise e

        return init_successful

    def handle_terminal_request(self, message: dict):
        """Handle hardware request from terminal based on received message."""
        # Reward related changes
        if message["key"] == "reward_left":
            self.managers["hardware"].reward_left(message["value"])
            self.managers["session"].total_reward += message["value"]
        elif message["key"] == "reward_right":
            self.managers["hardware"].reward_right(message["value"])
            self.managers["session"].total_reward += message["value"]
        elif message["key"] == "toggle_left_reward":
            self.managers["hardware"].toggle_reward("Left")
        elif message["key"] == "toggle_right_reward":
            self.managers["hardware"].toggle_reward("Right")
        elif message["key"] == "update_reward":
            self.managers["session"].full_reward_volume = message["value"]
            print(f"NEW REWARD VALUE IS {self.managers['session'].full_reward_volume}")
        elif message["key"] == "calibrate_reward":
            if self.config.SUBJECT["name"] in ["XXX", "xxx"]:
                self.managers["hardware"].start_calibration_sequence()

        # Lick related changes
        elif message["key"] == "reset_lick_sensor":
            self.managers["hardware"].reset_lick_sensor()
            print("RESETTING LICK SENSOR")
        elif message["key"] == "update_lick_threshold_left":
            self.managers["hardware"].lick_threshold_left = message["value"]
            print(f'UPDATED LEFT LICK THRESHOLD with {message["value"]}')
            print(self.managers["hardware"].lick_threshold_left)
        elif message["key"] == "update_lick_threshold_right":
            self.managers["hardware"].lick_threshold_right = message["value"]
            print(f'UPDATED RIGHT LICK THRESHOLD with {message["value"]}')
            print(self.managers["hardware"].lick_threshold_right)

    def _handle_lick_requests(self, key: str, value: any) -> bool:
        """Handle lick sensor-related terminal requests."""
        if key == "reset_lick_sensor":
            self.managers["hardware"].reset_lick_sensor()
            print("RESETTING LICK SENSOR")
            return True
        elif key == "update_lick_threshold_left":
            self.managers["hardware"].lick_threshold_left = value
            print(f'UPDATED LEFT LICK THRESHOLD with {value}')
            print(self.managers["hardware"].lick_threshold_left)
            return True
        elif key == "update_lick_threshold_right":
            self.managers["hardware"].lick_threshold_right = value
            print(f'UPDATED RIGHT LICK THRESHOLD with {value}')
            print(self.managers["hardware"].lick_threshold_right)
            return True
        return False

    def prepare_session_files(self):
        """Prepare session files and directories."""
        self.config.FILES = {}
        data_path = Path(
            prefs.get("DATADIR"),
            self.config.SUBJECT["name"],
            self.config.SUBJECT["protocol"],
            self.config.SUBJECT["experiment"],
            self.config.SUBJECT["session"],
        )

        # Safely handle existing directory
        self._handle_existing_directory(data_path)

        # Create directory structure
        data_path.mkdir(parents=True, exist_ok=True)

        # Create file paths
        self._create_file_paths(data_path)

    def _handle_existing_directory(self, data_path: Path):
        """Safely handle existing directory by validating and cleaning."""
        if not data_path.exists():
            return

        if not data_path.is_dir():
            raise FileOperationError("creation", str(data_path), "Path exists but is not a directory")

        # Validate path is within expected data directory structure
        expected_base = Path(prefs.get("DATADIR"))
        try:
            data_path.relative_to(expected_base)
        except ValueError as exc:
            raise FileOperationError(
                "validation",
                str(data_path),
                "Path is outside expected data directory"
            ) from exc

        # Since main storage is on server, we will rewrite the directory if already exists
        # assuming that data is already on the server.
        self._safe_directory_cleanup(data_path)

    def _safe_directory_cleanup(self, directory: Path):
        """Safely clean directory contents with validation."""
        if not directory.exists() or not directory.is_dir():
            return

        try:
            for item in directory.iterdir():
                if item.is_file():
                    item.unlink()  # Delete files
                elif item.is_dir():
                    # Only remove empty subdirectories for safety
                    try:
                        item.rmdir()  # Delete empty subdirectories only
                    except OSError:
                        # Directory not empty, skip it for safety
                        print(f"Warning: Skipping non-empty directory: {item}")
        except (OSError, PermissionError) as exc:
            raise FileOperationError("cleanup", str(directory), str(exc)) from exc

    def _create_file_paths(self, data_path: Path):
        """Create file paths for the session."""
        for file_id, file in self.config.DATAFILES.items():
            self.config.FILES[file_id] = Path(data_path, self.config.SUBJECT["name"] + file)

        # Create rolling performance files
        self.config.FILES["rolling_perf_before"] = Path(data_path, "rolling_perf_before.pkl")
        self.config.FILES["rolling_perf_before"].write_bytes(
            pickle.dumps(self.config.SUBJECT["rolling_perf"])
        )
        self.config.FILES["rolling_perf_after"] = Path(data_path, "rolling_perf_after.pkl")
        self.config.FILES["rolling_perf"] = Path(data_path.parent, "rolling_perf.pkl")

    def pause(self):
        """Pause the task (placeholder for future implementation)."""

    def end(self):
        """End the task and cleanup all resources."""
        try:
            # End session updates
            self.managers["session"].end_of_session_updates()
            self.managers["hardware"].end_session()

            # Stop all managed processes gracefully
            self.parallel_manager.stop_all_processes(timeout=10.0)

        except Exception as e:
            print(f"Error during cleanup: {e}")
        finally:
            # Final cleanup
            self.parallel_manager.cleanup()

    def get_process_status(self):
        """Get status of all managed processes."""
        return {
            process_id: {
                "state": info.state.value,
                "cpu_percent": info.cpu_percent,
                "memory_percent": info.memory_percent,
                "restart_count": info.restart_count,
                "error_message": info.error_message,
            }
            for process_id, info in self.parallel_manager.get_all_processes().items()
        }

    def restart_process(self, process_id: str):
        """Restart a specific process."""
        return self.parallel_manager.restart_process(process_id)

    def send_stimulus_message(self, message, timeout=1.0):
        """Send message to stimulus process."""
        return self.parallel_manager.send_message("stimulus", message, timeout)

    def receive_stimulus_message(self, timeout=1.0):
        """Receive message from stimulus process."""
        return self.parallel_manager.receive_message("stimulus", timeout)

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit with cleanup."""
        self.end()


if __name__ == "__main__":

    from protocols.random_dot_motion.rt_dynamic_training import config

    full_coherences = config.TASK["stimulus"]["signed_coherences"]["value"]
    current_coherence_level = config.TASK["rolling_performance"]["current_coherence_level"]
    reward_volume = config.TASK["rolling_performance"]["reward_volume"]
    rolling_window = config.TASK["rolling_performance"]["rolling_window"]
    rolling_perf = {
        "rolling_window": rolling_window,
        "history": {int(coh): list(np.zeros(rolling_window).astype(int)) for coh in full_coherences},
        "history_indices": {int(coh): 49 for coh in full_coherences},
        "accuracy": {int(coh): 0 for coh in full_coherences},
        "current_coherence_level": current_coherence_level,
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
        "experiment": "rt_dynamic_training",
        "session": "1_1",
        "session_uuid": "XXXX",
        "rolling_perf": rolling_perf,
    }

    value = {
        "stage_block": threading.Event(),
        "protocol": "random_dot_motion",
        "experiment": "rt_dynamic_training",
        "config": config,
    }    # Use context manager for automatic cleanup
    with Task(**value) as task:
        # Initialize processes
        if not task.initialize():
            print("Failed to initialize task")
            sys.exit(1)

        stage_list = [
            task.managers["trial"].fixation_stage,
            task.managers["trial"].stimulus_stage,
            task.managers["trial"].reinforcement_stage,
            task.managers["trial"].intertrial_stage,
        ]
        num_stages = len(stage_list)
        stages = itertools.cycle(stage_list)

        # Main execution loop
        try:
            iteration = 0
            while True:
                # Check process health
                status = task.get_process_status()
                for process_id, proc_status in status.items():
                    if proc_status["state"] in ["ERROR", "CRASHED"]:
                        print(f"Process {process_id} failed: {proc_status['error_message']}")
                        # Attempt restart
                        if not task.restart_process(process_id):
                            print(f"Failed to restart {process_id}")
                            break

                data = next(stages)()
                # Waiting for stage block to clear
                value["stage_block"].wait()

                print("stage block passed")
                iteration += 1                # Optional: Add break condition for testing
                if iteration > MAX_TEST_ITERATIONS:
                    break

        except KeyboardInterrupt:
            print("Interrupted by user")
        except Exception as e:
            print(f"Error in main loop: {e}")
        finally:
            print("Task completed")
