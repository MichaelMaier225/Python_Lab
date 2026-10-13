@echo off
cd /d "%~dp0"
py -3.14 train_rl.py --episodes 30000
if errorlevel 1 python train_rl.py --episodes 30000
pause
