@echo off
cd /d "%~dp0"
py -3.14 real_game_rl.py
if errorlevel 1 python real_game_rl.py
pause
