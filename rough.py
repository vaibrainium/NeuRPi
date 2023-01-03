# import time

# if __name__ == "__main__":

#     from NeuRPi.agents import test_pilot, test_terminal

#     test_pilot.main()
#     # test_terminal.main()
#     pass


# import importlib
# import threading

# # from protocols.RDK.data_model.subject import Subject
# from protocols.RDK.tasks.dynamic_training_rt import dynamic_training_rt

# if __name__ == "__main__":
#     stage_block = threading.Event()
#     # dynamic_training_rt(stage_block, subject_name="PSUIM4")

#     value = {
#         "task_module": "RDK",
#         "task_phase": "dynamic_training_rt",
#         "subject_id": "PSUIM4",
#     }

#     # Importing protocol function/class object using importlib
#     a = dynamic_training_rt(stage_block, **value)


# from NeuRPi.utils.get_config import get_configuration

# a = {
#     "test_a": "a",
#     "test_b": {"c": "c", "d": "d"},
# }

# directory = "protocols/RDK/config"
# filename = "dynamic_coherences.yaml"
# config = get_configuration(directory=directory, filename=filename)

import threading
import time

a = threading.Event()
a.clear()
a.set()
b = 2
print(time.time())
b = threading.Timer(20000000, lambda: None)
b.start()
print(time.time())
