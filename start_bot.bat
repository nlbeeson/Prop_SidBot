@echo off
:: Log the start of the script for visibility
echo [%date% %time%] Launching BeeTrader...

:: 1. Move to the MT5 directory and start terminal
:: Using absolute paths is the most reliable method for VPS startup
cd /d "C:\Trading\TradingTerminals\MT5_1"
start "" "C:\Trading\TradingTerminals\MT5_1\terminal64.exe" /portable

:: 2. Wait 30 seconds for MT5 to establish a broker connection
:: PING is used here as it is often more stable in startup environments than TIMEOUT
ping 127.0.0.1 -n 31 > nul

:: 3. Move to the Bot directory
cd /d "C:\Trading\Bots\Bot_1"

:: 4. Launch Python using the absolute path to the virtual environment
:: Use 'python.exe' instead of 'pythonw.exe' for now so you can see the window
"C:\Trading\Bots\Bot_1\venv\Scripts\python.exe" "C:\Trading\Bots\Bot_1\main.py"