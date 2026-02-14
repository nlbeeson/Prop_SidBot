@echo off
:: 1. Start MT5 in Portable Mode
:: 'start' allows the script to continue without waiting for MT5 to close
start "" "C:\Trading\TradingTerminals\terminal64.exe" /portable

:: 2. Wait for MT5 to initialize (15 seconds is usually enough for a VPS)
timeout /t 15 /nobreak

:: 3. Launch the Python Bot
"C:\Trading\Bots\Bot_1\venv\Scripts\pythonw.exe" "C:\Trading\Bots\Bot_1\main.py"