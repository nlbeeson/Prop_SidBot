@echo off
REM Wait a few seconds after login for Windows to be ready
timeout /t 10 /nobreak

REM Change to your bot folder
cd "C:\Trading\Bots\Bot_1"

REM Run Python bot and redirect output to a log file
C:\Trading\Bots\Bot_1\venv\Scripts\python.exe your_bot.py >> "C:\Trading\Bots\Bot_1\bot.log" 2>&1
