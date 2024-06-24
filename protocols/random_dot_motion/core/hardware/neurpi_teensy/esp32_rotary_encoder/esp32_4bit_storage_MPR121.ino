#include "FS.h"
#include "SD_MMC.h"
#include <MPR121.h>

MPR121 mpr121;

#define ONE_BIT_MODE false
File DataFile; // File on microSD card, to store waveform data

boolean isLogging = false; // If currently logging position and time to microSD memory
uint32_t dataPos = 0;
uint32_t dataMax = 4294967295; // Maximim number of positions that can be logged (limited by 32-bit counter)
unsigned long currentTime = 0;

// microSD variables
uint32_t nRemainderBytes = 0;
uint32_t nFullBufferReads = 0;
union DataUnion {
  byte uint8[10];  // Adjust the size based on the total bytes in your data format
  struct {
    uint32_t elapsedTime;
    uint8_t leftTouchAnalog;
    uint8_t rightTouchAnalog;
    int8_t lickState;
    int16_t encoderPosDegree;
    int8_t photodiodeState;
  } data;
};

// DataUnion sdWriteBuffer;
const int maxBufferSize = 228976 / (3 * sizeof(DataUnion)); // 1/3th the available heap memory
#define BUFFER_SIZE maxBufferSize
DataUnion sdWriteBuffer[BUFFER_SIZE];
uint32_t bufferCounter = 0;

const uint32_t sdReadBufferSize = 2048; // in bytes
uint8_t sdReadBuffer[sdReadBufferSize] = {0};


// Define the pins
#define ledPin 13
#define leftTouchPin 10
#define rightTouchPin 11
#define encoderPinA 25
#define encoderPinB 26

int32_t leftThreshold = 40;
int32_t rightThreshold = 40;
int32_t leftBaseline = 0;
int32_t rightBaseline = 0;
int rescalingFactor = 1; //000;
volatile int leftTouchValue = 0;
volatile int rightTouchValue = 0;
uint8_t leftTouchAnalog;
uint8_t rightTouchAnalog;
bool leftTouched = false;
bool rightTouched = false;
int8_t lickState;

const float resolution = 90 / 1024.0;
volatile int encoderPosCount = 0;
volatile uint32_t encoderPosDegree = 0;
int lastEncoded = 0;

int8_t photodiodeState = 0;

// general variables
int startTime;

HardwareSerial RewardSerial(2);

void setup(){
  Serial.begin(115200);
  Serial.setTimeout(100);
  // Reward Arduino
  RewardSerial.begin(115200);
  while (!Serial) { delay(10); }
  while (!RewardSerial) { delay(10); }
  mpr121_begin();

  // Starting session timer
  startTime = millis();

  // // Set touch sensor pins as input
  // pinMode(leftTouchPin, INPUT);
  // pinMode(rightTouchPin, INPUT);
  resetTouchSensor();
  // Set encoder pins as input with pull-up resistors
  pinMode(encoderPinA, INPUT_PULLUP);
  pinMode(encoderPinB, INPUT_PULLUP);
  // Attach interrupts to the encoder pins
  attachInterrupt(digitalPinToInterrupt(encoderPinA), updateEncoder, CHANGE);
  attachInterrupt(digitalPinToInterrupt(encoderPinB), updateEncoder, CHANGE);

  // Initialized SD card for MMS
  pinMode(2, INPUT_PULLUP);
  // pinMode(4, INPUT_PULLUP);
  // pinMode(12, INPUT_PULLUP);
  // pinMode(13, INPUT_PULLUP);
  // pinMode(15, INPUT_PULLUP);
  if(!SD_MMC.begin("/sdcard", ONE_BIT_MODE)){
      Serial.println("Card_Mount_Failed");
      return;
  }
}


void mpr121_begin(){
  mpr121.setupSingleDevice(*&Wire, MPR121::ADDRESS_5A, true);
  mpr121.setAllChannelsThresholds(40, 20);
  mpr121.setDebounce(MPR121::ADDRESS_5A, 10, 10);
  mpr121.setBaselineTracking(MPR121::ADDRESS_5A, MPR121::BASELINE_TRACKING_INIT_10BIT);
  mpr121.setChargeDischargeCurrent(MPR121::ADDRESS_5A, 63);
  mpr121.setChargeDischargeTime(MPR121::ADDRESS_5A, MPR121::CHARGE_DISCHARGE_TIME_HALF_US);
  mpr121.setFirstFilterIterations(MPR121::ADDRESS_5A, MPR121::FIRST_FILTER_ITERATIONS_34);
  mpr121.setSecondFilterIterations(MPR121::ADDRESS_5A, MPR121::SECOND_FILTER_ITERATIONS_10);
  mpr121.setSamplePeriod(MPR121::ADDRESS_5A, MPR121::SAMPLE_PERIOD_1MS);
  mpr121.startAllChannels(MPR121::ADDRESS_5A, MPR121::COMBINE_CHANNELS_0_TO_11);
  // mpr121.setChannelThresholds(uint8_t channel, uint8_t touch_threshold, uint8_t release_threshold)
}

void startSession(int msgInt){
  startTime = millis();
  resetTouchSensor();
  encoderPosCount = 0;
  photodiodeState = 0;

  String filename;
  filename = Serial.readStringUntil('\n');  // read until new line character
  if (filename.length() == 0){
    filename = "Data";
  }
  filename = "/" + filename + ".dat";
  const char* filename_cstr = filename.c_str(); // Convert to const char*

  DataFile = SD_MMC.open(filename_cstr, FILE_WRITE);
  if(!DataFile){
      Serial.println("Failed_to_open_file_for_writing");
      return;
  }

  isLogging = true;
  currentTime = micros();
  DataFile.seek(0);
  dataPos = 0;
  sendMessage(startTime, "session_started");
}

void logCurrentData(){
  unsigned long currentTime = millis();
  unsigned long elapsedTime = currentTime - startTime;
  sdWriteBuffer[bufferCounter].data.elapsedTime = elapsedTime;
  sdWriteBuffer[bufferCounter].data.leftTouchAnalog = leftTouchAnalog;
  sdWriteBuffer[bufferCounter].data.rightTouchAnalog = rightTouchAnalog;
  sdWriteBuffer[bufferCounter].data.lickState = lickState;
  sdWriteBuffer[bufferCounter].data.encoderPosDegree = encoderPosDegree;
  sdWriteBuffer[bufferCounter].data.photodiodeState = photodiodeState;
  bufferCounter++;
  if (bufferCounter == BUFFER_SIZE) {
      // Write sdWriteBuffer to file
      DataFile.write((byte*)sdWriteBuffer, sizeof(sdWriteBuffer));
      dataPos += bufferCounter;
      bufferCounter = 0;
  }
}

void endSession(int logNeeded){
  logCurrentData();
  isLogging = false;
  DataFile.flush();

  // if data is requested send it via serial
  if (logNeeded == 1){
    if (DataFile) {
      // Read and print each line of the file
      while (DataFile.available()) {
        Serial.write(DataFile.read());
      }
    }

  dataPos = 0;
  DataFile.close();
  Serial.println("\nsession_successfully_ended");
}
}

void sendMessage(int startTime, String msg) {
  unsigned long elapsedTime = millis() - startTime;
  Serial.print(elapsedTime);
  Serial.print("\t");
  Serial.println(msg);
}

void resetTouchSensor(){
  mpr121_begin();
}

void updateLicks(){
  leftTouchAnalog = mpr121.getChannelFilteredData(leftTouchPin) - mpr121.getChannelBaselineData(leftTouchPin);
  rightTouchAnalog = mpr121.getChannelFilteredData(rightTouchPin) - mpr121.getChannelBaselineData(rightTouchPin);

  if ((leftTouchAnalog > leftThreshold) && !(leftTouched)) {
    leftTouched = true;
    lickState = -1;
    sendMessage(startTime, "-1");
  } else if ((leftTouchAnalog < leftThreshold) && (leftTouched)) {
    leftTouched = false;
    lickState = -2;
    sendMessage(startTime, "-2");
  }
  if ((rightTouchAnalog > rightThreshold) && !(rightTouched)) {
    rightTouched = true;
    lickState = 1;
    sendMessage(startTime, "1");
  } else if ((rightTouchAnalog < rightThreshold) && (rightTouched)) {
    rightTouched = false;
    lickState = 2;
    sendMessage(startTime, "2");
  }
}

void updateLickThreshold(int channel, int threshold){
  mpr121.setChannelThresholds(channel, threshold, threshold);
  mpr121.stopAllChannels();
  mpr121.startAllChannels(MPR121::ADDRESS_5A, MPR121::COMBINE_CHANNELS_0_TO_11);
}
// void resetTouchSensor() {
//   int totalLeft = 0;
//   int totalRight = 0;
//   for (int i = 0; i < 50; i++) {
//     totalLeft += touchRead(leftTouchPin);
//     totalRight += touchRead(rightTouchPin);
//     delay(1);
//   }
//   leftBaseline = totalLeft / 50;
//   rightBaseline = totalRight / 50;
// }

// void updateLicks() {
//   // // leftTouchValue = touchRead(leftTouchPin) - leftBaseline;
//   // // rightTouchValue = touchRead(rightTouchPin) - rightBaseline;
//   // leftTouchValue = leftBaseline - touchRead(leftTouchPin); //touchRead(leftTouchPin) - leftBaseline;
//   // rightTouchValue = rightBaseline - touchRead(rightTouchPin); //touchRead(rightTouchPin) - rightBaseline;
//   // leftTouchAnalog = constrain(leftTouchValue / rescalingFactor, 0, 100);
//   // rightTouchAnalog = constrain(rightTouchValue / rescalingFactor, 0, 100);

//   // if ((leftTouchAnalog > leftThreshold) && !(leftTouched)) {
//   //   leftTouched = true;
//   //   lickState = -1;
//   //   sendMessage(startTime, "-1");
//   // } else if ((leftTouchAnalog < leftThreshold) && (leftTouched)) {
//   //   leftTouched = false;
//   //   lickState = -2;
//   //   sendMessage(startTime, "-2");
//   // }
//   // if ((rightTouchAnalog > rightThreshold) && !(rightTouched)) {
//   //   rightTouched = true;
//   //   lickState = 1;
//   //   sendMessage(startTime, "1");
//   // } else if ((rightTouchAnalog < rightThreshold) && (rightTouched)) {
//   //   rightTouched = false;
//   //   lickState = 2;
//   //   sendMessage(startTime, "2");
//   // }
// }

void updateEncoder() {
  int MSB = digitalRead(encoderPinA);  // MSB = most significant bit
  int LSB = digitalRead(encoderPinB);  // LSB = least significant bit
  int encoded = (MSB << 1) | LSB;          // Converting the 2 pin value to single number
  int sum = (lastEncoded << 2) | encoded;  // Adding it to the previous encoded value
  if (sum == 0b1101 || sum == 0b0100 || sum == 0b0010 || sum == 0b1011) encoderPosCount++;
  if (sum == 0b1110 || sum == 0b0111 || sum == 0b0001 || sum == 0b1000) encoderPosCount--;
  encoderPosDegree = static_cast<int16_t>(encoderPosCount * resolution);
  lastEncoded = encoded;  // Store this value for next time
}

void updatePhotodiode(){}

void loop() {
  checkMessage();
  updateLicks();
  updateEncoder();
  updatePhotodiode();
  if (isLogging){
      logCurrentData();
  }
  delay(1);
}

void checkMessage(){
  if (Serial.available() > 0) {
    int msgInt = int(Serial.parseInt());
    String msg = Serial.readStringUntil('\n');  // read until new line character
    RewardSerial.println(msgInt + msg);

    if (msg == "start_session") {
      startSession(msgInt);
    } else if (msg == "reset_licks") {
      resetTouchSensor();
    } else if (msg == "reset_wheel") {
      encoderPosCount = 0;
    } else if (msg == "update_lick_threshold_left") {
      leftThreshold = msgInt;
    //   updateLickThreshold(leftTouchPin, msgInt);
      sendMessage(startTime, "left_threshold_modified");
    } else if (msg == "update_lick_threshold_right") {
      rightThreshold = msgInt;
    //   updateLickThreshold(rightTouchPin, msgInt);
      sendMessage(startTime, "right_threshold_modified");
    } else if (msg == "end_session") {
      endSession(msgInt);
    }
  }
}
