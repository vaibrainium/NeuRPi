// compile with:
// g++ -shared -o protocols/random_dot_motion/core/stimulus/cpp_approach/libdrawcircle.so protocols/random_dot_motion/core/stimulus/cpp_approach/drawcircle.cpp -fPIC -lsfml-graphics -lsfml-window -lsfml-system

#include <SFML/Graphics.hpp>
// #include <SFML/Graphics/Text.hpp>
#include <vector> // Include the vector library
#include <iostream>

// Create a global SFML RenderWindow
sf::RenderWindow window;

// Declare sf::Text object for displaying FPS
sf::Text fpsText;
sf::Font font; // Declare a font object

// Create a clock for FPS calculation
sf::Clock frameClock;
sf::Clock fpsClock;
int frameCount = 0;
int currentFPS = 0;

extern "C" {

int init(int width, int height, int maxFPS, bool fullscreen, const char* title) {
    setenv("DISPLAY", ":0.0", 1); // Set the DISPLAY environment variable

    sf::VideoMode videoMode;
    if (fullscreen) {
        // Get the first available fullscreen mode
        videoMode = sf::VideoMode::getFullscreenModes()[0];
    } else {
        videoMode = sf::VideoMode(width, height);
    }

    window.create(videoMode, title, fullscreen ? sf::Style::Fullscreen : sf::Style::Default);
    window.setVerticalSyncEnabled(true); // Enable VSync
    window.setFramerateLimit(maxFPS); // Set the maximum framerate
    window.setMouseCursorVisible(false); // Hide the mouse cursor

    // Use a system font (Helvetica)
    if (!font.loadFromFile("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf")) {
        std::cerr << "Failed to load system font." << std::endl;
        return 1;
    }
    fpsText.setFont(font);
    fpsText.setCharacterSize(24);
    fpsText.setFillColor(sf::Color::White);
    fpsText.setPosition(10, 10);

    return 0;
}


// Draw a circle on the SFML window
void drawCircle(float x, float y, float radius, unsigned char r, unsigned char g, unsigned char b) {
    sf::CircleShape circle(radius);
    circle.setPosition(x - radius, y - radius);
    circle.setFillColor(sf::Color(r, g, b));
    window.draw(circle);
}

// Modify the drawCircle function to accept lists of coordinates
void drawCircles(const std::vector<float>& xList, const std::vector<float>& yList, float radius, unsigned char r, unsigned char g, unsigned char b) {
    for (size_t i = 0; i < xList.size() && i < yList.size(); ++i) {
        drawCircle(xList[i], yList[i], radius, r, g, b);
    }
}

// Display the SFML window
int update() {
    window.display();

    // Calculate FPS
    frameCount++;
    if (fpsClock.getElapsedTime().asSeconds() >= 1.0) {
        currentFPS = frameCount;
        frameCount = 0;
        fpsClock.restart();
    }

    // Update the FPS text content
    fpsText.setString("FPS: " + std::to_string(currentFPS));
    // Draw the FPS text
    window.draw(fpsText);

    return currentFPS; // Return current FPS
}

void fill_screen(unsigned char r, unsigned char g, unsigned char b) {
    window.clear(sf::Color(r, g, b));
}

// Handle SFML events (e.g., window close)
int handleEvents() {
    sf::Event event;
    while (window.pollEvent(event)) {
        if (event.type == sf::Event::Closed) {
            window.close();
            return 1;
        }
    }
    return 0;
}

} // extern "C"
