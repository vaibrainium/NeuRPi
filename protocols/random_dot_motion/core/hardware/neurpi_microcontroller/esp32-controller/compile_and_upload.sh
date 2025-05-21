#!/bin/bash

# === CONFIGURATION ===
SKETCH_PATH="$HOME/NeuRPi/protocols/random_dot_motion/core/hardware/neurpi_microcontroller/esp32-controller"
PORT="/dev/ttyUSB0"
FQBN="esp32:esp32:esp32"

# === STEP 1: Compile ===
echo "🔨 Compiling sketch..."
arduino-cli compile --fqbn $FQBN "$SKETCH_PATH"
if [ $? -ne 0 ]; then
  echo "❌ Compilation failed."
  exit 1
fi

# === STEP 2: Upload ===
echo "⬆️  Uploading to board..."
arduino-cli upload -p $PORT --fqbn $FQBN "$SKETCH_PATH"
if [ $? -ne 0 ]; then
  echo "❌ Upload failed. Check BOOT/RESET if needed."
  exit 1
fi

# === STEP 3: Monitor ===
echo "🖥️  Opening serial monitor. Press Ctrl+C to exit."
arduino-cli monitor -p $PORT -b $FQBN
if [ $? -ne 0 ]; then
  echo "❌ Serial monitor failed."
  exit 1
fi
echo "✅ Done."
