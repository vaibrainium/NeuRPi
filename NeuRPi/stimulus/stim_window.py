import pygame.mixer
from NeuRPi.stimulus.display import Display

class StimWindow(Display):

    def __init__(self, config=None, courier=None):
        self.courier = courier
        self.message = {}
        self.prev_message = {}

        super(StimWindow, self).__init__(config)
        self._start()
        self.run()


    def run(self):
        raise Exception("Stimulus needs to be modified for each task")


    # def fixation(self, screen=0):
    #     self.screen[screen].fill(eval(self.stim_config.fixation.background))
    #     if self.stim_config.fixation.audio:
    #         try:
    #             self.audio['fixation_onset'].play()
    #         except:
    #             raise Warning('fixation_onset audio path not set')
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

    stim_window = StimWindow(config=config)
