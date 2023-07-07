
# def update():

#     screen.blit(circle_surface, (0, 0))
#     pygame.display.update()
#     pygame.event.pump()
    
#     # print(clock.tick(60))


# def update_globally():
#     # Clear the display
#     circle_surface.fill((0, 0, 0))

#     pygame.draw.circle(
#         circle_surface,
#         (255, 25, 250),
#         (1920 * np.random.random(), 1080 * np.random.random()),
#         150,
#     )
#     # Draw the circle surface onto the display

#     # fps = font.render(
#     #             str(int(clock.get_fps())), 1, pygame.Color("coral")
#     # )
#     # circle_surface.blit(fps, (1900, 1000))

#     # screen.blit(circle_surface, (0,0))
#     # Update the display
#     # pygame.display.flip()
#     pygame.display.update()
#     # clock.tick(60)


# if __name__ == "__main__":
#     import os
#     import timeit

#     import numpy as np
#     import pygame

#     os.environ["DISPLAY"] = ":0.0"
#     # os.environ['SDL_VIDEODRIVER'] = 'fbcon'
#     os.environ['SDL_VIDEO_X11_NET_WM_BYPASS_COMPOSITOR'] = '0'

#     # Initialize Pygame
#     pygame.init()
#     # font = pygame.font.SysFont("Arial", 20)
#     flags = (
#         pygame.FULLSCREEN
#         | pygame.DOUBLEBUF
#         # | pygame.NOFRAME
#         # | pygame.HWSURFACE
#         # | pygame.NOEVENT
#         | pygame.SCALED
#     )
#     screen = pygame.display.set_mode((1920, 1080), flags=flags, vsync=1, display=0)

#     clock = pygame.time.Clock()

#     # Create a surface to store the circle
#     # circle_surface = pygame.Surface((circle_radius * 2, circle_radius * 2), pygame.SRCALPHA)
#     circle_surface = pygame.Surface((1920, 1080), pygame.SRCALPHA)
#     circle_surface.fill((0, 0, 0))
#     pygame.draw.circle(
#         circle_surface,
#         (255, 25, 250),
#         (1920 * np.random.random(), 1080 * np.random.random()),
#         1000,
#     )

#     # while True:
#     #     # Update the display
#     #     # update_globally()
#     #     update()
#     #     # # Limit the framerate
#     #     # print(clock.get_fps())

#     elapsed_time = timeit.timeit(lambda: update(), number=100)
#     # elapsed_time = timeit.timeit(lambda: update_globally(), number=100)
#     print(f"Elapsed time: {elapsed_time}")
