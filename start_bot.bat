@echo off
cd /d "C:\Trading\Bots\Bot_1"
echo [%date% %time%] Batch started >> debug_log.txt

:: Try to start MT5 and log errors
start "" "C:\Trading\TradingTerminals\terminal64.exe" /portable 2>> debug_log.txt

:: Try to start Python and log errors
"C:\Trading\Bots\Bot_1\venv\Scripts\pythonw.exe" "main.py" 2>> debug_log.txt

echo [%date% %time%] Batch finished >> debug_log.txt