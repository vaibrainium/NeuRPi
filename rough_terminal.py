import time

from NeuRPi.agents import agent_pilot

if __name__ == "__main__":

    from NeuRPi.agents import test_terminal

    test_terminal.main()
    pass


# import importlib
# import threading

# # from protocols.RDK.data_model.subject import Subject
# from protocols.RDK.tasks.dynamic_training_rt import dynamic_training_rt

# if __name__ == "__main__":
#     stage_block = threading.Event()
#     running = threading.Event()
#     quitting = threading.Event()

#     value = {
#         "task_module": "RDK",
#         "task_phase": "dynamic_training_rt",
#         "subject": "PSUIM4",
#     }

#     # Importing protocol function/class object using importlib
#     task = dynamic_training_rt(stage_block, **value)
#     running.set()

#     while True:
#         stage = next(task.stages)
#         print(stage)
#         data = stage()

#         stage_block.wait()

#         # Has trial ended?
#         if "TRIAL_END" in data.keys():
#             running.wait()  # If paused, waiting for running event set?
#             if quitting.is_set():  # is quitting event set?
#                 task.end_session()
#                 break  # Won't quit if the task is paused.
