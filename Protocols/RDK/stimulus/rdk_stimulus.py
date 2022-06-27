from NeuRPi.stimulus.stim_window import StimWindow
import threading


class RDKStimulus(StimWindow):
    def __init__(self, configuration=None, courier=None):
        self.config = configuration
        self.courier = courier
        self.stim_block = threading.Event()
        self.stim_block.clear()

        super(RDKStimulus, self).__init__()
        self.thread = threading.Thread(target=self.get_messages(), args=[], daemon=True).start()
        self.run()

    def get_messages(self):
        while True:
            if not self.courier.empty():
                self.message = self.courier.get()
                self.stim_block.set()

    def run(self):
        self.courier_map = self.stim_config.courier_handle

        while True:
            self.stim_block.wait()
            self.stim_block.clear()
            properties = self.courier_map.get(self.message)
            function = eval('self.' + properties.function)
            function(is_static=properties.is_static)

    def run_func(self, function=None, is_static={'video': False, 'audio': False}, screen=0, *args, **kwargs):
        video, audio = [0, 0]
        while not self.stim_block.is_set():
            if not is_static['video'] or video == 0:
                video = 1
                function(*args, **kwargs)
                pass

            if not is_static['audio'] or audio == 0:
                audio = 1
                pass

