import os
import threading
import time
from queue import Queue as thread_queue
import asyncio

import hydra
from omegaconf import DictConfig, OmegaConf
from NeuRPi.prefs import prefs
import logging


class Display:
    """
    Show Stimulus based on incoming messages.

    """

    def __init__(self, stimulus_configuration=None, stimulus_courier=None):
        super(Display, self).__init__()
        import pygame

        # When ssh, use display 'hostname:Display.ScreenNo'. In this case using localhost:0.0 or :0.0
        os.environ["DISPLAY"] = ":0.0"
        os.environ["PYGAME_BLEND_ALPHA_SDL2"] = "1"
        os.environ["ENABLE_ARM_NEON"] = "1"

        self.in_queue = stimulus_courier
        self.message = {}

        self.lock = threading.Lock()
        self.render_block = threading.Event()
        self.render_block.clear()
        self.epoch_update_event = threading.Event()
        self.epoch_update_event.clear()
        self.frame_queue_size = 1000
        self.frame_queue = thread_queue(maxsize=self.frame_queue_size)

        self.display_config = prefs.get('HARDWARE')["Display"]
        self.stimulus_config = stimulus_configuration
        self.courier_map = self.stimulus_config.courier_handle

        self.pygame = pygame

        self.frame_rate = self.display_config["max_fps"] #self.stimulus_config.display.frame_rate
        self.flags = 0
        for flag in self.display_config["flags"]:
            self.flags |= getattr(self.pygame, flag)

        self.font = None
        self.screen = None #{}
        self.images = {}
        self.videos = {}
        self.audios = {}
        self.clock = self.pygame.time.Clock()
        self.state = None
        
    def connect(self):
        try:
            # self.pygame.init()
            self.pygame.display.init()
            # wait for display to be initialized
            while self.pygame.display.get_init() == 0:
                pass

            self.pygame.mixer.init()
            self.pygame.font.init()
            self.pygame.mouse.set_visible(False)
            self.font = self.pygame.font.SysFont("Arial", 20)
            self.screen = self.pygame.display.set_mode(
                tuple(self.display_config["window_size"]),
                flags=self.flags,
                display=self.display_config["port"], 
                vsync=self.display_config["vsync"]
            )
            self.screen.fill((0, 0, 0))
            self.pygame.display.update()

        except self.pygame.error as e:
            raise Warning(f"Could not connect to display device: {e}")
        except Exception as e:
            raise Warning(f"An unexpected error occurred: {e}")
        finally:
            pass

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

    def start(self):
        try:
            self.connect()
            self.load_media()

            threading.Thread(target=self.render_visual, args=[], daemon=False).start()
            threading.Thread(target=self.in_queue_manager, args=[], daemon=False).start()
        except Exception as e:
            logging.error(f"An error occurred in the 'start' method: {e}")


    def in_queue_manager(self):
        self.state = "idle"
        init_method, update_method = None, None
        epoch, args = None, None

        while True:
            if not self.in_queue.empty():
                (epoch, args) = self.in_queue.get()
                epoch_value = self.stimulus_config["task_epochs"]["value"][epoch]
                self.epoch_update_event.clear()
                self.render_block.wait()
                if epoch_value["clear_queue"]:
                    self.frame_queue.queue.clear()

                init_method = getattr(self, epoch_value["init_func"])
                try:
                    init_method(args)
                except:
                    raise Warning(f"Unable to process {init_method}")
                if epoch_value["update_func"]:
                    update_method = getattr(self, epoch_value["update_func"])
        

                    # filling the queue before rendering starts
                    self.lock.acquire()
                    if epoch_value["clear_queue"]==False:
                        while not self.frame_queue.full():
                            try:
                                draw_func, args = update_method(args)
                                self.frame_queue.put([draw_func, args])
                            except:
                                raise Warning(f"Unable to process {update_method}")
                    self.lock.release()

                    self.epoch_update_event.set()
                else:
                    update_method = None

            if update_method:
                if not self.frame_queue.full():
                    try:
                        self.lock.acquire()
                        draw_func, args = update_method(args)
                        self.frame_queue.put([draw_func, args])
                        self.lock.release()
                    except:
                        raise Warning(f"Unable to process {update_method}")


    def render_visual(self):
        self.render_block.set()
        while True:
            self.epoch_update_event.wait()
            if not self.frame_queue.empty():
                try:
                    self.render_block.clear()
                    (func, args) = self.frame_queue.get()
                    self.lock.acquire()
                    # start = time.time()
                    self.draw(func, args)
                    # end = time.time()
                    self.lock.release()
                    self.render_block.set()
                    self.clock.tick_busy_loop(self.frame_rate)
                    # print(f"Render Time: {end-start}")
                except Exception as e:
                    raise Warning(f"Unable to process {func} {e}")

    def draw(self, func, args):
        try:
            func(args=args)
        except:
            logging.warning(f"Rendering error: Unable to process {func}")

        if self.stimulus_config["display"]["show_fps"]:
            fps = self.font.render(
                str(int(self.clock.get_fps())), 1, self.pygame.Color("coral")
            )
            self.screen.blit(fps, (1900, 1000))
        # logging.info(f"FPS: {self.clock.get_fps()}")
        print(f"FPS: {self.clock.get_fps()}")
        self.update()

    def update(self):
        self.pygame.display.flip()
        # self.pygame.display.update()
        self.pygame.event.pump()


if __name__ == "__main__":
    from multiprocessing import Queue

    import hydra

    path = "../../random_dot_motion/config"
    filename = "free_reward_training.yaml"
    hydra.initialize(version_base=None, config_path=path)
    config = hydra.compose(filename, overrides=[])
    courier = Queue()
    display_window = Display(stimulus_configuration=config, stimulus_courier=courier)
