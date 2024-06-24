import ctypes
import os
import time
import numpy as np
import pygame

from protocols.random_dot_motion.core.stimulus.random_dot_motion import RandomDotMotion


os.environ["DISPLAY"] = ":0.0"
# Load the C++ shared library
so_path = "protocols/random_dot_motion/core/stimulus/cpp_approach/libdrawcircle.so"
window = ctypes.CDLL(so_path)

# Initialize the SFML window
window_x = 1920
window_y = 1080

window.init(window_x, window_y, 60, 1, b"My Window", 1)


def draw_circle(x, y, radius, r, g, b):
    window.fill_screen(ctypes.c_ubyte(0), ctypes.c_ubyte(0), ctypes.c_ubyte(0))
    window.drawCircle(ctypes.c_float(x), ctypes.c_float(y), ctypes.c_float(radius), ctypes.c_ubyte(r), ctypes.c_ubyte(g), ctypes.c_ubyte(b))


def draw_circles(x, y, radius, r, g, b):
    window.fill_screen(ctypes.c_ubyte(0), ctypes.c_ubyte(0), ctypes.c_ubyte(0))
    # # Convert Python lists to C arrays
    # x_array = (ctypes.c_float * len(x))(*x)
    # y_array = (ctypes.c_float * len(y))(*y)
    # # Call the C++ function
    # window.drawCircles(x_array, y_array, ctypes.c_float(radius), ctypes.c_ubyte(r), ctypes.c_ubyte(g), ctypes.c_ubyte(b))
    for i in range(len(x)):
        window.drawCircle(ctypes.c_float(x[i]), ctypes.c_float(y[i]), ctypes.c_float(radius), ctypes.c_ubyte(r), ctypes.c_ubyte(g), ctypes.c_ubyte(b))


frame = 0


rdk = RandomDotMotion(stimulus_size=(window_x, window_y))
rdk.new_stimulus(
    {
        "coherence": 90,
        "seed": 1,
        "dot_vel": 400,
        "dot_fill": 15,
        "dot_radius": 17,
        "dot_color": (255, 255, 255),
        "dot_lifetime": 30,
    }
)

fps = 60
while True:
    # Handle SFML events (e.g., window close)
    if window.handleEvents():
        break

    # move dots
    try:
        rdk.move_dots(fps)
    except:
        rdk.move_dots(60)
    # Draw multiple circles
    draw_circles(rdk.x, rdk.y, rdk.radius, 255, 255, 255)

    # Display the SFML window
    fps = window.update()
