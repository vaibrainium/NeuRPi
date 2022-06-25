
import numpy as np
import threading
from queue import Queue, Empty
import time


class Behavior():
    """
    General class for monitoring behavior during the task. This also takes care of interacting between multiple
    hardwares (lick sensors, camera, rotary encoder etc). This class runs on its own thread to achieve better accuracy.
    Arguments:
        hardware_manager (class instance): Hardware manager for monitoring and giving rewards
        stage_block: Stage_Block event for controlling trial progression
    """

    def __init__(self, hardware_manager= None, stage_block=None):
        self.hardware_manager = hardware_manager
        self.stage_block = stage_block
        self.trigger = {}
        self.queue = Queue()
        self.response_block = threading.Event()
        self.response_block.clear()
        self.response = None
        self.response_time = None
        self.thread = None
        self.quit_monitoring = threading.Event()
        self.quit_monitoring.clear()

    def start(self):
        # Starting acquisition process on different thread
        self.thread = threading.Thread(target=self._acquire).start()
        self.thread = threading.Thread(target=self.monitor_response).start()

    def stop(self):
        """
        Stopping all hardware communications and closing treads
        """
        # Closing all threads
        self.quit_monitoring.set()

    def _acquire(self):
        while not self.quit_monitoring.is_set():
            lick = self.hardware_manager.read_licks()
            if lick:
                # Passing information if trigger is requested
                if self.response_block.is_set():
                    self.queue.put(lick)


    def monitor_response(self):
        """
        Monitoring response from agent when requested by 'response_block.set()'.
        Monitoring can be either GO or NoGO for requested time. Conditions are passed by
        setting 'self.trigger' dictionary type: NoGO/GO and time: float in ms
        """
        while True:
            self.response = np.NAN
            self.response_time = np.NAN
            self.response_block.wait()
            try:
                # When agent is not supposed to respond
                if self.trigger['type'] == 'NoGO':
                    start = time.time()
                    wait_time = self.trigger['time']/1000  # Converting wait time from ms to sec
                    while time.time() - start < wait_time:          # Waiting for response
                        if not self.queue.empty():
                            self.queue.queue.clear()
                            self.monitor_response()
                    # NoGo is complete. Set stage_block to proceed with the task


                # When agent is supposed to respond
                elif self.trigger['type'] == 'GO':
                    start = time.time()
                    wait_time = self.trigger['time'] / 1000  # Converting wait time from ms to sec
                    while time.time() - start < wait_time:            # Waiting for response
                        if not self.queue.empty():
                            self.response = self.queue.get()
                            self.response_time = time.time() - start
                            break
                    # Go is complete.

            except:
                raise Warning("Problem with response monitoring")

            finally:
                self.trigger = None
                self.response_block.clear()
                self.stage_block.set()











if __name__ == '__main__':
    pass