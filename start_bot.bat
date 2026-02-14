@echo off
:: Move to the MT5 directory first
cd /d "C:\Trading\TradingTerminals"
start "" "terminal64.exe" /portable

:: Wait for MT5 to load
timeout /t 20 /nobreak

:: Move to the Bot directory before launching Python
cd /d "C:\Trading\Bots\Bot_1"
"C:\Trading\Bots\Bot_1\venv\Scripts\pythonw.exe" "main.py"