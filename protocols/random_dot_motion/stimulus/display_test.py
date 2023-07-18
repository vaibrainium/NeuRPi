
class PygameTest():
    def __init__(self, window_size=(1920, 1080)):
        import pygame
        import os
        self.pygame = pygame
        self.window_size = window_size
        os.environ["DISPLAY"] = ":0.0"
        self.screen = {}
        self.clock = self.pygame.time.Clock()

    def start(self, flags):
        self.pygame.init()
        self.pygame.mouse.set_visible(False)
        self.screen[0] = self.pygame.display.set_mode(
            self.window_size,
            flags = flags,
            display=0,
            vsync=True
        )

    def update(self):
        self.pygame.display.update()
        self.clock.tick(60)

if __name__=="__main__":
    import timeit
    import os

    os.environ["DISPLAY"] = ":0.0"
    window_size = (1280, 720)
    # window_size = (1920, 1080)
    
    test = PygameTest(window_size)
    flags = test.pygame.FULLSCREEN | test.pygame.DOUBLEBUF# | test.pygame.SCALED
    test.start(flags=flags)

    num_frames = 300
    elapsed_time = timeit.timeit(lambda: test.update(), number=num_frames)
    print(f"Elapsed time: {elapsed_time}")
    print(f"Mean frame time: {elapsed_time/num_frames}")
    

