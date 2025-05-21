#!/bin/bash
set -euo pipefail  # Exit on error, unset vars error, and fail on pipe errors

# === CONFIGURATION ===
# Set SKETCH_PATH to the folder containing the .ino sketch file
# For example, if script is in esp32-controller folder and sketch is in the same folder:
SKETCH_PATH="$(cd "$(dirname "$0")" && pwd)"
PORT="/dev/ttyUSB0"
FQBN="esp32:esp32:esp32"

# Helper for error message and exit
error_exit() {
  printf "❌ %s\n" "$1"
  exit 1
}

# === STEP 0: Install Required Libraries ===
REQUIRED_LIBS_FILE="$SKETCH_PATH/required_libraries.txt"
if [[ -f "$REQUIRED_LIBS_FILE" ]]; then
  echo "📦 Installing required libraries..."
  while IFS= read -r lib || [[ -n $lib ]]; do
    # Trim surrounding quotes if any
    lib="${lib#\"}"
    lib="${lib%\"}"
    [[ -z "$lib" ]] && continue
    printf "Installing: %s\n" "$lib"
    arduino-cli lib install "$lib" || echo "⚠️ $lib may already be installed or failed"
  done < "$REQUIRED_LIBS_FILE"
else
  echo "⚠️ No required_libraries.txt found, skipping library installation."
fi

# === STEP 1: Compile ===
echo "🔨 Compiling sketch..."
if ! arduino-cli compile --fqbn "$FQBN" "$SKETCH_PATH"; then
  error_exit "Compilation failed."
fi

# === STEP 2: Upload ===
echo "⬆️  Uploading to board..."
if ! arduino-cli upload -p "$PORT" --fqbn "$FQBN" "$SKETCH_PATH" > /dev/null 2>&1; then
  error_exit "Upload failed. Check BOOT/RESET if needed."
fi
# === STEP 3: Monitor ===
echo "🖥️  Opening serial monitor. Press Ctrl+C to exit."
if ! arduino-cli monitor -p "$PORT" -b "$FQBN" -c baudrate=115200; then
  error_exit "Serial monitor failed."
fi

echo "✅ Done."
