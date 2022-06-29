import pygame
from queue import Queue, Empty
from omegaconf import DictConfig, OmegaConf


class Display():
    """
    Base class for video stimulus display. Defines display properties.
    """

    def __init__(self, configuration=None):
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
        self._start()

    def _start(self):
        # Initialize all screens with black background
        pygame.init()
        if self.stim_config.display.num_screens == 1:
            self.screen[0] = pygame.display.set_mode(self.window_size, flags=self.flags,
                                                     display=self.stim_config.display.screen, vsync=self.vsync)
            self.screen[0].fill((0, 0, 0))
        else:
            for screen in range(self.stim_config.display.num_screens):
                exec(
                    f"""self.screen[{screen}] = pygame.display.set_mode(self.window_size, flags=self.flags, display=screen, vsync=self.vsync)""")
                exec(f"""self.screen[{screen}].fill((0,0,0))""")
        self._update()
        # Initialize and load audios
        pygame.mixer.init()
        self.load_source_files(self.stim_config.courier_handle)

    def load_source_files(self, path_dict):
        for key, val in path_dict.items():
            if key not in ['tag', 'type'] and val.audio.properties.load:
                self.load_source_audios(key, val.audio.properties.load)

    def load_source_audios(self, key, val):
        if isinstance(val, DictConfig):
            self.audio[key] = {}
            for key2, paths in val.items():
                for ind, file in enumerate(paths):
                    temp_list = []
                    try:
                        temp_list.append(pygame.mixer.Sound(file))
                    except:
                        raise Warning(f'Could not initialize {file} in {key2} in {key}')
                    finally:
                        self.audio[key][key2] = temp_list
        else:
            for ind, file in enumerate(val):
                temp_list = []
                try:
                    temp_list.append(pygame.mixer.Sound(file))
                except:
                    raise Warning(f'Could not initialize {file} in {key}')
                finally:
                    self.audio[key] = temp_list


    def _update(self):
        pygame.display.update()
        pygame.event.pump()

    def _end(self):
        pygame.quit()
