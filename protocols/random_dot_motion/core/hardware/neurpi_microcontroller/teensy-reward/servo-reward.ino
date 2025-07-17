#include <Servo.h>

Servo servo;  // create servo object to control a servo

// Position definitions
const int LEFT = 0;
const int CENTER = 45;
const int RIGHT = 90;

// Pin definitions
const int servo_pin = 4;
const int led = 13;
const int left_led = 3;
const int right_led = 5;
const int center_led = 6;

// Speed setting (milliseconds per degree)
float servoSpeed = 0.1;

// Track current servo position
int currentPosition = CENTER;

// Input strings and parsed values
String input;
String command;
int value = 0;

// States
bool left_led_on = false, right_led_on = false, center_led_on = false;
bool reward_active = false;

// Manual control flags
bool left_led_manual = false, right_led_manual = false, center_led_manual = false;

// Flash timers and durations
unsigned long left_led_start = 0, right_led_start = 0, center_led_start = 0;
unsigned long left_led_duration = 0, right_led_duration = 0, center_led_duration = 0;

// Reward state tracking
unsigned long reward_start = 0;
unsigned long reward_duration = 0;
int reward_target_position = CENTER;
bool reward_at_target = false;

void setup() {
  Serial.begin(115200);
  Serial1.begin(115200);
  Serial1.setTimeout(50);

  servo.attach(servo_pin);
  pinMode(led, OUTPUT);
  pinMode(left_led, OUTPUT);
  pinMode(right_led, OUTPUT);
  pinMode(center_led, OUTPUT);

  // Initialize servo to center position
  servo.write(CENTER);
  currentPosition = CENTER;

  // Ensure everything is off initially
  digitalWrite(led, LOW);
  digitalWrite(left_led, LOW);
  digitalWrite(right_led, LOW);
  digitalWrite(center_led, LOW);
}

// Function to move servo to target position gradually
void moveToPosition(int targetPosition) {
  if (currentPosition != targetPosition) {
    // Move servo gradually to target position
    if (currentPosition < targetPosition) {
      currentPosition++;
    } else {
      currentPosition--;
    }
    servo.write(currentPosition);
    delay((int)servoSpeed);  // Wait based on speed setting
  }
}

void toggleOutput(bool &state, int pin) {
  state = !state;
  digitalWrite(pin, state ? HIGH : LOW);
}

void handleMessage() {
  int commaIdx = input.indexOf(',');
  if (commaIdx == -1) {
    Serial1.println("ERROR: Invalid command format, missing comma");
    return;
  }

  command = input.substring(0, commaIdx);
  command.trim();
  command.toLowerCase();  // Normalize command case

  String valueStr = input.substring(commaIdx + 1);
  valueStr.trim();
  value = valueStr.toInt();

  if (valueStr.length() == 0 || (!isDigit(valueStr[0]) && value != 0)) {
    Serial1.print("ERROR: Invalid duration value: '");
    Serial1.print(valueStr);
    Serial1.println("'");
    return;
  }

  unsigned long now = millis();

  if (command == "flash_led_left") {
    digitalWrite(left_led, HIGH);
    left_led_on = true;
    left_led_start = now;
    left_led_duration = value;
    left_led_manual = false;
  } else if (command == "flash_led_center") {
    digitalWrite(center_led, HIGH);
    center_led_on = true;
    center_led_start = now;
    center_led_duration = value;
    center_led_manual = false;
  } else if (command == "flash_led_right") {
    digitalWrite(right_led, HIGH);
    right_led_on = true;
    right_led_start = now;
    right_led_duration = value;
    right_led_manual = false;
  } else if (command == "toggle_led_left") {
    toggleOutput(left_led_on, left_led);
    left_led_manual = true;
  } else if (command == "toggle_led_center") {
    toggleOutput(center_led_on, center_led);
    center_led_manual = true;
  } else if (command == "toggle_led_right") {
    toggleOutput(right_led_on, right_led);
    right_led_manual = true;
  } else if (command == "reward_left") {
    reward_target_position = LEFT;
    reward_active = true;
    reward_at_target = false;
    reward_duration = value;
    digitalWrite(led, HIGH);
  } else if (command == "reward_right") {
    reward_target_position = RIGHT;
    reward_active = true;
    reward_at_target = false;
    reward_duration = value;
    digitalWrite(led, HIGH);
  } else {
    Serial1.print("ERROR: Unknown command '");
    Serial1.print(command);
    Serial1.println("'");
  }
}

void loop() {
  if (Serial1.available()) {
    input = Serial1.readStringUntil('\n');
    input.trim();
    handleMessage();
  }

  unsigned long now = millis();

  // Handle servo reward movement
  if (reward_active) {
    if (!reward_at_target) {
      // Move towards target position
      moveToPosition(reward_target_position);

      // Check if we've reached the target
      if (currentPosition == reward_target_position) {
        reward_at_target = true;
        reward_start = now;  // Start timing at target position
      }
    } else {
      // We're at target position, check if duration has elapsed
      if (now - reward_start >= reward_duration) {
        // Time to return to center
        if (currentPosition != CENTER) {
          moveToPosition(CENTER);
        } else {
          // We're back at center, reward complete
          reward_active = false;
          digitalWrite(led, LOW);
        }
      }
    }
  }

  // Handle LED timers
  if (!left_led_manual && left_led_on && (now - left_led_start >= left_led_duration)) {
    digitalWrite(left_led, LOW);
    left_led_on = false;
  }

  if (!right_led_manual && right_led_on && (now - right_led_start >= right_led_duration)) {
    digitalWrite(right_led, LOW);
    right_led_on = false;
  }

  if (!center_led_manual && center_led_on && (now - center_led_start >= center_led_duration)) {
    digitalWrite(center_led, LOW);
    center_led_on = false;
  }
}
