# import time

# if __name__ == "__main__":

#     from NeuRPi.agents import test_pilot, test_terminal


#     test_pilot.main()
#     # test_terminal.main()
#     pass


if __name__ == "__main__":
    import sys
    import threading

    from NeuRPi.agents.test_pilot import Pilot

    quitting = threading.Event()
    quitting.clear()
    try:
        pi = Pilot()
        pi.handshake()

        msg = {
            "subjectID": "PSUIM4",
            "task_module": "dynamic_coherence_rt",
            "task_phase": "4",
        }
        quitting.wait()

    except KeyboardInterrupt:
        quitting.set()
        sys.exit()
