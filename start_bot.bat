@echo off
:: Log the attempt for debugging
echo [%date% %time%] Attempting to start MT5... >> startup_debug.log

:: Start MT5 using the absolute path
start "" "C:\Trading\TradingTerminals\terminal64.exe" /portable

:: Headless-friendly 30-second wait for MT5 to initialize
ping 127.0.0.1 -n 31 > nul

echo [%date% %time%] Attempting to start Python... >> startup_debug.log

:: Move to the bot directory
cd /d "C:\Trading\Bots\Bot_1"

:: Launch Python using the absolute path to the venv
"C:\Trading\Bots\Bot_1\venv\Scripts\pythonw.exe" "main.py"

echo [%date% %time%] Batch execution complete. >> startup_debug.log