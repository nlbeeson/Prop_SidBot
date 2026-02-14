@echo off
:: 1. Force move to the MT5 directory and launch the terminal
cd /d "C:\Trading\TradingTerminals\MT5_1"
start "" "C:\Trading\TradingTerminals\MT5_1\terminal64.exe" /portable

:: 2. Wait 30 seconds for MT5 to establish a broker connection
ping 127.0.0.1 -n 31 > nul

:: 3. Force move to the Bot directory
cd /d "C:\Trading\Bots\Bot_1"

:: 4. Launch Python using the absolute path to the venv and the script
:: Using 'python.exe' instead of 'pythonw.exe' will let you see the window on your VPS desktop
"C:\Trading\Bots\Bot_1\venv\Scripts\python.exe" "C:\Trading\Bots\Bot_1\main.py"