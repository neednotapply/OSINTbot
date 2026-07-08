@echo off
setlocal ENABLEDELAYEDEXPANSION

echo ================================================
echo   OSINT Discord Bot - Environment Setup (Windows)
echo ================================================
echo.

for %%I in ("%~dp0.") do set "BASE=%%~fI"
set "BOT_DIR=%BASE%"
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
for /f "delims=" %%P in ('python -c "import site; print(site.USER_BASE + r'\Scripts')"') do set "USER_PY_SCRIPTS=%%P"
set "PATH=%USER_PY_SCRIPTS%;%USERPROFILE%\.local\bin;%PATH%"

echo.
echo [1/9] Setting up Sherlock...
cd /d "%TOOLS_DIR%"
if not exist sherlock mkdir sherlock
cd /d "%TOOLS_DIR%\sherlock"
python -m venv sherlockvenv
call sherlockvenv\Scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install sherlock-project
call deactivate

echo.
echo [2/9] Cloning and setting up cupidcr4wl...
cd /d "%TOOLS_DIR%"
if not exist cupidcr4wl git clone https://github.com/OSINTI4L/cupidcr4wl
cd /d "%TOOLS_DIR%\cupidcr4wl"
python -m venv cupidcr4wlvenv
call cupidcr4wlvenv\Scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
call deactivate

echo.
echo [3/9] Cloning and setting up blackbird...
cd /d "%TOOLS_DIR%"
if not exist blackbird git clone https://github.com/p1ngul1n0/blackbird
cd /d "%TOOLS_DIR%\blackbird"
python -m venv blackbirdvenv
call blackbirdvenv\Scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
call deactivate

echo.
echo [4/9] Setting up holehe...
cd /d "%TOOLS_DIR%"
if not exist holehe mkdir holehe
cd /d "%TOOLS_DIR%\holehe"
python -m venv holehevenv
call holehevenv\Scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install holehe
call deactivate

echo.
echo [5/9] Setting up user-scanner...
cd /d "%TOOLS_DIR%"
if not exist user-scanner git clone https://github.com/mishakorzik/UserFinder user-scanner
cd /d "%TOOLS_DIR%\user-scanner"
python -m venv userscannervenv
call userscannervenv\Scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install user-scanner
call deactivate

echo.
echo [6/9] Setting up whois...
cd /d "%TOOLS_DIR%"
if not exist whois mkdir whois
cd /d "%TOOLS_DIR%\whois"
python -m venv whoisvenv
call whoisvenv\Scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install python-whois
call deactivate

echo.
echo [7/9] Setting up theHarvester...
cd /d "%TOOLS_DIR%"
if not exist theHarvester mkdir theHarvester
cd /d "%TOOLS_DIR%\theHarvester"
python -m venv theharvestervenv
call theharvestervenv\Scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install theHarvester
call deactivate

echo.
echo [8/9] Setting up Sublist3r...
cd /d "%TOOLS_DIR%"
if not exist sublist3r mkdir sublist3r
cd /d "%TOOLS_DIR%\sublist3r"
python -m venv sublist3rvenv
call sublist3rvenv\Scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install sublist3r
call deactivate

echo.
echo [9/9] Setting up bot virtual environment...
cd /d "%BOT_DIR%"
python -m venv discordbotvenv
call discordbotvenv\Scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
call deactivate

echo.
echo ================================================
echo Setup complete.
echo Next: configure config.json with BOT_TOKEN.
echo Run manually with:
echo   cd /d %BOT_DIR%
echo   run_bot.bat
echo or:
echo   discordbotvenv\Scripts\python.exe bot.py
echo ================================================
