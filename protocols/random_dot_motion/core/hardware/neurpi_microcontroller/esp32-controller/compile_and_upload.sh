#!/bin/bash

# === CONFIGURATION ===
SKETCH_PATH="$HOME/NeuRPi/protocols/random_dot_motion/core/hardware/neurpi_microcontroller/esp32-controller"
PORT="/dev/ttyUSB0"
FQBN="esp32:esp32:esp32"

# === STEP 0: Install Required Libraries ===
REQUIRED_LIBS_FILE="$SKETCH_PATH/required_libraries.txt"
if [ -f "$REQUIRED_LIBS_FILE" ]; then
  echo "📦 Installing required libraries..."
  while IFS= read -r lib; do
    lib=$(echo "$lib" | sed 's/^"//;s/"$//')  # Remove surrounding quotes
    [[ -z "$lib" ]] && continue
    echo "Installing: $lib"
    arduino-cli lib install "$lib" || echo "⚠️ $lib may already be installed or failed"
  done < "$REQUIRED_LIBS_FILE"
else
  echo "⚠️ No required_libraries.txt found, skipping library installation."
fi


# === STEP 1: Compile ===
echo "🔨 Compiling sketch..."
arduino-cli compile --fqbn "$FQBN" "$SKETCH_PATH"
if [ $? -ne 0 ]; then
  echo "❌ Compilation failed."
  exit 1
fi

# === STEP 2: Upload ===
echo "⬆️  Uploading to board..."
arduino-cli upload -p "$PORT" --fqbn "$FQBN" "$SKETCH_PATH"
if [ $? -ne 0 ]; then
  echo "❌ Upload failed. Check BOOT/RESET if needed."
  exit 1
fi

# === STEP 3: Monitor ===
echo "🖥️  Opening serial monitor. Press Ctrl+C to exit."
arduino-cli monitor -p "$PORT" -b "$FQBN"
if [ $? -ne 0 ]; then
  echo "❌ Serial monitor failed."
  exit 1
fi

echo "✅ Done."
