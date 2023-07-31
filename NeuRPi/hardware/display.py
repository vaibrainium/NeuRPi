import time

import pygame
import serial
import os
from NeuRPi.hardware.hardware import Hardware


class Display(Hardware):
    """
    Class for Display        

    """
    pygame = pygame
    pygame.init()
    pygame.mixer.init()
    pygame.font.init()
    pygame.mouse.set_visible(False)
    

    def __init__(
        self, name=None, port=0, refresh_rate=60, window_size=[1920,1080], flags=['FULLSCREEN', 'DOUBLEBUF', 'HWSURFACE', 'SCALED', 'HWACCEL'], vsync=True, font='Arial', group="Display"):
        super(Display, self).__init__()
        
        # When ssh, use display 'hostname:Display.ScreenNo'. In this case using localhost:0.0 or :0.0
        
        self.name = name if name else port
        self.group = group
        self.port = port
        self.window_size = window_size
        self.refresh_rate = 100# refresh_rate
        self.vsync = vsync
        self.font = Display.pygame.font.SysFont(font, 50)
        self.flags = 0
        for flag in flags:
            self.flags |= getattr(Display.pygame, flag)
        self.clock = Display.pygame.time.Clock()    
        
        self.connection = None

    def connect(self):
        """
        Connect to serial hardware at given port with given baudrate and timeout
        """
        try:           
            self.screen = Display.pygame.display.set_mode(self.window_size, flags=self.flags, display=self.port, vsync=self.vsync).convert()
            # wait for screen to be initialized
            while not self.pygame.display.get_init():
                pass
            # initialize screen with black background
            self.screen.fill((0, 0, 0))
            self.is_connected = True
        except:
            raise Exception(
                f"Cannot connect to provided {self.group} device: {self.name} (at '{self.port}')"
            )

    def release(self):
        """
        If connection is already established, release the hardware
        """
        try:
            self.connection.close()
            self.is_connected = False
        except:
            raise Warning(
                f"Could not close connection with {self.group} device: {self.name} (at '{self.port}')"
            )

    def render_display(self, idx=0):
        """
        Render display with given stimulus
        """
        if idx == 0:
            self.screen.fill((0, 0, 0))
        # elif idx == 1:
        #     self.screen.fill((255, 255, 255))
        fps = self.font.render(
            str(int(self.clock.get_fps())), 1, Display.pygame.Color("coral")
        )
        print(self.clock.get_fps())
        self.screen.blit(fps, (1000, 1000))
        Display.pygame.display.update()
        self.clock.tick(self.refresh_rate)


if __name__ == "__main__":
    import os
    
    os.environ["DISPLAY"] = ":0.0"
    a = Display()
    a.connect()

    while True:
        a.render_display(0)
        # a.render_display(1)


