@echo off
setlocal

cd /d "%~dp0"

if exist "discordbotvenv\Scripts\python.exe" (
  "discordbotvenv\Scripts\python.exe" bot.py
  exit /b %ERRORLEVEL%
)

echo [WARN] discordbotvenv was not found. Falling back to the active Python on PATH.
echo [WARN] For the expected setup, run setup.bat first.
py bot.py
exit /b %ERRORLEVEL%
