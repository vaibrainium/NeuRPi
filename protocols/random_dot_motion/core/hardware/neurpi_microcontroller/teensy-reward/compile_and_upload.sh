#!/bin/bash

# === CONFIGURATION ===
SKETCH_PATH="/home/pi3/NeuRPi/protocols/random_dot_motion/core/hardware/neurpi_microcontroller/teensy-reward"  # Change to your sketch folder
FQBN="teensy:avr:teensy40"

# Default port
MONITOR_PORT="/dev/ttyACM0"

# Check if default port exists, otherwise auto-detect
if [ ! -e "$MONITOR_PORT" ]; then
  echo "Default port $MONITOR_PORT not found, trying to auto-detect..."
  MONITOR_PORT=$(ls /dev/ttyACM* 2>/dev/null | head -n 1)
  if [ -z "$MONITOR_PORT" ]; then
    echo "⚠️ No /dev/ttyACM* devices found. Serial monitor may not work."
    MONITOR_PORT=""
  else
    echo "Auto-detected serial port: $MONITOR_PORT"
  fi
else
  echo "Using default serial port: $MONITOR_PORT"
fi

# === STEP 1: Compile ===
BUILD_DIR="$SKETCH_PATH/build"
mkdir -p "$BUILD_DIR"

echo "🔨 Compiling sketch for Teensy 4.0..."
arduino-cli compile --fqbn "$FQBN" --build-path "$BUILD_DIR" "$SKETCH_PATH"
if [ $? -ne 0 ]; then
  echo "❌ Compilation failed."
  exit 1
fi

# === STEP 1.5: Find HEX file ===
HEX_FILE=$(find "$BUILD_DIR" -maxdepth 2 -name "*.hex" | head -n 1)

if [ -z "$HEX_FILE" ]; then
  echo "❌ HEX file not found in build directory: $BUILD_DIR"
  exit 1
else
  echo "Found HEX file: $HEX_FILE"
fi

# Check teensy_loader_cli command availability
if ! command -v teensy_loader_cli &> /dev/null; then
  echo "❌ teensy_loader_cli not found. Please install it first."
  exit 1
fi

echo "⬆️  Uploading via teensy_loader_cli..."
# teensy_loader_cli --mcu=TEENSY40 -w -s "$HEX_FILE"
teensy_loader_cli --mcu=mk66fx1m0 -w -s "$HEX_FILE"

if [ $? -ne 0 ]; then
  echo "❌ Upload failed. Try pressing the reset button on the board."
  exit 1
fi

echo "✅ Upload complete."

# === STEP 3: Monitor (optional) ===
if [ -z "$MONITOR_PORT" ]; then
  echo "Skipping serial monitor since no serial port was found."
  exit 0
fi

read -p "Open serial monitor on $MONITOR_PORT? [y/N]: " answer
if [[ "$answer" =~ ^[Yy]$ ]]; then
  echo "🖥️  Opening serial monitor. Press Ctrl+C to exit."
  arduino-cli monitor -p "$MONITOR_PORT" -b "$FQBN"
else
  echo "Serial monitor skipped."
fi
