# import time

# if __name__ == "__main__":

#     from NeuRPi.agents import test_pilot, test_terminal

import multiprocessing as mp
import threading

#     test_pilot.main()
#     # test_terminal.main()
#     pass
import time

# from protocols.RDK.data_model.subject import Subject
from NeuRPi.utils.get_config import get_configuration
from protocols.RDK.stimulus.dynamic_training_rt import Stimulus_Display
from protocols.RDK.stimulus.random_dot_kinematogram import RandomDotKinematogram
from protocols.RDK.tasks.dynamic_training_rt import dynamic_training_rt


def prepare_config(task_module, filename):
    # Preparing parameters parameters
    directory = "protocols/" + task_module + "/config"
    filename = filename  # "dynamic_coherences_rt.yaml"
    config = get_configuration(directory=directory, filename=filename)
    return config


def start_display(value):
    stim_config = prepare_config(task_module=value["task_module"], filename="stimulus")
    display = Stimulus_Display(
        stimulus_configuration=stim_config.STIMULUS,
        stimulus_courier=value["stimulus_queue"],
    )


def run_task(value):

    # Importing protocol function/class object using importlib
    config = prepare_config(
        task_module=value["task_module"], filename=value["task_phase"]
    )
    value["config"] = config
    # value["stimulus_queue"] = stimulus_queue
    task = dynamic_training_rt(stage_block, **value)
    running.set()

    while True:
        stage = next(task.stages)
        print(stage)
        data = stage()

        stage_block.wait()

        # Has trial ended?
        if "TRIAL_END" in data.keys():
            running.wait()  # If paused, waiting for running event set?
            if quitting.is_set():  # is quitting event set?
                task.end_session()
                break  # Won't quit if the task is paused.


if __name__ == "__main__":

    stage_block = threading.Event()
    running = threading.Event()
    quitting = threading.Event()

    # Preparing task
    value = {
        "task_module": "RDK",
        "task_phase": "dynamic_training_rt",
        "subject_id": "PSUIM4",
    }
    value["stimulus_queue"] = mp.Manager().Queue()

    mp.Process(target=start_display, args=(value,)).start()
    run_task(value)
