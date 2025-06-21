@echo off
echo Starting NeuRPi sync to all pilot devices...
echo.

echo Syncing self (local)...
cd /d "%~dp0"
git fetch origin
git reset --hard origin/main
if %errorlevel% equ 0 (
    echo self sync completed successfully
) else (
    echo ERROR: Failed to sync self
)
echo.

echo Syncing pi1...
ssh pi1@pi1 "cd ~/Documents/NeuRPi && git fetch origin && git reset --hard origin/main"
if %errorlevel% equ 0 (
    echo pi1 sync completed successfully
) else (
    echo ERROR: Failed to sync pi1
)
echo.

echo Syncing pi2...
ssh pi2@pi2 "cd ~/Documents/NeuRPi && git fetch origin && git reset --hard origin/main"
if %errorlevel% equ 0 (
    echo pi2 sync completed successfully
) else (
    echo ERROR: Failed to sync pi2
)
echo.

echo Syncing pi3...
ssh pi3@pi3 "cd ~/Documents/NeuRPi && git fetch origin && git reset --hard origin/main"
if %errorlevel% equ 0 (
    echo pi3 sync completed successfully
) else (
    echo ERROR: Failed to sync pi3
)
echo.

echo Syncing pi4...
ssh pi4@pi4 "cd ~/Documents/NeuRPi && git fetch origin && git reset --hard origin/main"
if %errorlevel% equ 0 (
    echo pi4 sync completed successfully
) else (
    echo ERROR: Failed to sync pi4
)
echo.

echo All sync operations completed!
echo Press any key to close this window...
pause >nul
