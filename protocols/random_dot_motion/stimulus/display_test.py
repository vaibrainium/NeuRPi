import os
import threading
import time
from queue import Queue as thread_queue

import hydra
from omegaconf import DictConfig, OmegaConf


class Display:
    """
    Show Stimulus based on incoming messages.

    """

    def __init__(self, stimulus_configuration):
        super(Display, self).__init__()
        import pygame

        # When ssh, use display 'hostname:Display.ScreenNo'. In this case using localhost:0.0 or :0.0
        os.environ["DISPLAY"] = ":0.0"

        self.lock = threading.Lock()
        self.render_block = threading.Event()

        self.pygame = pygame

        self.stim_config = stimulus_configuration
        self.courier_map = self.stim_config.courier_handle
        self.window_size = eval(self.stim_config.display.window_size)

        self.frame_rate = self.stim_config.display.frame_rate
        self.flags = eval(
            self.stim_config.display.flags
        )  # Converting flags from string to method name
        self.vsync = self.stim_config.display.vsync
        self.clock = self.pygame.time.Clock()
        self.screen = {}

        self.audio = {}
        self.video = {}

    def start(self):
        # Initialize all screens with black background
        self.pygame.init()
        self.pygame.mixer.init()
        self.pygame.font.init()
        self.pygame.mouse.set_visible(False)
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
                exec(
                    f"""self.screen[{screen}] = self.pygame.display.set_mode(self.window_size, flags=self.flags, display=screen, vsync=self.vsync)"""
                )
                exec(f"""self.screen[{screen}].fill((0,0,0))""")
        self.update()

        # self.gather_media()

        # threading.Thread(target=self.render_visual, args=[], daemon=False).start()
        # threading.Thread(target=self.courier_manager, args=[], daemon=False).start()

    def courier_manager(self):
        properties = OmegaConf.create(
            {"visual": {"is_static": True, "need_update": True}}
        )
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
                        (func, pars, screen) = eval(
                            "self." + properties.visual.update_function
                        )()
                        self.frame_queue.put([func, pars, screen])
                    except:
                        raise Warning(f"Failed to update visual for {message}")

    def render_visual(self):
        self.render_block.set()
        while 1:
            # self.render_block.clear()
            # (func, pars, screen) = self.frame_queue.get()
            self.lock.acquire()
            # start = time.time()
            self.draw(0)  # func, pars, screen)
            # end = time.time()
            self.lock.release()
            self.render_block.set()
            self.clock.tick_busy_loop(self.frame_rate)
            # print(f"Render Time: {end-start}")

    def draw(self, screen):  # , func, pars, screen):
        # try:
        #     func(pars=pars, screen=screen)
        # except:
        #     raise Warning(f"Rendering error: Unable to process {func}")
        self.screen[screen].fill([0, 0, 0])
        fps = self.font.render(
            str(int(self.clock.get_fps())), 1, self.pygame.Color("coral")
        )
        self.screen[screen].blit(fps, (1900, 1000))
        self.update()

    def update(self):
        # TODO: display.update is slow. Need to find a way to update only the changed pixels
        self.pygame.display.update()
        # self.pygame.event.pump()


if __name__ == "__main__":
    import time
    import timeit
    from multiprocessing import Queue

    import hydra

    path = "../../random_dot_motion/config"
    filename = "free_reward_training.yaml"
    hydra.initialize(version_base=None, config_path=path)
    config = hydra.compose(filename, overrides=[])
    config.STIMULUS.display.frame_rate = 100
    # courier = Queue()
    display_window = Display(stimulus_configuration=config.STIMULUS)
    display_window.start()
    time.sleep(3)
    # start = time.time()
    # while True:
    #     display_window.update()

    # Measure the execution time of the function
    execution_time = timeit.timeit(display_window.update, number=100)
    print("Execution time:", execution_time)
