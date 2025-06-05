#include <Arduino.h>
#include <FS.h>
#include <SD_MMC.h>
#include <MPR121.h>

MPR121 mpr121;

#define ONE_BIT_MODE false
#define ledPin 13
#define leftTouchPin 10
#define rightTouchPin 11
#define encoderPinA 25
#define encoderPinB 26

File DataFile;

bool isLogging = false;
uint32_t dataPos = 0;
uint32_t dataMax = 4294967295;
unsigned long currentTime = 0;

union DataUnion {
  byte uint8[10];
  struct {
    uint32_t elapsedTime;
    uint8_t leftTouchAnalog;
    uint8_t rightTouchAnalog;
    int8_t lickState;
    int16_t encoderPosDegree;
    int8_t photodiodeState;
  } data;
};

#define BUFFER_SIZE (228976 / (3 * sizeof(DataUnion)))
DataUnion sdWriteBuffer[BUFFER_SIZE];
uint32_t bufferCounter = 0;

uint8_t sdReadBuffer[2048] = {0};

int32_t leftThreshold = 40;
int32_t rightThreshold = 40;
uint8_t leftTouchAnalog, rightTouchAnalog;
bool leftTouched = false, rightTouched = false;
int8_t lickState = 0;

volatile int encoderPosCount = 0;
volatile uint32_t encoderPosDegree = 0;
int lastEncoded = 0;

int8_t photodiodeState = 0;
int startTime = 0;

HardwareSerial RewardSerial(2);

void setup() {
  Serial.begin(115200);
  Serial.setTimeout(100);
  RewardSerial.begin(115200);

  mpr121_init();
  startTime = millis();

  pinMode(encoderPinA, INPUT_PULLUP);
  pinMode(encoderPinB, INPUT_PULLUP);
  attachInterrupt(digitalPinToInterrupt(encoderPinA), updateEncoder, CHANGE);
  attachInterrupt(digitalPinToInterrupt(encoderPinB), updateEncoder, CHANGE);

  pinMode(2, INPUT_PULLUP);

  // Initialize SD card with more detailed error reporting
  Serial.println("Initializing_SD_card...");
  if (!SD_MMC.begin("/sdcard", ONE_BIT_MODE)) {
    Serial.println("Card_Mount_Failed");
    return;
  }

  uint8_t cardType = SD_MMC.cardType();
  if (cardType == CARD_NONE) {
    Serial.println("No_SD_card_attached");
    return;
  }

  Serial.print("SD_Card_Type: ");
  if (cardType == CARD_MMC) {
    Serial.println("MMC");
  } else if (cardType == CARD_SD) {
    Serial.println("SDSC");
  } else if (cardType == CARD_SDHC) {
    Serial.println("SDHC");
  } else {
    Serial.println("UNKNOWN");
  }

  uint64_t cardSize = SD_MMC.cardSize() / (1024 * 1024);
  Serial.printf("SD_Card_Size: %lluMB\n", cardSize);

  Serial.println("SD_card_ready");
}

void mpr121_init() {
  mpr121.setupSingleDevice(Wire, MPR121::ADDRESS_5A, true);
  mpr121.setAllChannelsThresholds(40, 20);
  mpr121.setDebounce(MPR121::ADDRESS_5A, 10, 10);
  mpr121.setBaselineTracking(MPR121::ADDRESS_5A, MPR121::BASELINE_TRACKING_INIT_10BIT);
  mpr121.setChargeDischargeCurrent(MPR121::ADDRESS_5A, 63);
  mpr121.setChargeDischargeTime(MPR121::ADDRESS_5A, MPR121::CHARGE_DISCHARGE_TIME_HALF_US);
  mpr121.setFirstFilterIterations(MPR121::ADDRESS_5A, MPR121::FIRST_FILTER_ITERATIONS_34);
  mpr121.setSecondFilterIterations(MPR121::ADDRESS_5A, MPR121::SECOND_FILTER_ITERATIONS_10);
  mpr121.setSamplePeriod(MPR121::ADDRESS_5A, MPR121::SAMPLE_PERIOD_1MS);
  mpr121.startAllChannels(MPR121::ADDRESS_5A, MPR121::COMBINE_CHANNELS_0_TO_11);
}

void resetTouchSensor() {
  mpr121_init();
}

void startSession(int sessionId) {
  startTime = millis();
  resetTouchSensor();
  encoderPosCount = 0;
  photodiodeState = 0;

  // Use sessionId as filename if not zero, otherwise don't record
  if (sessionId == 0) {
    // Don't record if sessionId is 0
    isLogging = false;
    sendMessage("session_started_no_recording");
    return;
  }

  // Check if SD card is still mounted
  if (!SD_MMC.cardType()) {
    Serial.println("SD_card_not_detected");
    // Try to remount
    if (!SD_MMC.begin("/sdcard", ONE_BIT_MODE)) {
      Serial.println("SD_remount_failed");
      return;
    }
  }

  String filename = String(sessionId);
  String fullPath = "/" + filename + ".dat";

  // Try to open file for writing
  DataFile = SD_MMC.open(fullPath.c_str(), FILE_WRITE);
  if (!DataFile) {
    // Try alternative approach - check if directory exists
    Serial.print("Failed_to_open: ");
    Serial.println(fullPath);

    // Try without leading slash
    String altPath = filename + ".dat";
    DataFile = SD_MMC.open(altPath.c_str(), FILE_WRITE);
    if (!DataFile) {
      Serial.println("Failed_both_paths");
      return;
    } else {
      Serial.print("Opened_alternative_path: ");
      Serial.println(altPath);
    }
  } else {
    Serial.print("File_opened: ");
    Serial.println(fullPath);
  }

  isLogging = true;
  currentTime = micros();
  DataFile.seek(0);
  dataPos = 0;
  bufferCounter = 0;  // Reset buffer counter
  sendMessage("session_started");
}

void endSession(int logNeeded) {
  if (isLogging && bufferCounter > 0) {
    // Write remaining buffer data before closing
    DataFile.write((byte*)sdWriteBuffer, bufferCounter * sizeof(DataUnion));
    dataPos += bufferCounter;
    bufferCounter = 0;
  }

  isLogging = false;
  if (DataFile) {
    DataFile.flush();
  }

  if (logNeeded == 1 && DataFile) {
    DataFile.seek(0);  // Go to beginning to read
    while (DataFile.available()) {
      Serial.write(DataFile.read());
    }
    Serial.println("\nsession_successfully_ended");
  }

  dataPos = 0;
  if (DataFile) {
    DataFile.close();
  }
}

void logCurrentData() {
  unsigned long elapsedTime = millis() - startTime;
  auto& entry = sdWriteBuffer[bufferCounter].data;
  entry.elapsedTime = elapsedTime;
  entry.leftTouchAnalog = leftTouchAnalog;
  entry.rightTouchAnalog = rightTouchAnalog;
  entry.lickState = lickState;
  entry.encoderPosDegree = encoderPosDegree;
  entry.photodiodeState = photodiodeState;
  bufferCounter++;

  if (bufferCounter >= BUFFER_SIZE) {
    DataFile.write((byte*)sdWriteBuffer, sizeof(sdWriteBuffer));
    dataPos += bufferCounter;
    bufferCounter = 0;
  }
}

void updateLicks() {
  leftTouchAnalog = mpr121.getChannelFilteredData(leftTouchPin) - mpr121.getChannelBaselineData(leftTouchPin);
  rightTouchAnalog = mpr121.getChannelFilteredData(rightTouchPin) - mpr121.getChannelBaselineData(rightTouchPin);

  if ((leftTouchAnalog > leftThreshold) && !leftTouched) {
    leftTouched = true;
    lickState = -1;
    sendMessage("-1");
  } else if ((leftTouchAnalog < leftThreshold) && leftTouched) {
    leftTouched = false;
    lickState = -2;
    sendMessage("-2");
  }

  if ((rightTouchAnalog > rightThreshold) && !rightTouched) {
    rightTouched = true;
    lickState = 1;
    sendMessage("1");
  } else if ((rightTouchAnalog < rightThreshold) && rightTouched) {
    rightTouched = false;
    lickState = 2;
    sendMessage("2");
  }
}

void updateEncoder() {
  int MSB = digitalRead(encoderPinA);
  int LSB = digitalRead(encoderPinB);
  int encoded = (MSB << 1) | LSB;
  int sum = (lastEncoded << 2) | encoded;

  if (sum == 0b1101 || sum == 0b0100 || sum == 0b0010 || sum == 0b1011) encoderPosCount++;
  if (sum == 0b1110 || sum == 0b0111 || sum == 0b0001 || sum == 0b1000) encoderPosCount--;

  encoderPosDegree = static_cast<int16_t>(encoderPosCount * (90.0 / 1024.0));
  lastEncoded = encoded;
}

void sendMessage(const String& msg) {
  Serial.print(millis() - startTime);
  Serial.print('\t');
  Serial.println(msg);
}

void updatePhotodiode() {}

void loop() {
  checkMessage();
  updateLicks();
  updateEncoder();
  updatePhotodiode();
  if (isLogging) logCurrentData();
  delay(1);
}

void checkMessage() {
  static String inputLine;

  while (Serial.available()) {
    char c = Serial.read();
    if (c == '\n') {
      RewardSerial.println(inputLine);  // Forward message directly
      int commaIndex = inputLine.lastIndexOf(',');
      if (commaIndex > 0) {
        String msg = inputLine.substring(0, commaIndex);
        int value = inputLine.substring(commaIndex + 1).toInt();

        if (msg == "start_session") {
          startSession(value);
        } else if (msg == "reset_licks") {
          resetTouchSensor();
        } else if (msg == "reset_wheel") {
          encoderPosCount = 0;
        } else if (msg == "update_lick_threshold_left") {
          leftThreshold = value;
          sendMessage("left_threshold_modified");
        } else if (msg == "update_lick_threshold_right") {
          rightThreshold = value;
          sendMessage("right_threshold_modified");
        } else if (msg == "end_session") {
          endSession(value);
        }
      }
      inputLine = "";
    } else {
      inputLine += c;
    }
  }
}
