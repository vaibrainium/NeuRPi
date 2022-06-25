import pygame
from queue import Queue, Empty


class Display():
    """
    Base class for video stimulus display. Defines display properties.
    """
    def __init__(self, configuration = None):
        """
        Inputs configuration file
        """
        self.config = configuration


    def _start(self):
        pygame.init()
        pygame.mixer.init()
        clock = pygame.time.Clock()

    def _end(self):
        pygame.quit()
