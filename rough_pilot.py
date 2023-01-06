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


if __name__ == "__main__":
    import queue

    stage_block = threading.Event()
    running = threading.Event()
    quitting = threading.Event()

    # Preparing task
    value = {
        "task_module": "RDK",
        "task_phase": "dynamic_training_rt",
        "subject_id": "PSUIM4",
    }
    stim_config = prepare_config(task_module=value["task_module"], filename="stimulus")
    stimulus_queue = queue.Queue()
    display = Stimulus_Display(
        stimulus_configuration=stim_config.STIMULUS, stimulus_courier=stimulus_queue
    )

    while True:
        print("Starting Fixation")
        message = "('initiate_fixation', {})"
        stimulus_queue.put(eval(message))
        time.sleep(2)
        print("Starting Stimulus")
        message = "('initiate_stimulus', {'seed': 1, 'coherence': 100, 'stimulus_size': (1920, 1280)})"
        stimulus_queue.put(eval(message))
        time.sleep(5)
        print("Starting Intertrial")
        message = "('initiate_intertrial', {})"
        stimulus_queue.put(eval(message))
        time.sleep(2)
        print("Loop complete")

    # # Importing protocol function/class object using importlib
    # config = prepare_config(
    #     task_module=value["task_module"], filename=value["task_phase"]
    # )
    # value["config"] = config
    # value["stimulus_queue"] = stimulus_queue
    # task = dynamic_training_rt(stage_block, **value)
    # running.set()

    # running.clear()
    # running.wait()
    # while True:
    #     stage = next(task.stages)
    #     print(stage)
    #     data = stage()

    #     stage_block.wait()

    #     # Has trial ended?
    #     if "TRIAL_END" in data.keys():
    #         running.wait()  # If paused, waiting for running event set?
    #         if quitting.is_set():  # is quitting event set?
    #             task.end_session()
    #             break  # Won't quit if the task is paused.
