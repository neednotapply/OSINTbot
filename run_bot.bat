@echo off
setlocal
cd /d "%~dp0"
if exist "discordbotvenv\Scripts\python.exe" (
    "discordbotvenv\Scripts\python.exe" -m osintbot
) else (
    py -m osintbot
)
exit /b %errorlevel%
