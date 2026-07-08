#!/usr/bin/env bash

# OSINT Discord Bot - Tool Update Script
# Updates all OSINT tools to their latest versions

set -euo pipefail

echo "================================================"
echo "  OSINT Tool Update Script"
echo "================================================"
echo ""

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BOT_DIR="$SCRIPT_DIR"
TOOLS_DIR="$SCRIPT_DIR/osint-tools"

# Stop the bot before updating
echo "[0/11] Stopping Discord bot..."
sudo systemctl stop osint-bot 2>/dev/null && echo "✅ Bot stopped" || echo "ℹ️  Bot was not running"
echo ""

echo "[1/11] Updating Sherlock..."
cd "$TOOLS_DIR/sherlock" || exit
source sherlockvenv/bin/activate
python -m pip install --upgrade sherlock-project certifi
deactivate
echo "✅ Sherlock updated"
echo ""

echo "[2/11] Updating cupidcr4wl..."
cd "$TOOLS_DIR/cupidcr4wl" || exit
git pull origin main
source cupidcr4wlvenv/bin/activate
python -m pip install --upgrade -r requirements.txt
python -m pip install --upgrade certifi
deactivate
echo "✅ cupidcr4wl updated"
echo ""

echo "[3/11] Updating blackbird..."
cd "$TOOLS_DIR/blackbird" || exit
git pull origin main
source blackbirdvenv/bin/activate
python -m pip install --upgrade -r requirements.txt
python -m pip install --upgrade certifi
deactivate
echo "✅ blackbird updated"
echo ""

echo "[4/11] Updating holehe..."
cd "$TOOLS_DIR/holehe" || exit
source holehevenv/bin/activate
python -m pip install --upgrade holehe certifi
deactivate
echo "✅ holehe updated"
echo ""

echo "[5/11] Updating user-scanner..."
cd "$TOOLS_DIR/user-scanner" || exit
source userscannervenv/bin/activate
python -m pip install --upgrade user-scanner certifi
deactivate
echo "✅ user-scanner updated"
echo ""

echo "[6/11] Updating whois (venv)..."
cd "$TOOLS_DIR/whois" || exit
source whoisvenv/bin/activate
python -m pip install --upgrade python-whois certifi
deactivate
echo "✅ whois updated"
echo ""

echo "[7/11] Updating theHarvester (venv)..."
cd "$TOOLS_DIR/theHarvester" || exit
source theharvestervenv/bin/activate
python -m pip install --upgrade theHarvester certifi
deactivate
echo "✅ theHarvester updated"
echo ""

echo "[8/11] Updating Sublist3r (venv)..."
cd "$TOOLS_DIR/sublist3r" || exit
source sublist3rvenv/bin/activate
python -m pip install --upgrade sublist3r certifi
deactivate
echo "✅ Sublist3r updated"
echo ""

if command -v apt >/dev/null 2>&1; then
  echo "[9/11] Updating system tools (whois, theHarvester, sublist3r)..."
  sudo apt update
  sudo apt upgrade -y whois sublist3r theHarvester || true
  echo "✅ System tool update attempted"
else
  echo "[9/11] apt not found; skipping system package updates."
fi
echo ""

echo "[10/11] Updating Discord bot dependencies..."
cd "$BOT_DIR" || exit
source discordbotvenv/bin/activate
python -m pip install --upgrade -r requirements.txt
deactivate
echo "✅ Bot dependencies updated"
echo ""

echo "[11/11] Installing child-process SSL patch..."
"$BOT_DIR/discordbotvenv/bin/python" "$BOT_DIR/install_tool_ssl_patch.py"
echo "✅ SSL patch installed"
echo ""

echo "================================================"
echo "✅ All tools updated successfully!"
echo "================================================"
echo ""
echo "Restart the bot:"
echo "  sudo systemctl start osint-bot"
echo "  sudo systemctl status osint-bot"
echo ""
