#include "FS.h"
#include "SPI.h"
#include <SdFat.h>

SdFs SDcard;
FsFile DataFile; // File on microSD card, to store waveform data
bool ready = false; // Indicates if SD is busy (for use with SDBusy() funciton)

const int SPI_SPEED = 30000000;
SPISettings DACSettings(SPI_SPEED, MSBFIRST, SPI_MODE0); // Settings for DAC

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
const int maxBufferSize = 228976 / (3 * sizeof(DataUnion)); // 1/4th the available heap memory
#define BUFFER_SIZE maxBufferSize
DataUnion sdWriteBuffer[BUFFER_SIZE];
uint32_t bufferCounter = 0;

const uint32_t sdReadBufferSize = 2048; // in bytes
uint8_t sdReadBuffer[sdReadBufferSize] = {0};

// Define the pins
#define ledPin 13
#define leftTouchPin 4
#define rightTouchPin 5
#define encoderPinA 2
#define encoderPinB 3
#define RXPin 14
#define TXPin 15
#define SCK 36
#define MISO 37
#define MOSI 35
#define DAC_CS_Pin 34

int32_t leftThreshold = 10;
int32_t rightThreshold = 10;
int32_t leftBaseline = 0;
int32_t rightBaseline = 0;
int rescalingFactor = 1000;
volatile int leftTouchValue = 0;
volatile int rightTouchValue = 0;
uint8_t leftTouchAnalog;
uint8_t rightTouchAnalog;
bool leftTouched = false;
bool rightTouched = false;
int8_t lickState;

const float resolution = 90 / 1024.0;  //
volatile int encoderPosCount = 0;
volatile uint32_t encoderPosDegree = 0;
int lastEncoded = 0;

int8_t photodiodeState = 0;  


// general variables
#define RGB_BUILTIN 18
#define RGB_BRIGHTNESS 50
int startTime;

HardwareSerial RewardSerial(1);

void setup(){
  Serial.begin(115200);
  Serial.setTimeout(100);
  // Reward arduino
  RewardSerial.begin(115200, SERIAL_8N1, RXPin, TXPin);
  while (!Serial) { delay(10); }
  while (!RewardSerial) { delay(10); }
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

  SPI.begin(SCK, MISO, MOSI, DAC_CS_Pin);  
  if (!SDcard.begin(DAC_CS_Pin, SPI_SPEED)) {
    Serial.println("SD card initialization failed!");
    while (1);
  }
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
  filename = String(filename + ".dat");
  SDcard.remove(filename);
  DataFile = SDcard.open(filename, O_RDWR | O_CREAT);
  
  if (!DataFile.isOpen()) {
    Serial.println("Error opening dat file");
    return;
  }

  // SDcard.remove("Data.wfm");
  // DataFile = SDcard.open("Data.wfm", O_RDWR | O_CREAT);
  // if (!DataFile.isOpen()) {
  //   Serial.println("Error opening Data.wfm file");
  //   return;
  // }
  DataFile.preAllocate(104857600);
  while (sdBusy()) {}
  DataFile.seek(0);
  dataPos = 0;
  currentTime = micros();
  isLogging = true;

  sendMessage(startTime, "Session Started");
}

void startLogging() {
  DataFile.seek(0);
  dataPos = 0;
  currentTime = micros();
  isLogging = true;
}

void logCurrentData(){
    unsigned long currentTime = millis();
    unsigned long elapsedTime = currentTime - startTime;
    // Fill sdWriteBuffer with your data
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
        // DataFile.flush();
        dataPos += bufferCounter;
        bufferCounter = 0;
    }
}

void endSession(int logNeeded){
  logCurrentData();
  isLogging = false;
  
  DataFile.flush();
  if (DataFile.size() > dataPos * sizeof(DataUnion)) {
    DataFile.truncate(dataPos * sizeof(DataUnion));
  }

  if (logNeeded == 1){
    // Calculate the number of full buffer reads
    nFullBufferReads = (dataPos * 8 > sdReadBufferSize) ? static_cast<unsigned long>(floor(static_cast<double>(dataPos) * 8 / static_cast<double>(sdReadBufferSize))) : 0;
    // Write dataPos as a 32-bit unsigned integer using Serial
    Serial.write(reinterpret_cast<byte*>(&dataPos), sizeof(dataPos));
    // Perform full buffer reads
    for (int i = 0; i < nFullBufferReads; i++) {
      DataFile.read(sdReadBuffer, sdReadBufferSize);
      Serial.write(sdReadBuffer, sdReadBufferSize);
    }
    // Calculate the number of remaining bytes
    nRemainderBytes = (dataPos * 8) - (nFullBufferReads * sdReadBufferSize);
    // Perform read and write if there are remaining bytes
    if (nRemainderBytes > 0) {
      DataFile.read(sdReadBuffer, nRemainderBytes);
      Serial.write(sdReadBuffer, nRemainderBytes);
    }
  }

  // Reset dataPos
  dataPos = 0;
  DataFile.close();

  Serial.println("\nSession successfully ended");
}


void returnLoggedData(){
  DataFile.flush();
  if (DataFile.size() > dataPos * sizeof(DataUnion)) {
    DataFile.truncate(dataPos * sizeof(DataUnion));
  }

  // Calculate the number of full buffer reads
  nFullBufferReads = (dataPos * 8 > sdReadBufferSize) ? static_cast<unsigned long>(floor(static_cast<double>(dataPos) * 8 / static_cast<double>(sdReadBufferSize))) : 0;

  // Write dataPos as a 32-bit unsigned integer using Serial
  Serial.write(reinterpret_cast<byte*>(&dataPos), sizeof(dataPos));

  // Perform full buffer reads
  for (int i = 0; i < nFullBufferReads; i++) {
    DataFile.read(sdReadBuffer, sdReadBufferSize);
    Serial.write(sdReadBuffer, sdReadBufferSize);
  }

  // Calculate the number of remaining bytes
  nRemainderBytes = (dataPos * 8) - (nFullBufferReads * sdReadBufferSize);

  // Perform read and write if there are remaining bytes
  if (nRemainderBytes > 0) {
    DataFile.read(sdReadBuffer, nRemainderBytes);
    Serial.write(sdReadBuffer, nRemainderBytes);
  }

  // Reset dataPos
  dataPos = 0;
  DataFile.close();

  // SPI.endTransaction();
}



void sendMessage(int startTime, String msg) {
  unsigned long currentTime = millis();
  unsigned long elapsedTime = currentTime - startTime;
  String msgString = String(elapsedTime) + "\t" + msg;
  Serial.println(msgString);
}

void resetTouchSensor() {
  int totalLeft = 0;
  int totalRight = 0;
  for (int i = 0; i < 50; i++) {
    totalLeft += touchRead(leftTouchPin);
    totalRight += touchRead(rightTouchPin);
    delay(1);
  }
  leftBaseline = totalLeft / 50;
  rightBaseline = totalRight / 50;
}

void updateLicks() {
  leftTouchValue = touchRead(leftTouchPin) - leftBaseline;
  rightTouchValue = touchRead(rightTouchPin) - rightBaseline;
  leftTouchAnalog = constrain(leftTouchValue / rescalingFactor, 0, 100);
  rightTouchAnalog = constrain(rightTouchValue / rescalingFactor, 0, 100);

  if ((leftTouchAnalog > leftThreshold) && !(leftTouched)) {
    leftTouched = true;
    lickState = -1;
    sendMessage(startTime, "-1");
    neopixelWrite(RGB_BUILTIN, 0, RGB_BRIGHTNESS, 0);
  } else if ((leftTouchAnalog < leftThreshold) && (leftTouched)) {
    leftTouched = false;
    lickState = -2;
    sendMessage(startTime, "-2");
    neopixelWrite(RGB_BUILTIN, 0, 0, 0);
  }
  if ((rightTouchAnalog > rightThreshold) && !(rightTouched)) {
    rightTouched = true;
    lickState = 1;
    sendMessage(startTime, "1");
    neopixelWrite(RGB_BUILTIN, 0, 0, RGB_BRIGHTNESS);
  } else if ((rightTouchAnalog < rightThreshold) && (rightTouched)) {
    rightTouched = false;
    lickState = 2;
    sendMessage(startTime, "2");
    neopixelWrite(RGB_BUILTIN, 0, 0, 0);
  }
}

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


bool sdBusy() {
  return ready ? SDcard.card()->isBusy() : false;
}

void loop() {
  checkMessage();
  updateLicks();
  updateEncoder();
  updatePhotodiode();
  if (isLogging){
    if (dataPos<dataMax){
      logCurrentData();
    }
  }
  delay(1);
}

void checkMessage() {
  if (Serial.available() > 0) {
    int msgInt = int(Serial.parseInt());
    String msg = Serial.readStringUntil('\n');  // read until new line character
    RewardSerial.print(msgInt + msg);

    if (msg == "start_session") {
      startSession(msgInt);
      // startTime = millis();
      // resetTouchSensor();
      // encoderPosCount = 0;
      // SDcard.remove("Data.wfm");
      // // DataFile = SDcard.open("Data.wfm", O_RDWR | O_CREAT);
      // DataFile = SDcard.open("Data.wfm", O_RDWR | O_CREAT);
      // if (!DataFile.isOpen()) {
      //   Serial.println("Error opening Data.wfm file");
      //   return;
      // }
      // DataFile.preAllocate(104857600);
      // while (sdBusy()) {}
      // DataFile.seek(0);
      // startLogging();
      // sendMessage(startTime, "clock_started");
    } else if (msg == "reset_licks") {
      resetTouchSensor();
    } else if (msg == "reset_wheel") {
      encoderPosCount = 0;
    } else if (msg == "update_lick_threshold_left)") {
      leftThreshold = msgInt;
      sendMessage(startTime, "left_threshold_modified");
    } else if (msg == "update_lick_threshold_right)") {
      rightThreshold = msgInt;
      sendMessage(startTime, "right_threshold_modified");
    } else if (msg == "end_session") {
      endSession(msgInt);

    }
  }
}