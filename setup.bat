@echo off
setlocal
cd /d "%~dp0"
if not exist "discordbotvenv\Scripts\python.exe" py -m venv discordbotvenv
"discordbotvenv\Scripts\python.exe" -m pip install -e .
if errorlevel 1 exit /b %errorlevel%
"discordbotvenv\Scripts\python.exe" -m osintbot.maintenance install
exit /b %errorlevel%
