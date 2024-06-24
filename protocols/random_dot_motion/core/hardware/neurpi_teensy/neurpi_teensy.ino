#define left_touch_pin 22
#define right_touch_pin 23
#define left_valve_pin 20
#define right_valve_pin 19

String msg;
int msg_int;
int threshold = 4;
int slope = 20;
bool left_valve_open = false;
bool right_valve_open = false;

byte lick;
int upper_limit = 15000;
int i=0; int j=0;
// Signal processing and filtering for lick sensor
int counter = 0;
int counter_L = 0;
int counter_R = 0;
int prev_L = 0;
int prev_R = 0;
// the average
const int numReadings = 10;
int readingsL[numReadings];      // the readings from the analog input
int readIndexL = 0;              // the index of the current reading
int totalL = 0;                  // the running total
int averageL = 0;
int readingsR[numReadings];      // the readings from the analog input
int readIndexR = 0;              // the index of the current reading
int totalR = 0;                  // the running total
int averageR = 0;



void setup() {
  // Reward arduino
  Serial1.begin(9600);
  // Lick
  Serial.begin(9600);
  Serial.setTimeout(50);

  // initialize pins
  pinMode(left_valve_pin, OUTPUT);
  digitalWrite(left_valve_pin, LOW);
  pinMode(right_valve_pin, OUTPUT);
  digitalWrite(right_valve_pin, LOW);

  for (int thisReading = 0; thisReading < numReadings; thisReading++) {
    readingsL[thisReading] = 0;
    readingsR[thisReading] = 0;
  }
}

void loop() {
  // see if there's incoming serial data:
  if (Serial.available() > 0) {

    // read incoming string from serial buffer
    msg_int = int(Serial.parseInt());
    msg = Serial.readString();

    Serial1.print(msg_int+msg);

//    // opening left valve for pulse_width msecs
//    if (msg=="reward_left"){
//      digitalWrite(left_valve_pin, HIGH);
//      delay(msg_int);
//      digitalWrite(left_valve_pin, LOW);
//    }
//    // opening right valve for pulse_width msecs
//    if (msg=="reward_right"){
//      digitalWrite(right_valve_pin, HIGH);
//      delay(msg_int);
//      digitalWrite(right_valve_pin, LOW);
//    }
//    // toggle right valve state
//    if (msg=="toggle_left_reward"){
//      if (left_valve_open){
//        digitalWrite(left_valve_pin, LOW);
//        left_valve_open = false;
//        }
//      else{
//        digitalWrite(left_valve_pin, HIGH);
//        left_valve_open = true;
//        }
//    }
//    // toggle right valve state
//    if (msg=="toggle_right_reward"){
//      if (right_valve_open){
//        digitalWrite(right_valve_pin, LOW);
//        right_valve_open = false;
//        }
//      else{
//        digitalWrite(right_valve_pin, HIGH);
//        right_valve_open = true;
//        }
//    }
//    // give `msg_int` pulses of 50ms to both spouts
//    if (msg=="calibrate_reward"){
//      digitalWrite(left_valve_pin, LOW);
//      digitalWrite(right_valve_pin, LOW);
//      for (counter=0; counter<=msg_int; counter++){
//          digitalWrite(left_valve_pin, HIGH);
//          delay(100);
//          digitalWrite(left_valve_pin, LOW);
//          delay(100);
//          digitalWrite(right_valve_pin, HIGH);
//          delay(100);
//          digitalWrite(right_valve_pin, LOW);
//        }
//    }

    // updating lick_threshold
    if (msg=="update_lick_threshold"){
        threshold = msg_int;
    }
    // updating lick_threshold
    if (msg=="update_lick_slope"){
        slope = msg_int;
    }

 }


//   **Alter Code for lick sensor**
  long left = touchRead(left_touch_pin);
  long right = touchRead(right_touch_pin);

  // moving average calculation for left lick
  if (left < upper_limit){
    totalL = totalL - readingsL[readIndexL];
    // read from the sensor:
    readingsL[readIndexL] = left;
    // add the reading to the total:
    totalL = totalL + readingsL[readIndexL];
    // advance to the next position in the array:
    readIndexL = readIndexL + 1;
    // if we're at the end of the array...
    if (readIndexL >= numReadings) {
      // ...wrap around to the beginning:
      readIndexL = 0;
    }
    // calculate the average:
    averageL = totalL / numReadings;
  }

  // moving average calculation for right lick
  if (right < upper_limit){
    totalR = totalR - readingsR[readIndexR];
    // read from the sensor:
    readingsR[readIndexR] = right;
    // add the reading to the total:
    totalR = totalR + readingsR[readIndexR];
    // advance to the next position in the array:
    readIndexR = readIndexR + 1;
    // if we're at the end of the array...
    if (readIndexR >= numReadings) {
      // ...wrap around to the beginning:
      readIndexR = 0;
    }
    // calculate the average:
    averageR = totalR / numReadings;

  }

if (counter>21){    // To avoid change in moving average for first 10 cycles
    if (averageL-prev_L > slope){
      counter_L = counter_L + 1;
      }

    if (averageL-prev_L < -slope){
      counter_L = 0;
      }

    if (averageR-prev_R > slope){
      counter_R = counter_R + 1;
      }

    if (averageR-prev_R < -slope){
      counter_R = 0;
      }
 }

  prev_L = averageL;
  prev_R = averageR;

    if (i==0 and (counter_L > threshold)){
        i = 1;
        lick=2;
        Serial.print(lick);      // send 2 when left lick starts (-3 in python = -1)
    }
    if (i==1 and (counter_L < threshold)){
        i=0;
        lick=1;
        Serial.print(lick);   // send 1 when left lick ends (-3 in python = -2)
    }

    if (j==0 and (counter_R > threshold)){
        j = 1;
        lick=4;
        Serial.print(lick);     // send 4 when right lick starts (-3 in python = 1)
    }
    if (j==1 and (counter_R < threshold)){
        j=0;
        lick=5;
        Serial.print(lick);   // send 5 when right lick ends (-3 in python = 2)
    }

  counter = counter+1;
 }
