import os
import threading
from queue import Queue
from NeuRPi.prefs import prefs
import logging


class Display:
    """
    Show Stimulus based on incoming messages.

    """

    def __init__(self, stimulus_configuration=None, in_queue=None, out_queue=None):

        import pygame

        # When ssh, use display 'hostname:Display.ScreenNo'. In this case using localhost:0.0 or :0.0
        os.environ["DISPLAY"] = ":0.0"
        os.environ["PYGAME_BLEND_ALPHA_SDL2"] = "1"
        os.environ["ENABLE_ARM_NEON"] = "1"
        os.environ["PYGAME_HWACCEL"] = "1"

        self.stimulus_config = stimulus_configuration
        self.in_queue = in_queue
        self.out_queue = out_queue
        self.message = {}

        self.lock = threading.Lock()
        self.render_block = threading.Event()
        self.render_block.clear()
        self.epoch_update_event = threading.Event()
        self.epoch_update_event.clear()
        self.frame_queue_size = 100
        self.frame_queue = Queue(maxsize=self.frame_queue_size)

        self.display_config = prefs.get("HARDWARE")["Display"]

        self.pygame = pygame

        self.frame_rate = self.display_config["max_fps"]
        try:
            self.flags = 0
            for flag in self.display_config["flags"]:
                self.flags |= getattr(self.pygame, flag)
        except:
            self.flags = self.pygame.FULLSCREEN | self.pygame.SCALED | self.pygame.DOUBLEBUF | self.pygame.HWSURFACE | self.pygame.NOFRAME

        self.clock = self.pygame.time.Clock()
        self.screen = None
        self.images = {}
        self.videos = {}
        self.audios = {}
        self.audio = {}
        self.video = {}

    def connect(self):
        try:
            self.pygame.init()
            self.pygame.display.init()
            # wait for display to be initialized
            while self.pygame.display.get_init() == 0:
                pass

            self.pygame.mixer.init()
            self.pygame.font.init()
            self.pygame.mouse.set_visible(False)
            self.font = self.pygame.font.SysFont("Arial", 20)
            self.screen = self.pygame.display.set_mode(tuple(self.display_config["window_size"]), flags=self.flags, display=self.display_config["port"], vsync=self.display_config["vsync"])
            self.screen.fill((0, 0, 0))
            self.pygame.display.update()

            self.out_queue.put("display_connected")

        except self.pygame.error as e:
            raise Warning(f"Could not connect to display device: {e}")
        except Exception as e:
            raise Warning(f"An unexpected error occurred: {e}")

    def load_media(self):
        try:
            media = self.stimulus_config["load_media"]["value"]
            if media["images"]:
                for key, val in media["images"].items():
                    self.images[key] = self.pygame.image.load(val)
            if media["audios"]:
                for key, val in media["audios"].items():
                    self.audios[key] = self.pygame.mixer.Sound(val)
            if media["videos"]:
                raise TypeError("Video loading not supported yet")
        except Exception as e:
            raise Exception(f"Cannot load media to display device. {e}")

    def play_audio(self, audio_name, loops=0, volume=1.0):
        self.pygame.mixer.stop()
        self.audios[audio_name].set_volume(volume)
        self.audios[audio_name].play(loops=loops)

    def stop_audio(self):
        self.pygame.mixer.stop()

    def _run(self):
        try:
            self.connect()
            self.load_media()
            self.display_process()
        except Exception as e:
            logging.error(f"An error occurred in the 'start' method: {e}")

    def display_process(self):
        init_method, update_method, draw_method = None, None, None
        while True:

            if update_method is None:
                init_method, update_method, draw_method = None, None, None
                (epoch, args) = self.in_queue.get(block=True, timeout=None)

                if epoch == "play_audio":
                    self.play_audio(args)
                else:
                    epoch_value = self.stimulus_config["task_epochs"]["value"][epoch]
                    if epoch_value["clear_queue"]:
                        # Re-defining clock here removes runaway effect
                        self.clock = self.pygame.time.Clock()
                    init_method = getattr(self, epoch_value["init_func"])
                    try:
                        init_method(args)
                    except:
                        raise Warning(f"Unable to process {init_method}")
                    if epoch_value["update_func"]:
                        update_method = getattr(self, epoch_value["update_func"])

            # if update is coming
            if update_method:
                if self.in_queue.empty():
                    try:
                        draw_method, draw_args = update_method(args)
                        if draw_method:
                            self.draw(draw_method, draw_args)
                        self.clock.tick_busy_loop(self.frame_rate)
                    except:
                        raise Warning(f"Unable to process {update_method}")
                else:
                    update_method = None

    def draw(self, func, args=None):
        try:
            func(args=args)
        except:
            raise Warning(f"Rendering error: Unable to process {func}")
        # print(f"FPS: {self.clock.get_fps()}")
        self.update()

    def update(self):
        self.pygame.display.update()
        self.pygame.event.pump()


if __name__ == "__main__":
    from multiprocessing import Queue


    path = "../NeuRPi/protocols/random_dot_motion/free_reward_training/"
    filename = "config.py"

    from protocols.random_dot_motion.free_reward_training import config

    in_queue = Queue()
    out_queue = Queue()
    display_window = Display(stimulus_configuration=config.STIMULUS, in_queue=in_queue, out_queue=out_queue)
