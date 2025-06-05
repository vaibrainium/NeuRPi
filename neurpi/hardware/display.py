# import time
# import multiprocessing
# import pygame
# import serial
# import os
# import numpy as np
# from neurpi.hardware.hardware import Hardware


# class Display(Hardware):
#     """
#     A class representing a display hardware.

#     This class handles the initialization, connection, rendering, and release of the display hardware.

#     Attributes:
#         name (str): The name of the display.
#         group (str): The group of the display hardware.
#         port (int): The connection port of the display.
#         window_size (list): The size of the display window.
#         max_refresh_rate (int): The maximum refresh rate of the display.
#         vsync (bool): The vertical synchronization of the display.
#         font (pygame.font.Font): The font used for rendering text on the display.
#         flags (int): The flags used for initializing the display.
#         clock (pygame.time.Clock): The pygame clock used for timing the display refresh rate.
#         connection: The connection object for the display hardware.
#         is_connected (bool): A boolean indicating whether the display is connected or not.
#     """
#     import pygame
#     os.environ["DISPLAY"] = ":0"
#     pygame = pygame
#     pygame.display.init()
#     pygame.mixer.init()
#     pygame.font.init()
#     pygame.mouse.set_visible(False)

#     @classmethod
#     def load_media(cls):
#         """
#         Load media from session_config file
#         """
#         pass

#     @classmethod
#     def update_display(cls):
#         """
#         Updates the display.
#         """
#         cls.pygame.event.pump()
#         cls.pygame.display.update()

#     def __init__(
#         self, name=None, port=0, max_refresh_rate=100, window_size=[1920,1080], flags=['FULLSCREEN', 'DOUBLEBUF', 'HWSURFACE', 'SCALED', 'HWACCEL'], vsync=True, font=['Arial',20], group="Display"
#     ):
#         super(Display, self).__init__()
#         """
#         Initializes a Display object.

#         Args:
#             name (str, optional): The name of the display. Defaults to None.
#             port (int, optional): The connection port of the display. Defaults to 0.
#             max_refresh_rate (int, optional): The maximum refresh rate of the display. Defaults to 100.
#             window_size (list, optional): The size of the display window. Defaults to [1920, 1080].
#             flags (list, optional): The flags used for initializing the display. Defaults to ['FULLSCREEN', 'DOUBLEBUF', 'HWSURFACE', 'SCALED', 'HWACCEL'].
#             vsync (bool, optional): The vertical synchronization of the display. Defaults to True.
#             font (str, optional): The font used for rendering text on the display. Defaults to 'Arial'.
#             group (str, optional): The group of the display hardware. Defaults to "Display".
#         """
#         super(Display, self).__init__()

#         # pygame variables
#         self.name = name if name else port
#         self.group = group
#         self.port = port
#         self.window_size = window_size
#         self.max_refresh_rate = max_refresh_rate
#         self.vsync = vsync
#         self.font = Display.pygame.font.SysFont(font[0], font[1])
#         self.flags = 0
#         for flag in flags:
#             self.flags |= getattr(Display.pygame, flag)
#         self.screen = None
#         self.default_screen = None

#         # support variables
#         self.frame_queue = multiprocessing.Queue()
#         self.stop_event = multiprocessing.Event()
#         self.clock = Display.pygame.time.Clock()
#         self.connection = None
#         self.is_connected = False

#     def connect(self):
#         """
#         Connects to the display hardware.
#         Raises:
#             Exception: If the connection to the display hardware fails.
#         """
#         try:
#             self.screen = Display.pygame.display.set_mode(
#                 self.window_size, flags=self.flags, display=self.port, vsync=self.vsync
#             )#.convert()
#             # wait for screen to be initialized
#             while not self.pygame.display.get_init():
#                 pass
#             # initialize screen with black background
#             self.is_connected = True
#         except Exception:
#             raise Exception(
#                 f"Cannot connect to provided {self.group} device: {self.name} (at '{self.port}')"
#             )

#     def run_display(self):#, frame_queue, stop_event):

#         # create default screen
#         self.screen.fill((0, 0, 0))
#         self.default_screen = Display.pygame.surfarray.array3d(self.screen)

#         while self.is_connected and not self.stop_event.is_set():
#             if not self.frame_queue.empty():
#                 frame = frame_queue.get()
#                 self.update_screen(frame)
#             else:
#                 # Render a black screen if no frame is available
#                 self.update_screen()

#         # self.release()


#     def update_screen(self, frame=None):
#         """
#         Shows a frame on the display.

#         Args:
#             frame (numpy.ndarray): The frame to be shown on the display.
#         """
#         if frame:
#             print('Entered update_screen with frame')
#             # Convert the frame (e.g., a NumPy array) to a Pygame surface
#             frame_surface = pygame.surfarray.make_surface(frame)
#             self.screen.blit(frame_surface, (0, 0))
#         else:
#             # print('Entered update_screen without frame')
#             self.screen.fill((255, 255, 255))

#         # fps = self.font.render(
#         #     str(int(self.clock.get_fps())), 1, Display.pygame.Color("coral")
#         # )
#         # print(self.clock.get_fps())
#         # self.screen.blit(fps, (1000, 1000))

#         # Print time between two frames
#         print(self.clock.get_fps())
#         # Update the display
#         Display.pygame.display.update()
#         Display.pygame.event.pump()
#         self.clock.tick(self.max_refresh_rate)

#     def release(self):
#         """
#         Releases the connection to the display hardware.

#         Raises:
#             Warning: If the connection with the display hardware cannot be closed.
#         """
#         try:
#             if self.is_connected:
#                 pygame.quit()
#             self.is_connected = False
#         except:
#             raise Warning(
#                 f"Could not close connection with {self.group} device: {self.name} (at '{self.port}')"
#             )


# def test_func():
#     a = Display()
#     a.connect()
#     a.run_display()

# if __name__ == "__main__":
#     import threading

#     stop_event = threading.Event()
#     try:
#         multiprocessing.Process(target=test_func, daemon=True).start()
#         stop_event.wait()
#     except KeyboardInterrupt:
#         pass

#     # a = Display()
#     # a.connect()

#     # # Create a multiprocessing Queue to pass frames between processes
#     # frame_queue = multiprocessing.Queue()#a.frame_queue
#     # # Create a stop event to signal when to stop the display process
#     # stop_event = multiprocessing.Event()
#     # # Create a separate process for the Pygame display
#     # display_process = multiprocessing.Process(target=a.run_display, args=(frame_queue, stop_event))


#     try:
#         # Start the Pygame display process
#         # This one still flickers
#         # display_process.start()

#         # # Below works without flickering
#         # a.run_display(frame_queue, stop_event)

#         # Main loop for other tasks
#         while True:
#             pass

#     except KeyboardInterrupt:
#         # Terminate the Pygame display process gracefully
#         a.release()
#         display_process.join()
