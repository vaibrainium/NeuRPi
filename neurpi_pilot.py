if __name__ == "__main__":
    import multiprocessing
    import sys
    import threading

    from NeuRPi.agents.agent_pilot import Pilot

    quitting = threading.Event()
    quitting.clear()
    try:
        pi = Pilot()
        quitting.wait()
    except KeyboardInterrupt:
        quitting.set()
        active = multiprocessing.active_children()
        # terminate all active children
        for child in active:
            child.terminate()
        sys.exit()
