import time

import numpy as np
import sdl2
import sdl2.ext
import sdl2.sdlgfx as sdl2gfx


def draw_circle(renderer):
    # Clear the renderer with a dark color
    renderer.clear(sdl2.ext.Color(0, 0, 0))
    # Draw a circle
    center_x = int(np.random.random() * 1920)
    center_y = int(np.random.random() * 1080)
    radius = 100
    color = sdl2.ext.Color(255, 0, 0)  # Red color
    sdl2gfx.filledCircleRGBA(renderer.sdlrenderer, center_x, center_y, radius, color.r, color.g, color.b, color.a)


def main_loop(window, renderer):
    running = True
    frame_count = 0
    start_time = time.time()

    while running:
        for event in sdl2.ext.get_events():
            if event.type == sdl2.SDL_QUIT:
                running = False
                break

        # Clear the renderer
        renderer.clear()

        # Render your graphics here
        draw_circle(renderer)

        # Update the renderer
        renderer.present()

        # Increment frame count
        frame_count += 1

        # Calculate elapsed time and print frame rate every second
        elapsed_time = time.time() - start_time
        if elapsed_time >= 1.0:
            frame_rate = frame_count / elapsed_time
            print(f"Frame rate: {frame_rate:.2f} FPS")
            frame_count = 0
            start_time = time.time()

    # Quit PySDL2
    sdl2.ext.quit()

if __name__ == "__main__":
    sdl2.ext.init()
    window = sdl2.ext.Window("PySDL2 Window", size=(1920, 1080), flags=sdl2.SDL_WINDOW_FULLSCREEN)
    window.show()
    renderer_flags = sdl2.SDL_RENDERER_ACCELERATED | sdl2.SDL_RENDERER_PRESENTVSYNC
    renderer = sdl2.ext.Renderer(window, flags=renderer_flags)
    main_loop(window, renderer)
