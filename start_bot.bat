@echo off
REM wait for desktop session to settle
timeout /t 15 /nobreak

REM set working directory
cd /d "C:\Trading\Bots\Bot_1"

REM run bot in the background with logging
start "" /B "C:\Trading\Bots\Bot_1\venv\Scripts\python.exe" main.py >> "bot_activity.log" 2>&1
