import datetime
import itertools
import multiprocessing as mp
import pickle
import threading
from pathlib import Path

import numpy as np

from neurpi.prefs import prefs
from protocols.random_dot_motion.core.hardware.behavior import Behavior
from protocols.random_dot_motion.core.hardware.hardware_manager import HardwareManager
from protocols.random_dot_motion.core.task.rt_task import RTTask
from protocols.random_dot_motion.rt_directional_training.session_manager import (
    SessionManager,
)
from protocols.random_dot_motion.rt_directional_training.stimulus_manager import (
    StimulusManager,
)

# TODO: 1. Use subject_config["session_uuid"] instead of subject name for file naming
# TODO: 5. Make sure graduation is working properly
# TODO: 7. In future version, change mulitprocessing queue to zmq queue for better performance.
# # Create a ZeroMQ context
# context = zmq.Context()

# # Create a PUSH socket for sending data to the display process
# out_socket = context.socket(zmq.PUSH)
# out_socket.bind("tcp://localhost:5555")  # Replace with your desired endpoint

# # Create a PULL socket for receiving data from the display process
# in_socket = context.socket(zmq.PULL)
# in_socket.connect("tcp://localhost:5555")  # Connect to the same endpoint


# display = StimulusDisplay(stimulus_configuration=config, in_socket=in_socket, out_socket=out_socket)

# # Don't forget to close and destroy sockets when done
# in_socket.close()
# out_socket.close()
# context.term()


class Task:
    """
    Dynamic Training Routine with reaction time trial structure
    """

    def __init__(
        self,
        stage_block=None,
        protocol="random_dot_motion",
        experiment="rt_directional_training",
        config=None,
        **kwargs,
    ):
        self.protocol = protocol
        self.experiment = experiment
        self.config = config
        self.__dict__.update(kwargs)

        # Event locks, triggers and queues
        self.stage_block = stage_block
        self.response_block = mp.Event()
        self.response_block.clear()
        self.response_queue = mp.Queue()
        self.msg_to_stimulus = mp.Queue()
        self.msg_from_stimulus = mp.Queue()

        self.timers = {
            "session": datetime.datetime.now(),
            "trial": datetime.datetime.now(),
        }

        # Preparing session files
        self.prepare_session_files()

        # Preparing Managers
        self.managers = {}
        self.managers["hardware"] = HardwareManager()
        self.managers["hardware"].start_session()
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
        self.stages = self.managers["trial"].stages

        # Preparing stimulus and behavior processes
        self.processes = {}
        self.processes["stimulus"] = StimulusManager(
            stimulus_configuration=config.STIMULUS,
            in_queue=self.msg_to_stimulus,
            out_queue=self.msg_from_stimulus,
        )
        self.processes["behavior"] = Behavior(
            hardware_manager=self.managers["hardware"],
            response_block=self.response_block,
            response_log=self.config.FILES["lick"],
            response_queue=self.response_queue,
            timers=self.timers,
        )

    def initialize(self):
        """Starting required processes"""
        init_successful = True
        try:
            self.processes["behavior"].start()
            self.processes["stimulus"].start()
            # wait for stimulus to start
            message = self.msg_from_stimulus.get(timeout=5)
            if message != "display_connected":
                raise TimeoutError("Display did not start in time")
                init_successful = False
            print("Display started")

        except Exception as e:
            print(f"Error in starting processes: {e}")
            raise e
            init_successful = False

        return init_successful

    def handle_controller_request(self, message: dict):
        """Handle hardware request from controller based on received message."""
        key = message.get("key")
        value = message.get("value")

        # Reward-related
        if key == "reward_left":
            self.managers["hardware"].reward_left(value)
            self.managers["session"].total_reward += value

        elif key == "reward_right":
            self.managers["hardware"].reward_right(value)
            self.managers["session"].total_reward += value

        elif key == "toggle_left_reward":
            self.managers["hardware"].toggle_reward("Left")

        elif key == "toggle_right_reward":
            self.managers["hardware"].toggle_reward("Right")

        elif key == "update_reward":
            self.managers["session"].full_reward_volume = value
            print(f"[INFO] Updated full reward volume to {value}")

        elif key == "calibrate_reward":
            if self.config.SUBJECT["name"].lower() == "xxx":
                self.managers["hardware"].start_calibration_sequence()

        # LED-related
        elif key == "flash_led_left":
            duration = self.managers["session"].knowledge_of_results_duration
            self.managers["hardware"].flash_led(-1, duration)

        elif key == "flash_led_center":
            duration = self.managers["session"].knowledge_of_results_duration
            self.managers["hardware"].flash_led(0, duration)

        elif key == "flash_led_right":
            duration = self.managers["session"].knowledge_of_results_duration
            self.managers["hardware"].flash_led(1, duration)

        elif key == "toggle_led_left":
            self.managers["hardware"].toggle_led(-1)

        elif key == "toggle_led_center":
            self.managers["hardware"].toggle_led(0)

        elif key == "toggle_led_right":
            self.managers["hardware"].toggle_led(1)

        # Combined LED and Reward
        elif key == "led_and_reward_left":
            duration = self.managers["session"].knowledge_of_results_duration
            self.managers["hardware"].flash_led(-1, duration)
            self.managers["hardware"].reward_left(value)
            self.managers["session"].total_reward += value

        elif key == "led_and_reward_right":
            duration = self.managers["session"].knowledge_of_results_duration
            self.managers["hardware"].flash_led(1, duration)
            self.managers["hardware"].reward_right(value)
            self.managers["session"].total_reward += value

        # Lick-related
        elif key == "reset_lick_sensor":
            self.managers["hardware"].reset_lick_sensor()
            print("[INFO] Resetting lick sensor.")

        elif key == "update_lick_threshold_left":
            self.managers["hardware"].lick_threshold_left = value
            print(f"[INFO] Updated LEFT lick threshold to {value}")

        elif key == "update_lick_threshold_right":
            self.managers["hardware"].lick_threshold_right = value
            print(f"[INFO] Updated RIGHT lick threshold to {value}")

        else:
            print(f"[WARNING] Unknown controller command received: {key}")

    def prepare_session_files(self):
        self.config.FILES = {}
        data_path = Path(
            prefs.get("DATADIR"),
            self.config.SUBJECT["name"],
            self.config.SUBJECT["protocol"],
            self.config.SUBJECT["experiment"],
            self.config.SUBJECT["session"],
        )
        # since main storage is on controller, we will rewrite the directory if already exists assuming that data is already on the controller.
        if data_path.exists() and data_path.is_dir():
            # If it exists, delete it and its contents
            for item in data_path.iterdir():
                if item.is_file():
                    item.unlink()  # Delete files
                elif item.is_dir():
                    item.rmdir()  # Delete subdirectories
        data_path.mkdir(parents=True, exist_ok=True)  # Recreate the directory
        for file_id, file in self.config.DATAFILES.items():
            self.config.FILES[file_id] = Path(
                data_path,
                self.config.SUBJECT["name"] + file,
            )
        self.config.FILES["rolling_perf_before"] = Path(
            data_path,
            "rolling_perf_before.pkl",
        )
        self.config.FILES["rolling_perf_before"].write_bytes(
            pickle.dumps(self.config.SUBJECT["rolling_perf"]),
        )
        self.config.FILES["rolling_perf_after"] = Path(
            data_path,
            "rolling_perf_after.pkl",
        )
        self.config.FILES["rolling_perf"] = Path(data_path.parent, "rolling_perf.pkl")

    def pause(self):
        pass

    def end(self):
        self.managers["session"].end_of_session_updates()
        self.managers["hardware"].end_session()
        self.processes["stimulus"].stop()
        self.processes["behavior"].stop()


if __name__ == "__main__":
    from protocols.random_dot_motion.rt_directional_training import config

    full_coherences = config.TASK["stimulus"]["signed_coherences"]["value"]
    # current_coherence_level = config.TASK["rolling_performance"]["current_coherence_level"]
    reward_volume = config.TASK["rolling_performance"]["reward_volume"]
    rolling_window = config.TASK["rolling_performance"]["rolling_window"]
    rolling_perf = {
        "rolling_window": rolling_window,
        "history": {
            int(coh): list(np.zeros(rolling_window).astype(int))
            for coh in full_coherences
        },
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

    value = {
        "stage_block": threading.Event(),
        "protocol": "random_dot_motion",
        "experiment": "rt_directional_training",
        "config": config,
    }

    task = Task(**value)

    stage_list = [
        task.managers["trial"].fixation_stage,
        task.managers["trial"].stimulus_stage,
        task.managers["trial"].reinforcement_stage,
        task.managers["trial"].intertrial_stage,
    ]
    num_stages = len(stage_list)
    stages = itertools.cycle(stage_list)

    # stages =
    iteration = 0
    while True:
        data = next(stages)()
        # Waiting for stage block to clear
        value["stage_block"].wait()

        # print(f"completed {data['trial_stage']}")
        print("stage block passed")
