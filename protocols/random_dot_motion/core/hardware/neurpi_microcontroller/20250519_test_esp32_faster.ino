// Enhanced ESP32-S2 Data Logger with FreeRTOS and Optimized SD Logging
// Includes:
// - FreeRTOS task separation
// - Buffered SD card writing
// - Async serial command handling
//
// Target: ESP32-S2-Dev board

#include "FS.h"
#include "SD_MMC.h"
#include <MPR121.h>
#include <freertos/FreeRTOS.h>
#include <freertos/task.h>

MPR121 mpr121;

#define ONE_BIT_MODE false
#define BUFFER_SIZE 256
#define CMD_BUF_LEN 64

File DataFile;

volatile bool isLogging = false;

struct DataPacket {
  uint32_t elapsedTime;
  uint8_t leftTouchAnalog;
  uint8_t rightTouchAnalog;
  int8_t lickState;
  int16_t encoderPosDegree;
  int8_t photodiodeState;
};

DataPacket sdWriteBuffer[BUFFER_SIZE];
volatile uint32_t bufferCounter = 0;

// Touch sensor
#define leftTouchPin 10
#define rightTouchPin 11
int32_t leftThreshold = 40;
int32_t rightThreshold = 40;
uint8_t leftTouchAnalog;
uint8_t rightTouchAnalog;
bool leftTouched = false;
bool rightTouched = false;
int8_t lickState = 0;

// Encoder
#define encoderPinA 25
#define encoderPinB 26
const float resolution = 90 / 1024.0;
volatile int encoderPosCount = 0;
volatile int16_t encoderPosDegree = 0;
int lastEncoded = 0;

// Session
int sessionStartTime = 0;
int8_t photodiodeState = 0;

HardwareSerial RewardSerial(2);

void mpr121_begin() {
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
}

void IRAM_ATTR updateEncoder() {
  int MSB = digitalRead(encoderPinA);
  int LSB = digitalRead(encoderPinB);
  int encoded = (MSB << 1) | LSB;
  int sum = (lastEncoded << 2) | encoded;
  if (sum == 0b1101 || sum == 0b0100 || sum == 0b0010 || sum == 0b1011) encoderPosCount++;
  if (sum == 0b1110 || sum == 0b0111 || sum == 0b0001 || sum == 0b1000) encoderPosCount--;
  encoderPosDegree = static_cast<int16_t>(encoderPosCount * resolution);
  lastEncoded = encoded;
}

void logCurrentData() {
  if (!isLogging || bufferCounter >= BUFFER_SIZE) return;
  uint32_t idx = bufferCounter++;
  sdWriteBuffer[idx].elapsedTime = millis() - sessionStartTime;
  sdWriteBuffer[idx].leftTouchAnalog = leftTouchAnalog;
  sdWriteBuffer[idx].rightTouchAnalog = rightTouchAnalog;
  sdWriteBuffer[idx].lickState = lickState;
  sdWriteBuffer[idx].encoderPosDegree = encoderPosDegree;
  sdWriteBuffer[idx].photodiodeState = photodiodeState;
}

void writeToSDTask(void *pvParameters) {
  for (;;) {
    if (isLogging && bufferCounter > 0) {
      noInterrupts();
      uint32_t count = bufferCounter;
      bufferCounter = 0;
      interrupts();
      DataFile.write((uint8_t*)sdWriteBuffer, count * sizeof(DataPacket));
      DataFile.flush();
    }
    vTaskDelay(pdMS_TO_TICKS(50));
  }
}

void checkTouchTask(void *pvParameters) {
  for (;;) {
    leftTouchAnalog = mpr121.getChannelFilteredData(leftTouchPin) - mpr121.getChannelBaselineData(leftTouchPin);
    rightTouchAnalog = mpr121.getChannelFilteredData(rightTouchPin) - mpr121.getChannelBaselineData(rightTouchPin);

    if ((leftTouchAnalog > leftThreshold) && !leftTouched) {
      leftTouched = true;
      lickState = -1;
    } else if ((leftTouchAnalog < leftThreshold) && leftTouched) {
      leftTouched = false;
      lickState = -2;
    }
    if ((rightTouchAnalog > rightThreshold) && !rightTouched) {
      rightTouched = true;
      lickState = 1;
    } else if ((rightTouchAnalog < rightThreshold) && rightTouched) {
      rightTouched = false;
      lickState = 2;
    }
    logCurrentData();
    vTaskDelay(pdMS_TO_TICKS(1));
  }
}

void checkCommandTask(void *pvParameters) {
  char input[CMD_BUF_LEN];
  for (;;) {
    if (Serial.available()) {
      int msgInt = Serial.parseInt();
      String msg = Serial.readStringUntil('\n');
      RewardSerial.println(String(msgInt) + msg);

      if (msg == "start_session") {
        sessionStartTime = millis();
        String fname = Serial.readStringUntil('\n');
        if (fname.length() == 0) fname = "Data";
        fname = "/" + fname + ".dat";
        DataFile = SD_MMC.open(fname.c_str(), FILE_WRITE);
        isLogging = true;
      } else if (msg == "end_session") {
        isLogging = false;
        DataFile.flush();
        DataFile.close();
        Serial.println("\nsession_successfully_ended");
      } else if (msg == "reset_licks") {
        mpr121_begin();
      } else if (msg == "reset_wheel") {
        encoderPosCount = 0;
      } else if (msg == "update_lick_threshold_left") {
        leftThreshold = msgInt;
      } else if (msg == "update_lick_threshold_right") {
        rightThreshold = msgInt;
      }
    }
    vTaskDelay(pdMS_TO_TICKS(10));
  }
}

void setup() {
  Serial.begin(115200);
  RewardSerial.begin(115200);
  mpr121_begin();
  pinMode(encoderPinA, INPUT_PULLUP);
  pinMode(encoderPinB, INPUT_PULLUP);
  attachInterrupt(digitalPinToInterrupt(encoderPinA), updateEncoder, CHANGE);
  attachInterrupt(digitalPinToInterrupt(encoderPinB), updateEncoder, CHANGE);

  if (!SD_MMC.begin("/sdcard", ONE_BIT_MODE)) {
    Serial.println("Card_Mount_Failed");
    return;
  }

  xTaskCreatePinnedToCore(writeToSDTask, "SD_Write", 4096, NULL, 1, NULL, 0);
  xTaskCreatePinnedToCore(checkTouchTask, "Touch_Read", 2048, NULL, 1, NULL, 0);
  xTaskCreatePinnedToCore(checkCommandTask, "Command_Parse", 2048, NULL, 1, NULL, 1);
}

void loop() {
  // Empty - logic handled in FreeRTOS tasks
}
