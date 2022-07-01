import threading
from NeuRPi.stimulus.display import Display
from queue import Queue, Empty
import time
from RandomMotion import DotMotionStim

class StimWindow(Display):
    """
    Show Stimulus based on incoming messages. MUST CONTAIN FOLLOWING BASIC TRIAL PHASES:

    """

    def __init__(self, configuration=None, courier=None):
        self.courier = courier
        self.message = {}
        self.prev_message = {}
        self.render_block = threading.Event()
        self.render_block.clear()
        self.stim_config = configuration.STIMULUS
        self.frame_queue_size = 100
        self.frame_queue = Queue(maxsize=self.frame_queue_size)
        super(StimWindow, self).__init__(configuration=configuration)


        self.Dots = DotMotionStim()
        self.Dots.newStimulus(100, 1)
        # self.Dots.vel = self.stim_config.
        # self.thread = threading.Thread(target=self.run, args=[], daemon=False).start()
        self.thread = threading.Thread(target=self.render_visual, args=[], daemon=False).start()


        self.run()

    def get_messages(self):
        while True:
            if not self.courier.empty():
                self.message = self.courier.get()
                self.stim_block.set()

    def run(self):
        while True:
            if self.frame_queue.qsize() < self.frame_queue_size*0.2: # not self.frame_queue.full():
                for _ in range(self.frame_queue_size*70):
                    func = self.draw_stim
                    screen = 0
                    pars = self.next_frame_stim()
                    self.frame_queue.put([func, screen, pars])



    def render_visual(self):
        while True:
            (func, screen, pars) = self.frame_queue.get()
            func(screen=screen, pars=pars)
            self._display_fps(screen)
            self._update()




    def next_frame_stim(self):
        self.Dots.moveDots(self.frame_rate)
        pars = {'ndots': self.Dots.nDots,
                'xpos': self.Dots.x,
                'ypos': self.Dots.y,
                'radius': [self.Dots.radius] * self.Dots.nDots,
                'color': [self.Dots.color] * self.Dots.nDots,
                }
        return pars

    def draw_stim(self, screen=0, pars = {}):
        self.screen[screen].fill((0,0,0))
        for ind in range(len(pars['xpos'])):
            self.pygame.draw.circle(self.screen[screen], pars['color'][ind], (pars['xpos'][ind], pars['ypos'][ind]), pars['radius'][ind])



    #
    # def exec_func(self, function=None, is_static={'video': False, 'audio': False}, screen=0, *args, **kwargs):
    #     video, audio = [0, 0]
    #     while not self.stim_block.is_set():
    #         if not is_static['video'] or video == 0:
    #             video = 1
    #             function(*args, **kwargs)
    #             pass
    #
    #         if audio == 0:
    #             # First time excecuting function?
    #             if is_static['audio']:
    #                 loops = 0
    #             else:
    #                 loops = -1  # If continuously play tone
    #             self.audio['fixation_onset'].play(loops=loops)
    #             pass



    def fixation(self, screen=0):
        self.screen[screen].fill(eval(self.stim_config.fixation.background))
        if self.stim_config.fixation.audio:
            try:
                self.audio['fixation_onset'].play()
            except:
                raise Warning('fixation_onset audio path not set')
    #
    # def reinforcement(self, screen=0, outcome=None):
    #     if self.stim_config.reinfocement.audio:
    #         if outcome == 'Correct' and self.stim_config.reinfocement.audio.correct:
    #             try:
    #                 self.audio['correct'].play()
    #             except:
    #                 raise Warning('corect audio path not set')
    #         if outcome == 'Incorrect' and self.stim_config.reinfocement.audio.incorrect:
    #             try:
    #                 self.audio['incorrect'].play()
    #             except:
    #                 raise Warning('incorrect audio path not set')
    #         if outcome == 'Invalid' and self.stim_config.reinfocement.audio.invalid:
    #             try:
    #                 self.audio['invalid'].play()
    #             except:
    #                 raise Warning('invalid audio path not set')
    #
    # def stimulus(self, screen=0):
    #     raise Exception("Stimulus needs to be modified for each task")
    #
    # def intertrial(self, screen=0):
    #     self.screen[screen].fill(eval(self.stim_config.intertrial.background))
    #     if self.stim_config.intertrial.audio:
    #         try:
    #             self.audio['intertrial_onset'].play()
    #         except:
    #             raise Warning('intertrial_onset audio path not set')


if __name__ == '__main__':

    import hydra

    path = '../../Protocols/RDK/config'
    filename = 'dynamic_coherences'
    hydra.initialize(version_base=None, config_path=path)
    config = hydra.compose(filename, overrides=[])

    stim_window = StimWindow(configuration=config)
