import pygame
from queue import Queue, Empty


class Display():
    """
    Base class for video stimulus display. Defines display properties.
    """
    def __init__(self, configuration = None):
        """
        Inputs configuration file
        """
        self.config = configuration.STIMULUS
        self.window_size = self.config.display.window_size
        self.frame_rate = self.config.display.frame_rate
        self.flags = self.config.display.flags
        self.vsync = self.config.display.vsync
        self.clock = pygame.time.Clock()
        self.screen = {}

    def _start(self):
        pygame.init()
        pygame.mixer.init()
        # Initialize all screens with black background
        for screen in range(self.config.display.num_screens):
            exec(f"""self.screen[{screen}] = self.pygame.display.set_mode(self.window_size, flags=self.config.display.flags, display=screen, vsync=self.vsync""")
            exec(f"""self.screen[{screen}].fill(0,0,0)""")
        self._update()

    def _update(self):
        pygame.display.update()
        pygame.event.pump()

    def _audio(self, tone):
        if tone not None:
        pygame.mixer.Sound.play(tone)

    def _end(self):
        pygame.quit()
