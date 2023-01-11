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
        self.pygame = pygame
        self.clock = self.pygame.time.Clock()
        self.screen = {}

        self.audio = {}
        self.gen_visual = {}
        self._start()


    def _start(self):
        # Initialize all screens with black background
        self.pygame.init()
        self.pygame.mixer.init()
        self.pygame.font.init()
        self.font = self.pygame.font.SysFont("Arial", 20)

        if self.stim_config.display.num_screens == 1:
            self.screen[0] = self.pygame.display.set_mode(self.window_size, flags=self.flags,
                                                     display=eval(self.stim_config.display.screen), vsync=self.vsync)
            self.screen[0].fill((0, 0, 0))
        else:
            for screen in range(self.stim_config.display.num_screens):
                exec(
                    f"""self.screen[{screen}] = self.pygame.display.set_mode(self.window_size, flags=self.flags, display=screen, vsync=self.vsync)""")
                exec(f"""self.screen[{screen}].fill((0,0,0))""")
        self._update()

        self.gather_media()

    def gather_media(self):
        for key, val in self.stim_config.courier_handle.items():
            if key not in ['tag', 'type']:
                # exec(f"self.{key} = dict()")
                if val.visual.properties.load:
                    self.load_videos(key, val.audio.properties.load)
                if val.audio.properties.load:
                    self.load_audios(key, val.audio.properties.load)

    def load_videos(self, key, val):
        if isinstance(val, DictConfig):
            self.audio[key] = {}
            for key2, paths in val.items():
                for ind, file in enumerate(paths):
                    temp_list = []
                    try:
                        pass
                        # temp_list.append(pygame.mixer.Sound(file))
                    except:
                        raise Warning(f'Could not initialize {file} in {key2} in {key}')
                    finally:
                        self.audio[key][key2] = temp_list
        else:
            for ind, file in enumerate(val):
                temp_list = []
                try:
                    pass
                    # temp_list.append(pygame.mixer.Sound(file))
                except:
                    raise Warning(f'Could not initialize {file} in {key}')
                finally:
                    self.audio[key] = temp_list

    def load_audios(self, key, val):
        if isinstance(val, DictConfig):
            self.audio[key] = {}
            for key2, paths in val.items():
                for ind, file in enumerate(paths):
                    temp_list = []
                    try:
                        temp_list.append(self.pygame.mixer.Sound(file))
                    except:
                        raise Warning(f'Could not initialize {file} in {key2} in {key}')
                    finally:
                        self.audio[key][key2] = temp_list
        else:
            for ind, file in enumerate(val):
                temp_list = []
                try:
                    temp_list.append(self.pygame.mixer.Sound(file))
                except:
                    raise Warning(f'Could not initialize {file} in {key}')
                finally:
                    self.audio[key] = temp_list

    def _update(self):
        self.pygame.display.update()
        self.clock.tick(self.frame_rate)
        self.pygame.event.pump()

    def _display_fps(self, screen):
        fps = self.font.render(str(int(self.clock.get_fps())), 1, pygame.Color("coral"))
        self.screen[screen].blit(fps, (1900, 1000))

    def _end(self):
        self.pygame.quit()
