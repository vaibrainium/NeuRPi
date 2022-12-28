# import time

# if __name__ == "__main__":

#     from NeuRPi.agents import test_pilot, test_terminal

#     test_pilot.main()
#     # test_terminal.main()
#     pass


import importlib
import threading

# from protocols.RDK.data_model.subject import Subject
from protocols.RDK.tasks.dynamic_training_rt import dynamic_training_rt

if __name__ == "__main__":
    stage_block = threading.Event()
    # dynamic_training_rt(stage_block, subject_name="PSUIM4")

    value = {
        "task_module": "RDK",
        "task_phase": "dynamic_training_rt",
        "subject_id": "PSUIM4",
    }

    # Importing protocol function/class object using importlib
    a = dynamic_training_rt(stage_block, **value)
