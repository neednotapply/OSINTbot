@echo off
setlocal ENABLEDELAYEDEXPANSION

echo ================================================
echo   OSINT Discord Bot - Environment Setup (Windows)
echo ================================================
echo.

set "BASE=%USERPROFILE%"
set "BOT_DIR=%BASE%\discord-bot"
set "TOOLS_DIR=%BASE%\osint-tools"

where git >nul 2>nul || (
  echo [ERROR] git is required. Install Git for Windows and re-run.
  exit /b 1
)
where python >nul 2>nul || (
  echo [ERROR] python is required. Install Python 3.10+ and re-run.
  exit /b 1
)

if not exist "%BOT_DIR%" mkdir "%BOT_DIR%"
if not exist "%TOOLS_DIR%" mkdir "%TOOLS_DIR%"

python -m pip install --upgrade pip
python -m pip install --user pipx
python -m pipx ensurepath
set "PATH=%USERPROFILE%\AppData\Roaming\Python\Python311\Scripts;%USERPROFILE%\.local\bin;%PATH%"

echo.
echo [1/6] Installing Sherlock...
call pipx install sherlock-project

echo.
echo [2/6] Cloning and setting up cupidcr4wl...
cd /d "%TOOLS_DIR%"
if not exist cupidcr4wl git clone https://github.com/OSINTI4L/cupidcr4wl
cd /d "%TOOLS_DIR%\cupidcr4wl"
python -m venv cupidcr4wlvenv
call cupidcr4wlvenv\Scripts\activate.bat
pip install -r requirements.txt
call deactivate

echo.
echo [3/6] Cloning and setting up blackbird...
cd /d "%TOOLS_DIR%"
if not exist blackbird git clone https://github.com/p1ngul1n0/blackbird
cd /d "%TOOLS_DIR%\blackbird"
python -m venv blackbirdvenv
call blackbirdvenv\Scripts\activate.bat
pip install -r requirements.txt
call deactivate

echo.
echo [4/6] Setting up holehe...
cd /d "%TOOLS_DIR%"
if not exist holehe mkdir holehe
cd /d "%TOOLS_DIR%\holehe"
python -m venv holehevenv
call holehevenv\Scripts\activate.bat
pip install holehe
call deactivate

echo.
echo [5/6] Setting up user-scanner...
cd /d "%TOOLS_DIR%"
if not exist user-scanner git clone https://github.com/mishakorzik/UserFinder user-scanner
cd /d "%TOOLS_DIR%\user-scanner"
python -m venv userscannervenv
call userscannervenv\Scripts\activate.bat
pip install user-scanner
call deactivate

echo.
echo [6/6] Setting up bot virtual environment...
cd /d "%BOT_DIR%"
python -m venv discordbotvenv
call discordbotvenv\Scripts\activate.bat
pip install discord.py requests
call deactivate

echo.
echo ================================================
echo Setup complete.
echo Next: copy osint_bot.py into %BOT_DIR% and configure config.json values.
echo Run manually with:
echo   cd /d %BOT_DIR%
echo   discordbotvenv\Scripts\python osint_bot.py
echo ================================================
