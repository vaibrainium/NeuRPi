import multiprocessing as mp
import threading
import time


class Behavior:
    """
    General class for monitoring behavior during the task. This also takes care of interacting between multiple
    hardwares (lick sensors, camera, rotary encoder etc). This class runs on its own thread to achieve better accuracy.
    Arguments:
        hardware_manager (class instance): Hardware manager for monitoring and giving rewards
        stage_block: Stage_Block event for controlling trial progression
    """

    def __init__(
        self,
        hardware_manager=None,
        response_block=None,
        response_queue=None,
        response_log=None,
        timers=None,
    ):
        self.hardware_manager = hardware_manager
        self.response_block = response_block
        self.response_queue = response_queue
        self.response_log = response_log
        self.timers = timers

        self.process = None
        self.quit_monitoring = threading.Event()
        self.quit_monitoring.clear()

    def start(self):
        # self.session_timer = session_timer
        # Starting acquisition process on different thread
        if not self.response_queue:
            raise Warning("Starting behavior acquisition without monitoring for response")

        self.process = mp.Process(
            target=self._acquire,
            args=(
                self.response_block,
                self.response_queue,
            ),
            daemon=True,
        )
        self.process.start()

    def _acquire(self, response_block=None, response_queue=None):
        left_clock_start = time.time()
        right_clock_start = time.time()

        while not self.quit_monitoring.is_set():
            hw_timestamp, lick = self.hardware_manager.read_licks()
            if lick is not None:
                # Passing information if trigger is requested
                if response_block.is_set():
                    if lick == -1 or lick == 1:
                        response_queue.put(lick)

                with open(self.response_log, "a+") as file:
                    if lick == -1:
                        left_clock_start = time.time()
                    elif lick == -2:
                        left_clock_end = time.time()
                        left_dur = left_clock_end - left_clock_start
                        file.write(
                            "%.6f, %.6f, %.6f, %s, %.6f\n"
                            % (
                                hw_timestamp,
                                left_clock_start - self.timers["session"].timestamp(),
                                left_clock_start - self.timers["trial"].timestamp(),
                                lick,
                                left_dur,
                            )
                        )
                    elif lick == 1:
                        right_clock_start = time.time()
                    elif lick == 2:
                        right_clock_end = time.time()
                        right_dur = right_clock_end - right_clock_start
                        file.write(
                            "%.6f, %.6f, %.6f, %s, %.6f\n"
                            % (
                                hw_timestamp,
                                right_clock_start - self.timers["session"].timestamp(),
                                right_clock_start - self.timers["trial"].timestamp(),
                                lick,
                                right_dur,
                            )
                        )

    def stop(self):
        """
        Stopping all hardware communications and closing treads
        """
        # Closing all
        # self.hardware_manager.close_hardware()
        self.quit_monitoring.set()
        self.process.kill()


if __name__ == "__main__":
    pass
