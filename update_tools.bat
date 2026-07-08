@echo off
setlocal ENABLEDELAYEDEXPANSION

echo ================================================
echo   OSINT Tool Update Script (Windows)
echo ================================================
echo.

for %%I in ("%~dp0.") do set "BASE=%%~fI"
set "BOT_DIR=%BASE%"
set "TOOLS_DIR=%BASE%\osint-tools"

echo [1/10] Updating Sherlock...
cd /d "%TOOLS_DIR%\sherlock" || goto :err
call sherlockvenv\Scripts\activate.bat
python -m pip install --upgrade sherlock-project certifi
call deactivate

echo.
echo [2/10] Updating cupidcr4wl...
cd /d "%TOOLS_DIR%\cupidcr4wl" || goto :err
call git pull
call cupidcr4wlvenv\Scripts\activate.bat
python -m pip install --upgrade -r requirements.txt
python -m pip install --upgrade certifi
call deactivate

echo.
echo [3/10] Updating blackbird...
cd /d "%TOOLS_DIR%\blackbird" || goto :err
call git pull
call blackbirdvenv\Scripts\activate.bat
python -m pip install --upgrade -r requirements.txt
python -m pip install --upgrade certifi
call deactivate

echo.
echo [4/10] Updating holehe...
cd /d "%TOOLS_DIR%\holehe" || goto :err
call holehevenv\Scripts\activate.bat
python -m pip install --upgrade holehe certifi
call deactivate

echo.
echo [5/10] Updating user-scanner...
cd /d "%TOOLS_DIR%\user-scanner" || goto :err
call userscannervenv\Scripts\activate.bat
python -m pip install --upgrade user-scanner certifi
call deactivate

echo.
echo [6/10] Updating whois...
cd /d "%TOOLS_DIR%\whois" || goto :err
call whoisvenv\Scripts\activate.bat
python -m pip install --upgrade python-whois certifi
call deactivate

echo.
echo [7/10] Updating theHarvester...
cd /d "%TOOLS_DIR%\theHarvester" || goto :err
call theharvestervenv\Scripts\activate.bat
python -m pip install --upgrade theHarvester certifi
call deactivate

echo.
echo [8/10] Updating Sublist3r...
cd /d "%TOOLS_DIR%\sublist3r" || goto :err
call sublist3rvenv\Scripts\activate.bat
python -m pip install --upgrade sublist3r certifi
call deactivate

echo.
echo [9/10] Updating bot dependencies...
cd /d "%BOT_DIR%" || goto :err
call discordbotvenv\Scripts\activate.bat
python -m pip install --upgrade -r requirements.txt
call deactivate

echo.
echo [10/10] Installing child-process SSL patch...
"%BOT_DIR%\discordbotvenv\Scripts\python.exe" "%BOT_DIR%\install_tool_ssl_patch.py"

echo.
echo ================================================
echo Updates complete.
echo Restart your bot process/service after updates.
echo ================================================
exit /b 0

:err
echo [ERROR] Missing expected directory. Ensure setup.bat was run first.
exit /b 1
