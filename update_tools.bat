@echo off
setlocal ENABLEDELAYEDEXPANSION

echo ================================================
echo   OSINT Tool Update Script (Windows)
echo ================================================
echo.

set "BASE=%USERPROFILE%"
set "BOT_DIR=%BASE%\discord-bot"
set "TOOLS_DIR=%BASE%\osint-tools"

echo [1/6] Updating Sherlock...
call pipx upgrade sherlock-project

echo.
echo [2/6] Updating cupidcr4wl...
cd /d "%TOOLS_DIR%\cupidcr4wl" || goto :err
call git pull
call cupidcr4wlvenv\Scripts\activate.bat
pip install --upgrade -r requirements.txt
call deactivate

echo.
echo [3/6] Updating blackbird...
cd /d "%TOOLS_DIR%\blackbird" || goto :err
call git pull
call blackbirdvenv\Scripts\activate.bat
pip install --upgrade -r requirements.txt
call deactivate

echo.
echo [4/6] Updating holehe...
cd /d "%TOOLS_DIR%\holehe" || goto :err
call holehevenv\Scripts\activate.bat
pip install --upgrade holehe
call deactivate

echo.
echo [5/6] Updating user-scanner...
cd /d "%TOOLS_DIR%\user-scanner" || goto :err
call userscannervenv\Scripts\activate.bat
pip install --upgrade user-scanner
call deactivate

echo.
echo [6/6] Updating bot dependencies...
cd /d "%BOT_DIR%" || goto :err
call discordbotvenv\Scripts\activate.bat
pip install --upgrade discord.py requests
call deactivate

echo.
echo ================================================
echo Updates complete.
echo Restart your bot process/service after updates.
echo ================================================
exit /b 0

:err
echo [ERROR] Missing expected directory. Ensure setup.bat was run first.
exit /b 1
