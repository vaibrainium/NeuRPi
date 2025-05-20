#define left_valve_pin 6
#define right_valve_pin 7
#define led 13
#define left_led 3
#define right_led 4
#define center_led 5


String msg;
int msg_int;
int counter;
bool left_valve_open = false;
bool right_valve_open = false;


void setup() {
  Serial.begin(115200);
  Serial1.begin(115200);
  Serial1.setTimeout(100);
  // initialize pins
  pinMode(left_valve_pin, OUTPUT);
  digitalWrite(left_valve_pin, LOW);
  pinMode(right_valve_pin, OUTPUT);
  digitalWrite(right_valve_pin, LOW);
  pinMode(led, OUTPUT);
  digitalWrite(led, LOW);
}

void loop() {
  // see if there's incoming serial data:
  if (Serial1.available() > 0) {
    // read incoming string from serial buffer
    msg_int = Serial1.parseInt();
    msg = Serial1.readString();
    msg = msg.trim();
    Serial.println(msg_int);
    Serial.println(msg);

    // opening left valve for pulse_width msecs
    if (msg=="reward_left"){
      digitalWrite(left_valve_pin, HIGH);
      digitalWrite(led, HIGH);
      delay(msg_int);
      digitalWrite(left_valve_pin, LOW);
      digitalWrite(led, LOW);
    }
    // opening right valve for pulse_width msecs
    if (msg=="reward_right"){
      digitalWrite(right_valve_pin, HIGH);
      digitalWrite(led, HIGH);
      delay(msg_int);
      digitalWrite(right_valve_pin, LOW);
      digitalWrite(led, LOW);
    }
    // toggle right valve state
    if (msg=="toggle_left_reward"){
      if (left_valve_open){
        digitalWrite(left_valve_pin, LOW);
        digitalWrite(led, LOW);
        left_valve_open = false;
        }
      else{
        digitalWrite(left_valve_pin, HIGH);
        digitalWrite(led, HIGH);
        left_valve_open = true;
        }
    }
    // toggle right valve state
    if (msg=="toggle_right_reward"){
      if (right_valve_open){
        digitalWrite(right_valve_pin, LOW);
        digitalWrite(led, LOW);
        right_valve_open = false;
        }
      else{
        digitalWrite(right_valve_pin, HIGH);
        digitalWrite(led, HIGH);
        right_valve_open = true;
        }
    }
    // give `msg_int` pulses of 50ms to both spouts
    if (msg=="caliberate_reward"){
      digitalWrite(left_valve_pin, LOW);
      digitalWrite(right_valve_pin, LOW);
      digitalWrite(led, LOW);
      for (counter=0; counter<=msg_int; counter++){
          digitalWrite(left_valve_pin, HIGH);
          digitalWrite(led, HIGH);
          delay(100);
          digitalWrite(left_valve_pin, LOW);
          digitalWrite(led, LOW);
          delay(100);
          digitalWrite(right_valve_pin, HIGH);
          digitalWrite(led, HIGH);
          delay(100);
          digitalWrite(right_valve_pin, LOW);
          digitalWrite(led, LOW);
        }
    }

	if (msg=="flash_left_led"){
	  digitalWrite(left_led, HIGH);
	  delay(msg_int);
	  digitalWrite(left_led, LOW);
	}
	if (msg=="flash_right_led"){
	  digitalWrite(right_led, HIGH);
	  delay(msg_int);
	  digitalWrite(right_led, LOW);
	}
	if (msg=="flash_center_led"){
	  digitalWrite(center_led, HIGH);
	  delay(msg_int);
	  digitalWrite(center_led, LOW);
	}
  }
}
