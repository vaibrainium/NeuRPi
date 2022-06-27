import pygame
from queue import Queue, Empty
from omegaconf import DictConfig, OmegaConf


class Display():
    """
    Base class for video stimulus display. Defines display properties.
    """
    def __init__(self, configuration = None):
        """
        Inputs configuration file
        """
        self.stim_config = configuration.STIMULUS
        self.window_size = eval(self.stim_config.display.window_size)
        self.frame_rate = self.stim_config.display.frame_rate
        self.flags = eval(self.stim_config.display.flags)  # Converting flags from string to method name
        self.vsync = self.stim_config.display.vsync
        self.clock = pygame.time.Clock()
        self.screen = {}
        self.audio = {}

    def _start(self):
        # Initialize all screens with black background
        pygame.init()
        for screen in range(self.stim_config.display.num_screens):
            exec(f"""self.screen[{screen}] = pygame.display.set_mode(self.window_size, flags=self.flags, display=screen, vsync=self.vsync)""")
            exec(f"""self.screen[{screen}].fill((0,0,0))""")
        self._update()

        # Initialize and load audios
        pygame.mixer.init()
        self.load_audio(self.stim_config.audio)

    def load_audio(self, path_dict):
        for key, val in path_dict.items():
            if key != 'tag' and val:
                if isinstance(val, DictConfig):
                    self.load_audio(val)
                else:
                    try:
                        self.audio[key] = pygame.mixer.Sound(val)
                    except:
                        raise Warning(f'Could not initialize {key}')

    def _update(self):
        pygame.display.update()
        pygame.event.pump()

    def _end(self):
        pygame.quit()
