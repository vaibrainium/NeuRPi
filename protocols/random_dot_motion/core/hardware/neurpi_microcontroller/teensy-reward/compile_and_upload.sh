#!/bin/bash
set -e  # Exit on any error

# === CONFIGURATION ===
SKETCH_PATH="$(cd "$(dirname "$0")" && pwd)"
FQBN="teensy:avr:teensy40"
MONITOR_PORT="/dev/ttyACM0"

# Check if default port exists, otherwise auto-detect
if [ ! -e "$MONITOR_PORT" ]; then
  echo "Default port $MONITOR_PORT not found, trying to auto-detect..."
  MONITOR_PORT=$(ls /dev/ttyACM* 2>/dev/null | head -n 1 || true)
  if [ -z "$MONITOR_PORT" ]; then
    echo "⚠️ No /dev/ttyACM* devices found. Serial monitor may not work."
  else
    echo "Auto-detected serial port: $MONITOR_PORT"
  fi
else
  echo "Using default serial port: $MONITOR_PORT"
fi

# === STEP 0: Install Required Libraries (optional) ===
REQUIRED_LIBS_FILE="$SKETCH_PATH/required_libraries.txt"
if [[ -f "$REQUIRED_LIBS_FILE" ]]; then
  echo "📦 Installing required libraries..."
  while IFS= read -r lib || [[ -n $lib ]]; do
    lib="${lib#\"}"
    lib="${lib%\"}"
    [[ -z "$lib" ]] && continue
    echo "Installing: $lib"
    arduino-cli lib install "$lib" || echo "⚠️ $lib may already be installed or failed"
  done < "$REQUIRED_LIBS_FILE"
else
  echo "⚠️ No required_libraries.txt found, skipping library installation."
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
sudo teensy_loader_cli --mcu=TEENSY40 -w -s "$HEX_FILE"
# sudo teensy_loader_cli --mcu=imxrt1062 -w -s "$HEX_FILE"



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
	if ! arduino-cli monitor -p "$MONITOR_PORT" -b "$FQBN" -c baudrate=115200; then
	error_exit "Serial monitor failed."
	fi
else
  echo "Serial monitor skipped."
fi

echo "✅ Done."
