import time
import multiprocessing
import os
import numpy as np
from queue import Queue, Empty
import threading
from NeuRPi.prefs import prefs



class DisplayManager:

    def __init__(self, stimulus_config, in_queue=None, out_queue=None, epoch_update_event=None, stop_event=None):
        
        # initialize pygame
        import pygame
        
        self.pygame = pygame
        # When ssh, use display 'hostname:Display.ScreenNo'. In this case using localhost:0.0 or :0.0
        os.putenv('DISPLAY', ':0.0')


        self.display_config = prefs.get('HARDWARE')["Display"]
        self.stimulus_config = stimulus_config
        self.in_queue = in_queue
        self.out_queue = self.out_queue = out_queue or multiprocessing.Queue()
        self.epoch_update_event = epoch_update_event
        self.stop_event = stop_event

        self.flags = 0
        for flag in self.display_config["flags"]:
            self.flags |= getattr(self.pygame, flag)
        self.clock = None
        self.font = None
        self.screen = {}
        self.images = {}
        self.videos = {}
        self.audios = {}

        self.buffer_surf = None
        self.display_surf = None
        self.display_updated = threading.Event()
        self.display_ready = threading.Event()

        self.buffer_count = 3  # Number of buffers
        self.buffers = None
        self.display_queue = Queue(maxsize=self.buffer_count)
        self.buffer_index = 0

        self.lock = threading.Lock()
        self.frame_queue = Queue(maxsize=100)
        self.is_connected = False
        self.state = None

    def connect(self):
        try:
            self.pygame.init()  
            self.pygame.display.init()
            # wait for display to be initialized
            while not self.pygame.display.get_init():
                pass  
            # initialize other pygame modules
            self.pygame.mixer.init()
            self.pygame.font.init()
            self.pygame.mouse.set_visible(self.display_config["mouse_visible"])
            self.font = self.pygame.font.SysFont(self.display_config["font"][0],self.display_config["font"][1])
            self.clock = self.pygame.time.Clock()
            # Starting displays
            self.screen = self.pygame.display.set_mode(self.display_config["window_size"], flags=self.flags, display=self.display_config["port"], vsync=self.display_config["vsync"])
            self.screen.fill((0, 255, 255))
            self.pygame.display.update()

            self.display_surf = self.pygame.Surface(self.display_config["window_size"])
            self.buffer_surf = self.pygame.Surface(self.display_config["window_size"])

            self.buffers = [self.pygame.Surface(self.display_config["window_size"]) for _ in range(self.buffer_count)]
            
            
        except Exception as e:
            raise Exception(f"Cannot connect to provided display device. {e}")
        finally:
            self.is_connected = True
            self.out_queue.put(("display_connected", None))

    def load_media(self):
        try:
            media = self.stimulus_config.load_media.value
            if media.images:
                for key, val in media.images.items():
                    self.images[key] = self.pygame.image.load(val)
            if media.audios:
                for key, val in media.audios.items():
                    self.audios[key] = self.pygame.mixer.Sound(val)
            if media.videos:
                raise TypeError("Video loading not supported yet")
        except Exception:
            raise Exception(f"Cannot load media to display device.")
        
    def start(self):
        threading.Thread(target=self.run_display, daemon=True).start()
        self.update_display()


    def update_surfaces(self, method, args):
        if not self.display_queue.full():
            self.buffer_index = (self.buffer_index + 1) % self.buffer_count       
            method(args=args, surface=self.buffers[self.buffer_index])
            self.display_queue.put(self.buffers[self.buffer_index])

    def run_display(self):
        """
        Obeserve incoming queue for either of below three states:
        idle: System is idle and display is blank
        init_epoch: New epoch has been initialized
        update_epoch: Epoch is being updated
        """
        self.state = "idle"
        init_method, update_method = None, None
        epoch, args = None, None
        self.epoch_update_event.clear()
        self.display_updated.set()
        
        while self.is_connected:
            print(f"observed in {self.state} state")
            if self.state == "idle":
                self.epoch_update_event.wait()
                self.state = "init_epoch"

            elif self.state == "init_epoch":
                if not self.in_queue.empty():
                    init_method, update_method = None, None
                    (epoch, args) = self.in_queue.get_nowait()
                    self.epoch_update_event.clear() # received message so clear the event

                    epoch_value = getattr(self.stimulus_config.task_epochs.value, epoch)
                    init_method = epoch_value.init_func
                    update_method = epoch_value.update_func
                    method = getattr(self, init_method)

                    self.clear_queue(self.display_queue)
                    self.buffer_index = 0
                    method(args=args, surface=self.buffers[self.buffer_index])
                    self.display_queue.put(self.buffers[self.buffer_index])

                    if update_method:
                        self.state = "update_epoch"
                    else:
                        self.state = "idle"
            elif self.state == "update_epoch": 
                method = getattr(self, update_method)
                while not self.epoch_update_event.is_set():
                    self.update_surfaces(method, args)
            
            if self.epoch_update_event.is_set():
                self.state="init_epoch"
                self.clear_queue(self.frame_queue)
                self.epoch_update_event.clear()


    def update_display(self):
        while True:
            if not self.display_queue.empty():
                current_surface = self.display_queue.get()
                self.screen.blit(current_surface, (0,0))
                self.display_updated.set()
                self.pygame.display.flip()
                self.pygame.event.pump()
                self.clock.tick(self.display_config["max_fps"])
                print(f"FPS: {self.clock.get_fps()}")



    def clear_queue(self, q):
        try:
            while True:
                q.get_nowait()
        except Empty:
            pass

    def release(self):
        try:
            if self.is_connected:
                self.pygame.quit()
            self.is_connected = False
        except:
            raise Warning(f"Could not close connection with display device")
        
