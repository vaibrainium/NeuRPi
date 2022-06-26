from NeuRPi.stimulus.video import Display

class RDK(Display):
    def __init__(self, config=None, courier=None):
        super(RDK, self).__init__(config)
        self.stim_config = self.config.STIMULUS
        self._start()
        self.load_audio(self.stim_config.audio)

    def load_audio(self, path_dict):
        for key, val in path_dict.items():
            if key != 'tag':
                if isinstance(val, dict):
                    pass

        # self.reward_tone = self.


    def fixation(self, screen=0):
        self.screen[screen].fill(self.stim_config.fixation.background)
        self.screen[screen].fill(self.stim_config.fixation.background)






if __name__ == '__main__':
    a = RDK()
    print(a)


# msg = ['Nil']
# prev_msg = ['Nil']
# Dots = DotMotionStim();
# Dots.vel = 1
#
# screen.fill((0, 0, 0))  # Display Black Screen
# pygame.display.update()
# pygame.event.pump()
#
# counter = 0
