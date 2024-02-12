#include "FS.h"
#include "SD.h"
#include "SPI.h"

// Define the pins
#define ledPin 13
// Touch related variables
#define leftTouchPin 4
#define rightTouchPin 5
// Encoder related variables
#define encoderPinA 2
#define encoderPinB 3
// UART 1
#define RXPin 14
#define TXPin 15
// SPI-interface for SD card 
#define SCK 36
#define MISO 37
#define MOSI 35
#define CS 34
String filename;
File file;

const int bufferSize = 1000;  // Adjust the buffer size as needed
String dataBuffer[bufferSize];
int bufferIndex = 0;
const int flushInterval = 10000;  // Flush every 10 iterations
int iterationsSinceLastFlush = 0;

int leftThreshold = 5;
int rightThreshold = 5;
int leftBaseline = 0;
int rightBaseline = 0;
int rescalingFactor = 1000;
volatile int leftTouchValue = 0;
volatile int rightTouchValue = 0;
bool leftTouched = false;
bool rightTouched = false;
int lick;

const float resolution = 90/1024.0; //
volatile int encoderPosCount = 0;
volatile float encoderPosDegree = 0;
int lastEncoded = 0;

#define RGB_BUILTIN 18
#define RGB_BRIGHTNESS 50
// general variables
int startTime;

HardwareSerial RewardSerial(1);

File createFile(fs::FS &fs, const char *filename) {
    // Create the file
    File newFile = fs.open("/" + String(filename) + ".csv", FILE_WRITE);
    if (!newFile) {
        // Serial.println("Failed to open file for writing");
        return File();  // Return an empty File object on failure
    }
    // newFile.close();
    return newFile;
}

void sendFileOverSerial(File &file) {
    // Serial.println("Sending file over serial:");
    if (file) {
      while (file.available()) {
        Serial.write(file.read());
      }
      file.close();
      Serial.println("\nFile sent successfully");
    } else {
      Serial.println("Error opening file for reading");
    }
}

void sendMessage(int startTime, String msg) {
  unsigned long currentTime = millis();
  unsigned long elapsedTime = currentTime - startTime;
  String msgString = String(elapsedTime) + "\t" + msg;
  Serial.println(msgString);
}

void writeData() {
    unsigned long currentTime = millis();
    unsigned long elapsedTime = currentTime - startTime;
    String data = String(elapsedTime) + "," + String(leftTouchValue) + "," + String(rightTouchValue) + "," +
                  String(leftTouched) + "," + String(rightTouched) + "," +
                  String(encoderPosDegree);

    if (bufferIndex < bufferSize) {
        dataBuffer[bufferIndex++] = data;
    } 
    else {
        for (int i = 0; i < bufferSize; i++) {
            file.println(dataBuffer[i]);
        }
        file.flush();  // Flush the data to ensure it's written to the file
        bufferIndex = 0;  // Reset the buffer index
    }
    if (++iterationsSinceLastFlush >= flushInterval) {
        file.flush();
        iterationsSinceLastFlush = 0;
    }
}

void resetTouchSensor(){
  int totalLeft = 0;
  int totalRight = 0;
  for (int i = 0; i<50; i++){
    totalLeft+=touchRead(leftTouchPin);
    totalRight+=touchRead(rightTouchPin);
    delay(1);
  }
  leftBaseline = totalLeft/50;
  rightBaseline = totalRight/50;
}
  
void updateLicks(){
//void updateLicks(int startTime){
  leftTouchValue = touchRead(leftTouchPin) - leftBaseline;
  rightTouchValue = touchRead(rightTouchPin) - rightBaseline;
  leftTouchValue = constrain(leftTouchValue/rescalingFactor, 0, 100);
  rightTouchValue = constrain(rightTouchValue/rescalingFactor, 0, 100);  
  
  if ((leftTouchValue > leftThreshold) && !(leftTouched)){
    leftTouched = true;
    sendMessage(startTime,"-1");
    neopixelWrite(RGB_BUILTIN, 0, RGB_BRIGHTNESS, 0);
  }
  else if ((leftTouchValue < leftThreshold) && (leftTouched)){
    leftTouched = false;
    sendMessage(startTime,"-2");
    neopixelWrite(RGB_BUILTIN, 0, 0, 0);
  }
  if ((rightTouchValue > rightThreshold) && !(rightTouched)){
    rightTouched = true;
    sendMessage(startTime,"1");
    neopixelWrite(RGB_BUILTIN, 0, 0, RGB_BRIGHTNESS);
  }
  else if ((rightTouchValue < rightThreshold) && (rightTouched)){
    rightTouched = false;
    sendMessage(startTime,"2");
    neopixelWrite(RGB_BUILTIN, 0, 0, 0);
  }
}

void updateEncoder() {
  int MSB = digitalRead(encoderPinA); // MSB = most significant bit
  int LSB = digitalRead(encoderPinB); // LSB = least significant bit

  int encoded = (MSB << 1) | LSB; // Converting the 2 pin value to single number
  int sum  = (lastEncoded << 2) | encoded; // Adding it to the previous encoded value

  if(sum == 0b1101 || sum == 0b0100 || sum == 0b0010 || sum == 0b1011) encoderPosCount++;
  if(sum == 0b1110 || sum == 0b0111 || sum == 0b0001 || sum == 0b1000) encoderPosCount--;
  
  encoderPosDegree = static_cast<float>(encoderPosCount) * resolution;

  lastEncoded = encoded; // Store this value for next time
}



void setup() {
  Serial.begin(115200);
  Serial.setTimeout(100);
  // Reward arduino
  RewardSerial.begin(115200, SERIAL_8N1, RXPin, TXPin);
  while (!Serial){delay(10);}
  while (!RewardSerial){delay(10);}
  // Starting session timer
  startTime = millis();
  
  // Set touch sensor pins as input
  pinMode(leftTouchPin, INPUT);
  pinMode(rightTouchPin, INPUT);
  resetTouchSensor();

  // Set encoder pins as input with pull-up resistors
  pinMode(encoderPinA, INPUT_PULLUP); 
  pinMode(encoderPinB, INPUT_PULLUP);
  // Attach interrupts to the encoder pins
  attachInterrupt(digitalPinToInterrupt(encoderPinA), updateEncoder, CHANGE);
  attachInterrupt(digitalPinToInterrupt(encoderPinB), updateEncoder, CHANGE);
  
  SPI.begin(SCK, MISO, MOSI, CS);
  if(!SD.begin()){
      // Serial.println("Card Mount Failed");
      return;
  }
}

void loop() {
  checkMessage(); 
  updateLicks();
  updateEncoder();
  writeData();
  delay(1);

}

void checkMessage(){
  if (Serial.available() > 0){
    int msgInt = int(Serial.parseInt());
    String msg = Serial.readStringUntil('\n'); // read until new line character
    RewardSerial.print(msgInt + msg);

    if (msg=="start_session"){
      startTime = millis();
      resetTouchSensor();
      encoderPosCount = 0;    
      sendMessage(startTime, "clock_started");
      filename = Serial.readStringUntil('\n'); // read until new line character
      if (filename.length() > 0) {
      file = createFile(SD, filename.c_str());
      Serial.print("file created: ");
      Serial.println(filename.c_str());
      } else{
      file = createFile(SD, "test");
      Serial.print("file created: ");
      Serial.println("test");
      }
    }
    else if (msg == "reset_licks"){
      resetTouchSensor();
    }    
    else if (msg == "reset_wheel"){
      encoderPosCount = 0;
    }
    else if (msg == "update_lick_threshold_left)"){
      leftThreshold = msgInt;
      sendMessage(startTime, "left_threshold_modified");
    }
    else if (msg == "update_lick_threshold_right)"){
      rightThreshold = msgInt;
      sendMessage(startTime, "right_threshold_modified");
    }
    else if (msg == "end_session"){
      file.flush();
      sendFileOverSerial(file);
      file.close();
    }
  }
}