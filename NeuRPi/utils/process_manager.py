import multiprocessing
import threading
from queue import Empty


class CommunicationProcess(multiprocessing.Process):
    def __init__(self, target_func, args=(), in_queue=None, out_queue=None, stop_event=None, daemon=True):
        super(CommunicationProcess, self).__init__()
        self.target_func = target_func
        self.in_queue = in_queue or multiprocessing.Queue()
        self.out_queue = out_queue or multiprocessing.Queue()
        self.stop_event = stop_event or multiprocessing.Event()
        self.args = args
        self.daemon = daemon  # if True, the process will be terminated when the main process ends

    def run(self):
        try:
            self.target_func(self.in_queue, self.out_queue, self.stop_event, *self.args)
        finally:
            if self.daemon:
                multiprocessing.current_process().terminate()


class QueueObserver(threading.Thread):
    def __init__(self, in_queue, update_screen):
        super().__init__()
        self.in_queue = in_queue
        self.update_screen = update_screen
        self.stop_event = threading.Event()

    def run(self):
        while not self.stop_event.is_set():
            try:
                (func, args, screen_name) = self.in_queue.get(block=True, timeout=0.1)
                self.update_screen(func, args, screen_name)
            except Empty:
                pass
            except Exception as e:
                print(f"Error: {e}")

    def stop(self):
        self.stop_event.set()
