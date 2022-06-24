
import numpy as np
import threading
from queue import Queue, Empty
import time


class Behavior():
    """
    General class for monitoring behavior during the task. This also takes care of interacting between multiple
    hardwares (lick sensors, camera, rotary encoder etc). This class runs on it's own thread to achieve better accuracy.
    Arguments:
        HARDWARE (dict): Dictionary of all hardwares involved in the task.
        EVENT_FILE (dict): Event file details for exporting all events
        stage_block: Stage_Block event for controling trial progression
    """

    def __init__(self, hardwares={}, event_file=None, stage_block=None, trigger={}):
        self.hw = hardwares
        self.event_file = event_file
        self.stage_block = stage_block
        self.trigger = trigger
        self.queue = Queue
        self.response_block = threading.Event()
        self.response_block.clear()
        self.response = None
        self.response_time = None
        self.thread = None
        self.quit_monitoring = threading.Event()
        self.quit_monitoring.clear()

    def start(self):
        # Establishing connections with all hardwares
        for key in self.hw.keys():
            self.hw[key].connect()
        # Starting acquisition process on different thread
        self.thread = threading.Thread(target=self._acquire, daemon=True).start()
        self.thread = threading.Thread(target=self.monitor_trigger, daemon=True).start()
        # self._acquire()

    def stop(self):
        """
        Stopping all hardware communications and closing treads
        """
        # Closing all threads
        self.quit_monitoring.set()

        # Releasing connections with all hardwares
        for key in self.hw.keys():
            self.hw[key].release()

    def _acquire(self):
        while True:#not self.quit_monitoring.is_set():
            message = self.hw['Response'].read()
            if message:
                lick = int(message) - 3
                if lick == 1:
                    print("Left Spout Licked")
                elif lick == -1:
                    print("Left Spout Free")
                elif lick == 2:
                    print("Right Spout Licked")
                elif lick == -2:
                    print("Right Spout Free")

                # Passing information if trigger is requested
                if self.response_block.is_set():
                    self.queue.put(lick)


    def monitor_response(self):
        self.stage_block.set()
        while True:
            self.response = np.NAN
            self.response_time = np.NAN
            self.response_block.wait()
            try:
                # When agent is not supposed to respond
                if self.trigger['type'] == 'NoGO':
                    start = time.thread_time_ns()
                    wait_time = self.trigger['time']*1000  # Converting wait time from ms to ns
                    while start < wait_time:          # Waiting for response
                        if not self.queue.empty():
                            self.queue.clear()
                            self.monitor_response()
                    # NoGo is complete. Set stage_block to proceed with the task

                # When agent is supposed to respond
                elif self.trigger['type'] == 'GO':
                    start = time.thread_time_ns()
                    wait_time = self.trigger['time'] * 1000  # Converting wait time from ms to ns
                    while start < wait_time:            # Waiting for response
                        if not self.queue.empty():
                            self.response = self.queue.get()
                            self.response_time = time.thread_time_ns() - start
                            break
                    # Go is complete.

            except:
                raise Warning("Problem with response monitoring")

            self.response_block.clear()
            self.stage_block.set()











if __name__ == '__main__':
    HARDWARE = {
        'Arduino': {
            'Response': {'tag': "[Lick, Reward]",
                     'port': "COM7",
                     'baudrate': None,
                     'timeout': None
                     }
        },

        'GPIO': {
            'Stim_Onset': {'pin': None,
                           'tag': 'TTL'
                           },
            'Video_Monitor': {'pin': None,
                              'tag': 'Frame Time'}
        }
    }
    Behav = Behavior(HARDWARE)

    Behav.start()
    while True:
        pass
        # if KeyboardInterrupt:
        #     break