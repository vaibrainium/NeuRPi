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
from protocols.random_dot_motion.rt_pulse.session_manager import SessionManager
from protocols.random_dot_motion.rt_pulse.stimulus_manager import StimulusManager

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
        experiment="rt_pulse",
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
        self.managers["hardware"].start_session(
            session_id=self.config.SUBJECT["session_uuid"],
        )
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

    # Reward management from GUI
    def handle_controller_request(self, message: dict):
        """Handle hardware request from controller based on received message"""
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
            if self.config.SUBJECT["id"] in ["XXX", "xxx"]:
                self.managers["hardware"].start_calibration_sequence()

        # Lick related changes
        elif message["key"] == "reset_lick_sensor":
            self.managers["hardware"].reset_lick_sensor()
            print("RESETTING LICK SENSOR")
        elif message["key"] == "update_lick_threshold_left":
            self.managers["hardware"].lick_threshold_left = message["value"]
            print(f"UPDATED LEFT LICK THRESHOLD with {message['value']}")
            print(self.managers["hardware"].lick_threshold_left)
        elif message["key"] == "update_lick_threshold_right":
            self.managers["hardware"].lick_threshold_right = message["value"]
            print(f"UPDATED RIGHT LICK THRESHOLD with {message['value']}")
            print(self.managers["hardware"].lick_threshold_right)

    def prepare_session_files(self):
        self.config.FILES = {}
        data_path = Path(
            prefs.get("DATADIR"),
            self.config.SUBJECT["id"],
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
                self.config.SUBJECT["id"] + file,
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
    from protocols.random_dot_motion.rt_pulse import config

    full_coherences = config.TASK["stimulus"]["signed_coherences"]["value"]
    # current_coherence_level = config.TASK["rolling_performance"]["current_coherence_level"]
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
        "experiment": "rt_pulse",
        "session": "1_1",
        "session_uuid": "XXXX",
        "rolling_perf": rolling_perf,
    }

    value = {
        "stage_block": threading.Event(),
        "protocol": "random_dot_motion",
        "experiment": "rt_pulse",
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
