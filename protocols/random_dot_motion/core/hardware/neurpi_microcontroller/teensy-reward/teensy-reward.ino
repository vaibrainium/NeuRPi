// Pin definitions
const int left_valve_pin = 6;
const int right_valve_pin = 7;
const int led = 13;
const int left_led = 3;
const int right_led = 4;
const int center_led = 5;

// Input strings and parsed values
String input;
String command;
int value = 0;

// States
bool left_valve_on = false;
bool right_valve_on = false;
bool left_led_on = false;
bool right_led_on = false;
bool center_led_on = false;

// Flash timers and durations
unsigned long left_valve_start = 0;
unsigned long right_valve_start = 0;
unsigned long left_led_start = 0;
unsigned long right_led_start = 0;
unsigned long center_led_start = 0;

unsigned long left_valve_duration = 0;
unsigned long right_valve_duration = 0;
unsigned long left_led_duration = 0;
unsigned long right_led_duration = 0;
unsigned long center_led_duration = 0;

void setup() {
  Serial.begin(115200);
  Serial1.begin(115200);
  Serial1.setTimeout(50);

  pinMode(left_valve_pin, OUTPUT);
  pinMode(right_valve_pin, OUTPUT);
  pinMode(led, OUTPUT);
  pinMode(left_led, OUTPUT);
  pinMode(right_led, OUTPUT);
  pinMode(center_led, OUTPUT);

  // Ensure everything is off initially
  digitalWrite(left_valve_pin, LOW);
  digitalWrite(right_valve_pin, LOW);
  digitalWrite(led, LOW);
  digitalWrite(left_led, LOW);
  digitalWrite(right_led, LOW);
  digitalWrite(center_led, LOW);
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

  // Parse duration value safely
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
  } else if (command == "flash_led_center") {
    digitalWrite(center_led, HIGH);
    center_led_on = true;
    center_led_start = now;
    center_led_duration = value;
  } else if (command == "flash_led_right") {
    digitalWrite(right_led, HIGH);
    right_led_on = true;
    right_led_start = now;
    right_led_duration = value;
  } else if (command == "toggle_led_left") {
    toggleOutput(left_led_on, left_led);
  } else if (command == "toggle_led_center") {
    toggleOutput(center_led_on, center_led);
  } else if (command == "toggle_led_right") {
    toggleOutput(right_led_on, right_led);
  } else if (command == "reward_left") {
    digitalWrite(left_valve_pin, HIGH);
    digitalWrite(led, HIGH);
    left_valve_on = true;
    left_valve_start = now;
    left_valve_duration = value;
  } else if (command == "reward_right") {
    digitalWrite(right_valve_pin, HIGH);
    digitalWrite(led, HIGH);
    right_valve_on = true;
    right_valve_start = now;
    right_valve_duration = value;
  } else if (command == "toggle_reward_left") {
    toggleOutput(left_valve_on, left_valve_pin);
    digitalWrite(led, left_valve_on ? HIGH : LOW);
  } else if (command == "toggle_reward_right") {
    toggleOutput(right_valve_on, right_valve_pin);
    digitalWrite(led, right_valve_on ? HIGH : LOW);
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

  // Handle auto-off for flash commands
  if (left_valve_on && (now - left_valve_start >= left_valve_duration)) {
    digitalWrite(left_valve_pin, LOW);
    digitalWrite(led, LOW);
    left_valve_on = false;
  }

  if (right_valve_on && (now - right_valve_start >= right_valve_duration)) {
    digitalWrite(right_valve_pin, LOW);
    digitalWrite(led, LOW);
    right_valve_on = false;
  }

  if (left_led_on && (now - left_led_start >= left_led_duration)) {
    digitalWrite(left_led, LOW);
    left_led_on = false;
  }

  if (right_led_on && (now - right_led_start >= right_led_duration)) {
    digitalWrite(right_led, LOW);
    right_led_on = false;
  }

  if (center_led_on && (now - center_led_start >= center_led_duration)) {
    digitalWrite(center_led, LOW);
    center_led_on = false;
  }
}
