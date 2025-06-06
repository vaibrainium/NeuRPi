@echo off
echo Cleaning up NeuRPi processes...

REM Kill any Python processes that might be running NeuRPi
for /f "tokens=2" %%i in ('tasklist /fi "imagename eq python.exe" ^| findstr python.exe') do (
    echo Killing Python process %%i
    taskkill /PID %%i /F >nul 2>&1
)

for /f "tokens=2" %%i in ('tasklist /fi "imagename eq pythonw.exe" ^| findstr pythonw.exe') do (
    echo Killing Python process %%i
    taskkill /PID %%i /F >nul 2>&1
)

REM Wait a moment for processes to clean up
timeout /t 2 >nul

echo Cleanup complete. You can now restart NeuRPi.
pause
