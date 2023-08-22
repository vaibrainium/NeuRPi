import os
os.putenv('DISPLAY', ':0.0')

import pygame
from pygame.locals import *
from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GL.shaders import *

import math
import random

# Initialize Pygame
pygame.init()

# Constants
WIDTH, HEIGHT = 1920, 1080
FPS = 60
NUM_DOTS = 100

# Colors
WHITE = (1, 1, 1)

# Initialize Pygame display
screen = pygame.display.set_mode((WIDTH, HEIGHT), DOUBLEBUF | OPENGL | FULLSCREEN | NOFRAME | SCALED, vsync=1)
pygame.display.set_caption("OpenGL Multiple Dots Renderer")

# Set up OpenGL
glClearColor(0, 0, 0, 0)

# Vertex shader source code
vertex_shader = """
#version 330 core
layout(location = 0) in vec2 in_position;
layout(location = 1) in vec3 in_color;
out vec3 color;
void main()
{
    gl_Position = vec4(in_position, 0.0, 1.0);
    color = in_color;
}
"""

# Fragment shader source code
fragment_shader = """
#version 330 core
in vec3 color;
out vec4 FragColor;
void main()
{
    FragColor = vec4(color, 1.0);
}
"""

# Compile shaders and create shader program
shader_program = compileProgram(compileShader(vertex_shader, GL_VERTEX_SHADER),
                                compileShader(fragment_shader, GL_FRAGMENT_SHADER))

# Generate VBO (vertex buffer object) and VAO (vertex array object)
vbo = glGenBuffers(1)
vao = glGenVertexArrays(1)

# Initialize dot parameters
dots = []
for _ in range(NUM_DOTS):
    dot_x, dot_y = random.uniform(0, WIDTH), random.uniform(0, HEIGHT)
    dot_speed = random.uniform(1, 5)
    dot_color = (random.uniform(0, 1), random.uniform(0, 1), random.uniform(0, 1))
    dots.append([dot_x, dot_y, dot_color])

# Bind VAO and VBO
glBindVertexArray(vao)
glBindBuffer(GL_ARRAY_BUFFER, vbo)

# Upload data to VBO
data = []
for dot in dots:
    data.extend(dot)
glBufferData(GL_ARRAY_BUFFER, len(data) * 4, (GLfloat * len(data))(*data), GL_STATIC_DRAW)

# Specify attribute pointers
glEnableVertexAttribArray(0)
glVertexAttribPointer(0, 2, GL_FLOAT, GL_FALSE, 20, ctypes.c_void_p(0))
glEnableVertexAttribArray(1)
glVertexAttribPointer(1, 3, GL_FLOAT, GL_FALSE, 20, ctypes.c_void_p(8))

# Use shader program
glUseProgram(shader_program)

clock = pygame.time.Clock()

running = True
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    # Clear the screen
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

    # Update dot positions
    for dot in dots:
        dot[0] += dot_speed
        if dot[0] > WIDTH:
            dot[0] = 0

    # Bind VAO and draw
    glBindVertexArray(vao)
    glDrawArrays(GL_POINTS, 0, NUM_DOTS)

    # Swap the buffers
    pygame.display.flip()

    # Cap the frame rate
    clock.tick(FPS)
    print(f"FPS: {clock.get_fps()}")

# Clean up
glDeleteBuffers(1, [vbo])
glDeleteVertexArrays(1, [vao])
glDeleteProgram(shader_program)
pygame.quit()
