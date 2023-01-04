import threading
import time
from queue import Queue


class Behavior:
    """
    General class for monitoring behavior during the task. This also takes care of interacting between multiple
    hardwares (lick sensors, camera, rotary encoder etc). This class runs on its own thread to achieve better accuracy.
    Arguments:
        hardware_manager (class instance): Hardware manager for monitoring and giving rewards
        stage_block: Stage_Block event for controlling trial progression
    """

    def __init__(
        self, hardware_manager=None, response_block=None, response_log=None, timers=None
    ):

        self.hardware_manager = hardware_manager
        self.response_block = response_block
        self.response_log = response_log
        self.timers = timers

        self.thread = None
        self.response_queue = Queue()
        self.quit_monitoring = threading.Event()
        self.quit_monitoring.clear()

    def start(self, session_timer=None):
        self.session_timer = session_timer
        # Starting acquisition process on different thread
        if not self.response_queue:
            raise Warning(
                "Starting behavior acquisition without monitoring for response"
            )

        self.thread = threading.Thread(target=self._acquire, daemon=True)
        self.thread.start()

    def _acquire(self):

        while not self.quit_monitoring.is_set():
            lick = self.hardware_manager.read_licks()
            if lick:
                # Passing information if trigger is requested
                if self.response_block.is_set():
                    self.response_queue.put(lick)

                with open(self.response_log, "a+") as file:
                    if lick == 1:
                        left_clock_start = time.time()
                    elif lick == -1:
                        left_clock_end = time.time()
                        left_dur = left_clock_end - left_clock_start
                        file.write(
                            "%.6f, %.6f, %s, %.6f\n"
                            % (
                                left_clock_start - self.timers["session"],
                                left_clock_start - self.timers["trial"],
                                lick,
                                left_dur,
                            )
                        )
                    elif lick == 2:
                        right_clock_start = time.time()
                    elif lick == -2:
                        right_clock_end = time.time()
                        right_dur = right_clock_end - right_clock_start
                        file.write(
                            "%.6f, %.6f, %s, %.6f\n"
                            % (
                                right_clock_start - self.timers["session"],
                                right_clock_start - self.timers["trial"],
                                lick,
                                right_dur,
                            )
                        )

    def stop(self):
        """
        Stopping all hardware communications and closing treads
        """
        # Closing all threads
        self.quit_monitoring.set()
        self.thread.join()


if __name__ == "__main__":
    pass
