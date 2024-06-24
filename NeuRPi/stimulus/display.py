import threading

# import multiprocessing
# from multiprocessing import Process, Queue
import time
from queue import Queue as thread_queue

import hydra
from omegaconf import DictConfig, OmegaConf


class Display:
    """
    Show Stimulus based on incoming messages. MUST CONTAIN FOLLOWING BASIC TRIAL PHASES:

    """

    def __init__(self, configuration=None, courier=None):
        super(Display, self).__init__()
        import pygame

        self.courier = courier
        self.message = {}

        self.lock = threading.Lock()
        self.render_block = threading.Event()
        self.render_block.clear()
        self.frame_queue_size = 100
        self.frame_queue = thread_queue(maxsize=self.frame_queue_size)

        self.stim_config = configuration.STIMULUS
        self.courier_map = self.stim_config.courier_handle
        self.window_size = eval(self.stim_config.display.window_size)

        self.pygame = pygame
        self.frame_rate = self.stim_config.display.frame_rate
        self.flags = eval(self.stim_config.display.flags)  # Converting flags from string to method name
        self.vsync = self.stim_config.display.vsync
        self.clock = self.pygame.time.Clock()
        self.screen = {}

        self.audio = {}
        self.video = {}
        self.start()

        threading.Thread(target=self.render_visual, args=[], daemon=False).start()
        threading.Thread(target=self.courier_manager, args=[], daemon=False).start()

    def get_configuration(self, directory=None, filename=None):
        """
        Getting configuration from respective config.yaml file.

        Arguments:
            directory (str): Path to configuration directory relative to root directory (as Protocols/../...)
            filename (str): Specific file name of the configuration file
        """
        path = "../../" + directory
        hydra.initialize(version_base=None, config_path=path)
        return hydra.compose(filename, overrides=[])

    def start(self):
        # Initialize all screens with black background
        self.pygame.init()
        self.pygame.mixer.init()
        self.pygame.font.init()
        self.font = self.pygame.font.SysFont("Arial", 20)

        if self.stim_config.display.num_screens == 1:
            self.screen[0] = self.pygame.display.set_mode(
                self.window_size,
                flags=self.flags,
                display=self.stim_config.display.screen,
                vsync=self.vsync,
            )
            self.screen[0].fill((0, 0, 0))
        else:
            for screen in range(self.stim_config.display.num_screens):
                exec(f"""self.screen[{screen}] = self.pygame.display.set_mode(self.window_size, flags=self.flags, display=screen, vsync=self.vsync)""")
                exec(f"""self.screen[{screen}].fill((0,0,0))""")
        self.update()

        self.gather_media()

        # Letting terminal agent know that display is ready
        while True:
            if self.pygame.display.get_init():
                self.courier.put(("info", "display_ready"))
                break

        # Waiting for terminal agent to send start signal
        while True:
            if not self.courier.empty():
                (message, arguments) = self.courier.get()
                if message == "start":
                    break

    def gather_media(self):
        for key, val in self.stim_config.courier_handle.items():
            if key not in ["tag", "type"]:
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
                        raise Warning(f"Could not initialize {file} in {key2} in {key}")
                    finally:
                        self.audio[key][key2] = temp_list
        else:
            for ind, file in enumerate(val):
                temp_list = []
                try:
                    pass
                    # temp_list.append(pygame.mixer.Sound(file))
                except:
                    raise Warning(f"Could not initialize {file} in {key}")
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
                        raise Warning(f"Could not initialize {file} in {key2} in {key}")
                    finally:
                        self.audio[key][key2] = temp_list
        else:
            for ind, file in enumerate(val):
                temp_list = []
                try:
                    temp_list.append(self.pygame.mixer.Sound(file))
                except:
                    raise Warning(f"Could not initialize {file} in {key}")
                finally:
                    self.audio[key] = temp_list

    def courier_manager(self):
        properties = OmegaConf.create({"visual": {"is_static": True, "need_update": True}})
        while 1:
            if not self.courier.empty():
                (message, arguments) = self.courier.get()
                properties = self.courier_map.get(message)
                if properties.visual.need_update:
                    self.clock = self.pygame.time.Clock()
                    self.frame_queue.queue.clear()
                function = eval("self." + properties.function)
                self.render_block.wait()
                try:
                    if arguments:
                        function(arguments)
                    else:
                        function()
                except:
                    raise Warning(f"Unable to process {function}")

            if properties.visual.is_static:
                self.frame_queue.queue.clear()
            else:
                if not self.frame_queue.full():
                    try:
                        (func, pars, screen) = eval("self." + properties.visual.update_function)()
                        self.frame_queue.put([func, pars, screen])
                    except:
                        raise Warning(f"Failed to update visual for {message}")

    def render_visual(self):
        self.render_block.set()
        while 1:
            if not self.frame_queue.empty():
                self.render_block.clear()
                (func, pars, screen) = self.frame_queue.get()
                self.lock.acquire()
                self.draw(func, pars, screen)
                self.lock.release()
                self.render_block.set()
                self.clock.tick_busy_loop(self.frame_rate)

    def draw(self, func, pars, screen):
        try:
            func(pars=pars, screen=screen)
        except:
            raise Warning(f"Rendering error: Unable to process {func}")

        if self.stim_config.display.show_fps:
            fps = self.font.render(str(int(self.clock.get_fps())), 1, self.pygame.Color("coral"))
            self.screen[screen].blit(fps, (1900, 1000))
        self.update()

    def update(self):
        self.pygame.display.update()
        self.pygame.event.pump()


if __name__ == "__main__":
    import hydra

    path = "../../Protocols/RDK/config"
    filename = "dynamic_coherences"
    hydra.initialize(version_base=None, config_path=path)
    config = hydra.compose(filename, overrides=[])

    display_window = Display(configuration=config)
