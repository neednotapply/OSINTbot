#!/usr/bin/env bash

# OSINT Discord Bot - Environment Setup Script for Debian/Kali-style Linux
# This script installs the bot venv and OSINT tool venvs used by bot.py.

set -euo pipefail

echo "================================================"
echo "  OSINT Discord Bot - Environment Setup"
echo "  Host OS: Debian/Kali-style Linux"
echo "================================================"
echo ""

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BOT_DIR="$SCRIPT_DIR"
TOOLS_DIR="$SCRIPT_DIR/osint-tools"

if command -v apt >/dev/null 2>&1; then
  echo "[1/9] Updating package metadata..."
  sudo apt update

  echo ""
  echo "[2/9] Installing system dependencies..."
  sudo apt install -y \
      python3 \
      python3-pip \
      python3-venv \
      git \
      curl
else
  echo "[WARN] apt was not found. Skipping system package installation."
  echo "[WARN] Make sure python3, python3-venv, pip, git, and curl are installed."
fi

echo ""
echo "[3/9] Creating directory structure..."
mkdir -p "$BOT_DIR"
mkdir -p "$TOOLS_DIR"

setup_python_tool_dir() {
  local label="$1"
  local dir_name="$2"
  local venv_name="$3"
  shift 3

  echo ""
  echo "  - Setting up $label..."
  mkdir -p "$TOOLS_DIR/$dir_name"
  cd "$TOOLS_DIR/$dir_name"
  python3 -m venv "$venv_name"
  # shellcheck disable=SC1090
  source "$venv_name/bin/activate"
  python -m pip install --upgrade pip
  python -m pip install "$@" certifi
  deactivate
}

clone_or_update() {
  local repo_url="$1"
  local target_dir="$2"

  cd "$TOOLS_DIR"
  if [ -d "$target_dir/.git" ]; then
    git -C "$target_dir" reset --hard || true
    git -C "$target_dir" pull --ff-only || true
  elif [ -d "$target_dir" ]; then
    echo "[WARN] $TOOLS_DIR/$target_dir exists but is not a git checkout; leaving it in place."
  else
    git clone "$repo_url" "$target_dir"
  fi
}

echo ""
echo "[4/9] Installing OSINT tools..."

setup_python_tool_dir "Sherlock" "sherlock" "sherlockvenv" sherlock-project
source "$TOOLS_DIR/sherlock/sherlockvenv/bin/activate"
python -m pip install --force-reinstall "$BOT_DIR/tool_shims"
deactivate

clone_or_update "https://github.com/OSINTI4L/cupidcr4wl" "cupidcr4wl"
echo ""
echo "  - Setting up cupidcr4wl..."
cd "$TOOLS_DIR/cupidcr4wl"
python3 -m venv cupidcr4wlvenv
source cupidcr4wlvenv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install --upgrade certifi
deactivate

clone_or_update "https://github.com/p1ngul1n0/blackbird" "blackbird"
echo ""
echo "  - Setting up blackbird..."
cd "$TOOLS_DIR/blackbird"
python3 -m venv blackbirdvenv
source blackbirdvenv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install --upgrade certifi
deactivate

setup_python_tool_dir "holehe" "holehe" "holehevenv" holehe
source "$TOOLS_DIR/holehe/holehevenv/bin/activate"
python -m pip install --force-reinstall "$BOT_DIR/tool_shims"
deactivate

clone_or_update "https://github.com/mishakorzik/UserFinder" "user-scanner"
echo ""
echo "  - Setting up user-scanner..."
cd "$TOOLS_DIR/user-scanner"
python3 -m venv userscannervenv
source userscannervenv/bin/activate
python -m pip install --upgrade pip
python -m pip install user-scanner certifi
python -m pip install --force-reinstall "$BOT_DIR/tool_shims"
deactivate

setup_python_tool_dir "whois" "whois" "whoisvenv" python-whois
setup_python_tool_dir "theHarvester" "theHarvester" "theharvestervenv" theHarvester
setup_python_tool_dir "Sublist3r" "sublist3r" "sublist3rvenv" sublist3r

echo ""
echo "[5/9] Setting up Discord bot virtual environment..."
cd "$BOT_DIR"
python3 -m venv discordbotvenv
source discordbotvenv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
deactivate
chmod +x "$BOT_DIR/run_bot.sh" || true

echo ""
echo "[6/9] Installing Blackbird wrapper..."
"$BOT_DIR/discordbotvenv/bin/python" "$BOT_DIR/patch_blackbird.py"

echo ""
echo "[7/9] Installing child-process SSL patch..."
"$BOT_DIR/discordbotvenv/bin/python" "$BOT_DIR/install_tool_ssl_patch.py"

echo ""
echo "[8/9] Verifying tool shim entrypoints..."
"$TOOLS_DIR/sherlock/sherlockvenv/bin/sherlock" test --timeout 3 >/dev/null 2>&1 || true
"$TOOLS_DIR/holehe/holehevenv/bin/holehe" test@example.com --timeout 3 >/dev/null 2>&1 || true
"$TOOLS_DIR/user-scanner/userscannervenv/bin/user-scanner" -u test --timeout 3 >/dev/null 2>&1 || true

echo ""
echo "[9/9] Creating systemd service for Discord bot..."

if command -v systemctl >/dev/null 2>&1; then
  sudo tee /etc/systemd/system/osint-bot.service > /dev/null << EOF
[Unit]
Description=OSINT Discord Bot
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$BOT_DIR
Environment="PATH=/home/$USER/.local/bin:/usr/local/bin:/usr/bin:/bin"
ExecStart=$BOT_DIR/discordbotvenv/bin/python $BOT_DIR/bot.py
Restart=always
RestartSec=10
StandardOutput=append:$BOT_DIR/osintbot.log
StandardError=append:$BOT_DIR/osintbot.log

[Install]
WantedBy=multi-user.target
EOF

  sudo systemctl daemon-reload
  sudo systemctl enable osint-bot.service
  echo "✅ Systemd service created and enabled"
  echo "   Service will auto-start on boot after you configure the bot"
else
  echo "[WARN] systemctl was not found. Skipping systemd service creation."
fi

echo ""
echo "================================================"
echo "✅ Setup Complete!"
echo "================================================"
echo ""
echo "📁 Directory Structure Created:"
echo "   $BOT_DIR/discordbotvenv/        (Discord.py environment)"
echo "   $TOOLS_DIR/sherlock/            (Sherlock + venv + OSINTbot shim)"
echo "   $TOOLS_DIR/cupidcr4wl/          (cupidcr4wl + venv)"
echo "   $TOOLS_DIR/blackbird/           (blackbird + venv + OSINTbot wrapper)"
echo "   $TOOLS_DIR/holehe/              (holehe + venv + OSINTbot shim)"
echo "   $TOOLS_DIR/user-scanner/        (user-scanner + venv + OSINTbot shim)"
echo ""
echo "⚙️  Next Steps:"
echo "   1. Edit config.json and set BOT_TOKEN"
echo "   2. Test the bot manually first:"
echo "      cd $BOT_DIR"
echo "      ./run_bot.sh"
echo ""
echo "   3. Once working, start the systemd service:"
echo "      sudo systemctl start osint-bot"
echo "      sudo systemctl status osint-bot"
echo ""
echo "📊 Useful Commands:"
echo "   sudo systemctl start osint-bot    # Start bot"
echo "   sudo systemctl stop osint-bot     # Stop bot"
echo "   sudo systemctl restart osint-bot  # Restart bot"
echo "   sudo systemctl status osint-bot   # Check status"
echo "   tail -f $BOT_DIR/osintbot.log     # View logs"
echo ""
echo "================================================"
