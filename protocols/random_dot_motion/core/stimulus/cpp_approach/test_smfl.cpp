#include <SFML/Graphics.hpp>
#include <SFML/System.hpp>
#include <random>
#include <vector>
#include <ctime>
#include <iostream>

class Dot {
public:
    float x, y;
    float radius;
    sf::Color color;

    Dot(float _x, float _y, float _radius, sf::Color _color) : x(_x), y(_y), radius(_radius), color(_color) {}
};

int main() {
    if (setenv("DISPLAY", ":0.0", 1) != 0) {
        std::cerr << "Failed to set the DISPLAY environment variable." << std::endl;
        return 1;
    }

    sf::RenderWindow window(sf::VideoMode(1920, 1080), "Random Dot Motion");

    // Enable VSync
    window.setVerticalSyncEnabled(true);

    std::srand(static_cast<unsigned int>(std::time(nullptr)));

    std::vector<Dot> dots;

    for (int i = 0; i < 1000; ++i) {
        float x = static_cast<float>(std::rand() % 1920);
        float y = static_cast<float>(std::rand() % 1080);
        float radius = 17.0f;
        sf::Color color = sf::Color(255, 255, 255);
        dots.emplace_back(x, y, radius, color);
    }

    sf::Clock clock;

    sf::Font font;
    // Use a system font (Helvetica)
    if (!font.loadFromFile("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf")) {
        std::cerr << "Failed to load system font." << std::endl;
        return 1;
    }

    sf::Text fpsText;
    fpsText.setFont(font);
    fpsText.setCharacterSize(24);
    fpsText.setFillColor(sf::Color::White);
    fpsText.setPosition(10, 10);

    int frameCount = 0;
    float fpsTimer = 0.0f;

    while (window.isOpen()) {
        sf::Event event;
        while (window.pollEvent(event)) {
            if (event.type == sf::Event::Closed)
                window.close();
        }

        float deltaTime = clock.restart().asSeconds();
        for (Dot& dot : dots) {
            float dx = static_cast<float>(std::rand() % 11) - 5.0f;
            float dy = static_cast<float>(std::rand() % 11) - 5.0f;
            dot.x += dx;
            dot.y += dy;

            if (dot.x < 0) dot.x += 1920;
            if (dot.x >= 1920) dot.x -= 1920;
            if (dot.y < 0) dot.y += 1080;
            if (dot.y >= 1080) dot.y -= 1080;
        }

        window.clear(sf::Color::Black);

        for (const Dot& dot : dots) {
            sf::CircleShape circle(dot.radius);
            circle.setPosition(dot.x - dot.radius, dot.y - dot.radius);
            circle.setFillColor(dot.color);
            window.draw(circle);
        }

        window.draw(fpsText);

        window.display();

        frameCount++;
        fpsTimer += deltaTime;

        if (fpsTimer >= 1.0f) {
            float fps = static_cast<float>(frameCount) / fpsTimer;
            fpsText.setString("FPS: " + std::to_string(static_cast<int>(fps)));
            frameCount = 0;
            fpsTimer = 0.0f;
        }
    }

    return 0;
}



// install SFML
// sudo apt-get install libsfml-dev
// to run the program
// g++ test.cpp -o test -lsfml-graphics -lsfml-window -lsfml-system
// ./test
