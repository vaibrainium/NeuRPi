from NeuRPi.stimulus.stimulus_manager import StimulusManager
from Protocols.RDK.stimulus.random_dot_kinematogram import RandomDotKinematogram


class RDKManager(StimulusManager):

    def __init__(self, configuration=None, courier=None, stimulus=RandomDotKinematogram):
        self.config = configuration
        self.courier = courier
        self.RDK = stimulus()

        self.courier_map = self.stim_config.courier_handle

        super(RDKManager, self).__init__(configuration=configuration, courier=courier)

    def initiate_fixation(self, pars):
        self.screen[0].fill(self.courier_map.initiate_fixation.visual.properties.generate.background)
        self.update()
        if self.courier_map.initiate_fixation.audio.need_update:
            self.pygame.mixer.Sound.stop()
            if self.courier_map.initiate_fixation.audio.is_static:
                self.audio['']

    def next_frame_fixation(self, pars):
        raise Warning('next_frame_fixation Function Not Implemented')

    def initiate_stimulus(self, pars):
        raise Warning('initiate_stimulus Function Not Implemented')

    def next_frame_stimulus(self, pars):
        raise Warning('next_frame_stimulus Function Not Implemented')

    def initiate_response(self, pars):
        raise Warning('initiate_response Function Not Implemented')

    def next_frame_response(self, pars):
        raise Warning('next_frame_response Function Not Implemented')

    def initiate_reinforcement(self, pars):
        raise Warning('initiate_reinforcement Function Not Implemented')

    def next_frame_reinforcement(self, pars):
        raise Warning('next_frame_reinforcement Function Not Implemented')

    def initiate_must_response(self, pars):
        raise Warning('initiate_must_response Function Not Implemented')

    def next_frame_must_response(self, pars):
        raise Warning('next_frame_must_response Function Not Implemented')

    def initiate_intertrial(self, pars):
        raise Warning('initiate_intertrial Function Not Implemented')

    def next_frame_intertrial(self, pars):
        raise Warning('next_frame_intertrial Function Not Implemented')

    def initiate_stimulus(self, pars):
        self.stimulus.new_stimulus(pars)

    def stimulus_next_frame(self):
        self.RDK.moveDots(self.frame_rate)
        func = self.stimulus_draw
        pars = {'ndots': self.RDK.nDots,
                'xpos': self.RDK.x,
                'ypos': self.RDK.y,
                'radius': [self.RDK.radius] * self.RDK.nDots,
                'color': [self.RDK.color] * self.RDK.nDots,
                }
        screen = 0
        return self.stimulus_draw, pars, screen

    def stimulus_draw(self, pars, screen=0):
        self.screen[screen].fill((0, 0, 0))
        for ind in range(len(pars['xpos'])):
            self.pygame.draw.circle(self.screen[screen], pars['color'][ind], (pars['xpos'][ind], pars['ypos'][ind]),
                                    pars['radius'][ind])

    # def fixation(self, screen=0):
    #     self.screen[screen].fill(eval(self.stim_config.fixation.background))
    #     if self.stim_config.fixation.audio:
    #         try:
    #             self.audio['fixation_onset'].play()
    #         except:
    #             raise Warning('fixation_onset audio path not set')
    #
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
