@echo off
setlocal
cd /d "%~dp0"
if not exist "discordbotvenv\Scripts\python.exe" (
    echo [ERROR] Run setup.bat first.
    exit /b 1
)
"discordbotvenv\Scripts\python.exe" -m pip install -e .
if errorlevel 1 exit /b %errorlevel%
"discordbotvenv\Scripts\python.exe" -m osintbot.maintenance update
exit /b %errorlevel%
