@echo off
setlocal ENABLEDELAYEDEXPANSION

echo ================================================
echo   OSINT Discord Bot - Environment Setup (Windows)
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
echo [1/12] Setting up Sherlock...
cd /d "%TOOLS_DIR%"
if not exist sherlock mkdir sherlock
cd /d "%TOOLS_DIR%\sherlock"
python -m venv sherlockvenv
call sherlockvenv\Scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install sherlock-project certifi
python -m pip install --force-reinstall "%BOT_DIR%\tool_shims"
call deactivate

echo.
echo [2/12] Cloning and setting up cupidcr4wl...
cd /d "%TOOLS_DIR%"
if not exist cupidcr4wl git clone https://github.com/OSINTI4L/cupidcr4wl
cd /d "%TOOLS_DIR%\cupidcr4wl"
python -m venv cupidcr4wlvenv
call cupidcr4wlvenv\Scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install --upgrade certifi
call deactivate

echo.
echo [3/12] Cloning and setting up blackbird...
cd /d "%TOOLS_DIR%"
if not exist blackbird git clone https://github.com/p1ngul1n0/blackbird
cd /d "%TOOLS_DIR%\blackbird"
git reset --hard
python -m venv blackbirdvenv
call blackbirdvenv\Scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install --upgrade certifi
call deactivate

echo.
echo [4/12] Setting up holehe...
cd /d "%TOOLS_DIR%"
if not exist holehe mkdir holehe
cd /d "%TOOLS_DIR%\holehe"
python -m venv holehevenv
call holehevenv\Scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install holehe certifi
python -m pip install --force-reinstall "%BOT_DIR%\tool_shims"
call deactivate

echo.
echo [5/12] Setting up user-scanner...
cd /d "%TOOLS_DIR%"
if not exist user-scanner git clone https://github.com/mishakorzik/UserFinder user-scanner
cd /d "%TOOLS_DIR%\user-scanner"
python -m venv userscannervenv
call userscannervenv\Scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install user-scanner certifi
python -m pip install --force-reinstall "%BOT_DIR%\tool_shims"
call deactivate

echo.
echo [6/12] Setting up whois...
cd /d "%TOOLS_DIR%"
if not exist whois mkdir whois
cd /d "%TOOLS_DIR%\whois"
python -m venv whoisvenv
call whoisvenv\Scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install python-whois certifi
call deactivate

echo.
echo [7/12] Setting up theHarvester...
cd /d "%TOOLS_DIR%"
if not exist theHarvester mkdir theHarvester
cd /d "%TOOLS_DIR%\theHarvester"
python -m venv theharvestervenv
call theharvestervenv\Scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install theHarvester certifi
call deactivate

echo.
echo [8/12] Setting up Sublist3r...
cd /d "%TOOLS_DIR%"
if not exist sublist3r mkdir sublist3r
cd /d "%TOOLS_DIR%\sublist3r"
python -m venv sublist3rvenv
call sublist3rvenv\Scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install sublist3r certifi
call deactivate

echo.
echo [9/12] Setting up bot virtual environment...
cd /d "%BOT_DIR%"
python -m venv discordbotvenv
call discordbotvenv\Scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
call deactivate

echo.
echo [10/12] Installing Blackbird wrapper...
"%BOT_DIR%\discordbotvenv\Scripts\python.exe" -m osintbot_tool_shims --patch-blackbird "%BOT_DIR%"

echo.
echo [11/12] Installing child-process SSL patch...
"%BOT_DIR%\discordbotvenv\Scripts\python.exe" -m osintbot_tool_shims --install-ssl-patch "%BOT_DIR%"

echo.
echo [12/12] Verifying tool shim entrypoints...
"%TOOLS_DIR%\sherlock\sherlockvenv\Scripts\sherlock.exe" test --timeout 3 >nul 2>nul
"%TOOLS_DIR%\holehe\holehevenv\Scripts\holehe.exe" test@example.com --timeout 3 >nul 2>nul
"%TOOLS_DIR%\user-scanner\userscannervenv\Scripts\user-scanner.exe" -u test --timeout 3 >nul 2>nul

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
