@echo off
setlocal ENABLEDELAYEDEXPANSION

echo ================================================
echo   OSINT Tool Update Script (Windows)
echo ================================================
echo.

for %%I in ("%~dp0.") do set "BASE=%%~fI"
set "BOT_DIR=%BASE%"
set "TOOLS_DIR=%BASE%\osint-tools"
if defined PYTHONPATH (
  set "PYTHONPATH=%BOT_DIR%\tool_shims;%PYTHONPATH%"
) else (
  set "PYTHONPATH=%BOT_DIR%\tool_shims"
)

echo [1/13] Updating Sherlock...
cd /d "%TOOLS_DIR%\sherlock" || goto :err
call sherlockvenv\Scripts\activate.bat
python -m pip install --upgrade sherlock-project certifi
python -m pip install --force-reinstall "%BOT_DIR%\tool_shims"
call deactivate

echo.
echo [2/13] Updating cupidcr4wl...
cd /d "%TOOLS_DIR%\cupidcr4wl" || goto :err
call git pull
call cupidcr4wlvenv\Scripts\activate.bat
python -m pip install --upgrade -r requirements.txt
python -m pip install --upgrade certifi
call deactivate

echo.
echo [3/13] Updating blackbird...
cd /d "%TOOLS_DIR%\blackbird" || goto :err
git reset --hard
call git pull
call blackbirdvenv\Scripts\activate.bat
python -m pip install --upgrade -r requirements.txt
python -m pip install --upgrade certifi
call deactivate
"%BOT_DIR%\discordbotvenv\Scripts\python.exe" -m osintbot_tool_shims --patch-blackbird "%BOT_DIR%"

echo.
echo [4/13] Updating holehe...
cd /d "%TOOLS_DIR%\holehe" || goto :err
call holehevenv\Scripts\activate.bat
python -m pip install --upgrade holehe certifi
python -m pip install --force-reinstall "%BOT_DIR%\tool_shims"
call deactivate

echo.
echo [5/13] Updating user-scanner...
cd /d "%TOOLS_DIR%\user-scanner" || goto :err
call userscannervenv\Scripts\activate.bat
python -m pip install --upgrade user-scanner certifi
python -m pip install --force-reinstall "%BOT_DIR%\tool_shims"
call deactivate

echo.
echo [6/13] Updating whois...
cd /d "%TOOLS_DIR%\whois" || goto :err
call whoisvenv\Scripts\activate.bat
python -m pip install --upgrade python-whois certifi
call deactivate

echo.
echo [7/13] Updating theHarvester...
cd /d "%TOOLS_DIR%\theHarvester" || goto :err
call theharvestervenv\Scripts\activate.bat
python -m pip install --upgrade theHarvester certifi
call deactivate

echo.
echo [8/13] Updating Sublist3r...
cd /d "%TOOLS_DIR%\sublist3r" || goto :err
call sublist3rvenv\Scripts\activate.bat
python -m pip install --upgrade sublist3r certifi
call deactivate

echo.
echo [9/13] Updating bot dependencies...
cd /d "%BOT_DIR%" || goto :err
call discordbotvenv\Scripts\activate.bat
python -m pip install --upgrade -r requirements.txt
call deactivate

echo.
echo [10/13] Applying bot parser maintenance patches...
"%BOT_DIR%\discordbotvenv\Scripts\python.exe" "%BOT_DIR%\tool_shims\bot_maintenance.py" "%BOT_DIR%"

echo.
echo [11/13] Installing child-process SSL patch...
"%BOT_DIR%\discordbotvenv\Scripts\python.exe" -m osintbot_tool_shims --install-ssl-patch "%BOT_DIR%"

echo.
echo [12/13] Verifying tool shim entrypoints...
"%TOOLS_DIR%\sherlock\sherlockvenv\Scripts\sherlock.exe" test --timeout 3 >nul 2>nul
"%TOOLS_DIR%\holehe\holehevenv\Scripts\holehe.exe" test@example.com --timeout 3 >nul 2>nul
"%TOOLS_DIR%\user-scanner\userscannervenv\Scripts\user-scanner.exe" -u test --timeout 3 >nul 2>nul

echo.
echo [13/13] Done.

echo.
echo ================================================
echo Updates complete.
echo Restart your bot process/service after updates.
echo ================================================
exit /b 0

:err
echo [ERROR] Missing expected directory. Ensure setup.bat was run first.
exit /b 1
