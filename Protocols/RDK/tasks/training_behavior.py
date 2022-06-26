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

    def __init__(self, hardware_manager=None, stage_block=None, response_block=None, response_handler=None):
        self.hardware_manager = hardware_manager
        self.stage_block = stage_block
        self.response_block = response_block
        self.trigger = {}
        self.response_handler = response_handler
        self.response = None
        self.response_time = None
        self.thread = None
        self.quit_monitoring = threading.Event()
        self.quit_monitoring.clear()

    def start(self):
        # Starting acquisition process on different thread
        if not self.response_handler:
            raise Warning('Starting behavior acquisition with monitoring for response')
        self.thread = threading.Thread(target=self._acquire, daemon=True).start()

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
                    self.response_handler.put(lick)


if __name__ == '__main__':
    pass
