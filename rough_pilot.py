
if __name__ == "__main__":
    import multiprocessing
    import sys
    import threading

    from NeuRPi.agents.test_pilot import Pilot

    quitting = threading.Event()
    quitting.clear()
    try:
        pi = Pilot()
        pi.handshake()

        msg = {
            "subject_id": "PSUIM4",
            "task_module": "RDK",
            "task_phase": "dynamic_training_rt",
        }
        pi.l_start(msg)
        quitting.wait()

    except KeyboardInterrupt:
        quitting.set()
        active = multiprocessing.active_children()
        # terminate all active children
        for child in active:
            child.terminate()
        sys.exit()
