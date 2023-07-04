/*********************************************************
This is a library for the MPR121 12-channel Capacitive touch sensor

Designed specifically to work with the MPR121 Breakout in the Adafruit shop
  ----> https://www.adafruit.com/products/

These sensors use I2C communicate, at least 2 pins are required
to interface

Adafruit invests time and resources providing this open source code,
please support Adafruit and open-source hardware by purchasing
products from Adafruit!

Written by Limor Fried/Ladyada for Adafruit Industries.
BSD license, all text above must be included in any redistribution
**********************************************************/

#include <Wire.h>
#include "Adafruit_MPR121.h"

#ifndef _BV
#define _BV(bit) (1 << (bit))
#endif

int start_millis;

bool left_touched = false;
bool right_touched = false;
int left_value = 0;
int right_value = 0;
int left_threshold = 5;
int right_threshold = 5;

int led_pin = 13;
String msg;
int msg_int;
#define left_pin 10
#define right_pin 11
int lick_threshold = 5;

// Keeps track of the last pins touched
// so we know when buttons are 'released'
uint16_t lasttouched = 0;
uint16_t currtouched = 0;
// uint32_t start_time = millis();

// Creating lick senor object
// You can have up to 4 on one i2c bus but one is enough for testing!
Adafruit_MPR121 cap = Adafruit_MPR121();

void send_message(int start_millis, String msg)
{
    String msg_string = millis() - start_millis;
    msg_string += "\t";
    msg_string += msg;
    Serial.println(msg_string);
}

void get_licks(int start_millis)
{
    //  left_value = cap.filteredData(left_pin);// - cap.baselineData(left_pin);
    //  right_value = cap.filteredData(right_pin);// - cap.baselineData(right_pin);
    //  Serial.print(left_value);
    //  Serial.print(",");
    //  Serial.println(right_value);
    //  delay(5);

    // Get the currently touched pads
    currtouched = cap.touched();

    // it if *is* touched and *wasnt* touched before, alert!
    if ((currtouched & _BV(left_pin)) && !(lasttouched & _BV(left_pin)))
    {
        send_message(start_millis, "-1");
        digitalWrite(led_pin, HIGH);
        left_touched = true;
        //    delay(5);
    }
    // if it *was* touched and now *isnt*, alert!
    if (!(currtouched & _BV(left_pin)) && (lasttouched & _BV(left_pin)))
    {
        send_message(start_millis, "-2");
        digitalWrite(led_pin, LOW);
        left_touched = false;
    }
    // it if *is* touched and *wasnt* touched before, alert!
    if ((currtouched & _BV(right_pin)) && !(lasttouched & _BV(right_pin)))
    {
        send_message(start_millis, "1");
        digitalWrite(led_pin, HIGH);
        right_touched = true;
        //    delay(5);
    }
    // if it *was* touched and now *isnt*, alert!
    if (!(currtouched & _BV(right_pin)) && (lasttouched & _BV(right_pin)))
    {
        send_message(start_millis, "2");
        digitalWrite(led_pin, LOW);
        right_touched = false;
    }

    // reset our state
    lasttouched = currtouched;

    //  delay(10);
    return;
}

void measure_licks(int left_threshold, int right_threshold)
{
    left_value = cap.filteredData(left_pin) - cap.baselineData(left_pin);
    right_value = cap.filteredData(right_pin) - cap.baselineData(right_pin);

    if ((left_value > left_threshold) && !(left_touched))
    {
        left_touched = true;
        send_message(start_millis, "-1");
        digitalWrite(led_pin, HIGH);
    }

    if ((left_value < left_threshold) && (left_touched))
    {
        left_touched = false;
        send_message(start_millis, "-2");
        digitalWrite(led_pin, LOW);
    }

    if ((right_value > right_threshold) && !(right_touched))
    {
        right_touched = true;
        send_message(start_millis, "1");
        digitalWrite(led_pin, HIGH);
    }

    if ((right_value < right_threshold) && (right_touched))
    {
        right_touched = false;
        send_message(start_millis, "2");
        digitalWrite(led_pin, LOW);
    }

    delay(1);
}

void resetMPR121()
{
    //  cap.end(); // Disable the MPR121
    //  cap = Adafruit_MPR121(); // Re-instantiating MPR121 object rather than disabling it
    //  delay(10);   // Delay for a short period
    cap.begin(); // Re-enable the MPR121
}

void setup()
{
    Serial.begin(115200);
    // Reward arduino
    Serial1.begin(115200);
    Serial1.print("reward_left");
    delay(20);
    Serial1.print("reward_right");
    Serial.setTimeout(100);

    while (!Serial)
    { // needed to keep leonardo/micro from starting too fast!
        delay(10);
    }
    while (!Serial1)
    { // needed to keep leonardo/micro from starting too fast!
        delay(10);
    }

    // Initialize the I2C bus
    Wire.begin();
    while (!cap.begin(0x5A))
    {
        // Default address is 0x5A, if tied to 3.3V its 0x5B
        // If tied to SDA its 0x5C and if SCL then 0x5D
        Serial.println("MPR121 not found, check wiring?");
    }
    cap.setThresholds(lick_threshold, 0);

    // Starting session timer
    start_millis = millis();
}

void loop()
{
    //  see if there's incoming serial data:
    if (Serial.available() > 0)
    {

        // read and forward incoming string from serial buffer
        msg_int = int(Serial.parseInt());
        msg = Serial.readStringUntil('\n'); // Read until new line character
                                            //        msg = Serial.readString();
        Serial1.print(msg_int + msg);

        // resetting millis timer to zero
        if (msg == "reset")
        {
            //          unsigned long start_time = millis();
            resetMPR121();
            send_message(start_millis, "board_resetted");
        }

        // starting session clock
        else if (msg == "start_clock")
        {
            start_millis = millis();
            send_message(start_millis, "clock_started");
        }

        // updating lick_threshold
        else if (msg == "update_lick_threshold")
        {
            left_threshold = msg_int;
            right_threshold = msg_int;
            lick_threshold = msg_int;
            cap.setThresholds(lick_threshold, 0);
            send_message(start_millis, "lick_threshold_modified");
        }

        // updating lick_threshold
        else if (msg == "update_lick_threshold_left")
        {
            // threshold_multiplier_left = msg_int;
            left_threshold = msg_int;
            cap.writeRegister(MPR121_TOUCHTH_0 + left_pin * 2, left_threshold);       // change left touch threshold
            cap.writeRegister(MPR121_RELEASETH_0 + left_pin * 2, left_threshold - 1); // change left release threshold
            send_message(start_millis, "left_threshold_modified");
        }

        // updating lick_threshold
        else if (msg == "update_lick_threshold_right")
        {
            // threshold_multiplier_right = msg_int;
            right_threshold = msg_int;
            cap.writeRegister(MPR121_TOUCHTH_0 + right_pin * 2, right_threshold);       // change right touch threshold
            cap.writeRegister(MPR121_RELEASETH_0 + right_pin * 2, right_threshold - 1); // change right release threshold
            send_message(start_millis, "right_threshold_modified");
        }
    }

    // Continuously monitor lick sesor
    //    measure_licks(left_threshold, right_threshold);
    get_licks(start_millis);
}