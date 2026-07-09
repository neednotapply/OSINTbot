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
export PYTHONPATH="$BOT_DIR/tool_shims${PYTHONPATH:+:$PYTHONPATH}"

# Stop the bot before updating
echo "[0/14] Stopping Discord bot..."
sudo systemctl stop osint-bot 2>/dev/null && echo "✅ Bot stopped" || echo "ℹ️  Bot was not running"
echo ""

echo "[1/14] Updating Sherlock..."
cd "$TOOLS_DIR/sherlock" || exit
source sherlockvenv/bin/activate
python -m pip install --upgrade sherlock-project certifi
python -m pip install --force-reinstall "$BOT_DIR/tool_shims"
deactivate
echo "✅ Sherlock updated"
echo ""

echo "[2/14] Updating cupidcr4wl..."
cd "$TOOLS_DIR/cupidcr4wl" || exit
git pull origin main
source cupidcr4wlvenv/bin/activate
python -m pip install --upgrade -r requirements.txt
python -m pip install --upgrade certifi
deactivate
echo "✅ cupidcr4wl updated"
echo ""

echo "[3/14] Updating blackbird..."
cd "$TOOLS_DIR/blackbird" || exit
git reset --hard
git pull origin main
source blackbirdvenv/bin/activate
python -m pip install --upgrade -r requirements.txt
python -m pip install --upgrade certifi
deactivate
"$BOT_DIR/discordbotvenv/bin/python" -m osintbot_tool_shims --patch-blackbird "$BOT_DIR"
echo "✅ blackbird updated"
echo ""

echo "[4/14] Updating holehe..."
cd "$TOOLS_DIR/holehe" || exit
source holehevenv/bin/activate
python -m pip install --upgrade holehe certifi
python -m pip install --force-reinstall "$BOT_DIR/tool_shims"
deactivate
echo "✅ holehe updated"
echo ""

echo "[5/14] Updating user-scanner..."
cd "$TOOLS_DIR/user-scanner" || exit
source userscannervenv/bin/activate
python -m pip install --upgrade user-scanner certifi
python -m pip install --force-reinstall "$BOT_DIR/tool_shims"
deactivate
echo "✅ user-scanner updated"
echo ""

echo "[6/14] Updating whois (venv)..."
cd "$TOOLS_DIR/whois" || exit
source whoisvenv/bin/activate
python -m pip install --upgrade python-whois certifi
deactivate
echo "✅ whois updated"
echo ""

echo "[7/14] Updating theHarvester (venv)..."
cd "$TOOLS_DIR/theHarvester" || exit
source theharvestervenv/bin/activate
python -m pip install --upgrade theHarvester certifi
deactivate
echo "✅ theHarvester updated"
echo ""

echo "[8/14] Updating Sublist3r (venv)..."
cd "$TOOLS_DIR/sublist3r" || exit
source sublist3rvenv/bin/activate
python -m pip install --upgrade sublist3r certifi
deactivate
echo "✅ Sublist3r updated"
echo ""

if command -v apt >/dev/null 2>&1; then
  echo "[9/14] Updating system tools (whois, theHarvester, sublist3r)..."
  sudo apt update
  sudo apt upgrade -y whois sublist3r theHarvester || true
  echo "✅ System tool update attempted"
else
  echo "[9/14] apt not found; skipping system package updates."
fi
echo ""

echo "[10/14] Updating Discord bot dependencies..."
cd "$BOT_DIR" || exit
source discordbotvenv/bin/activate
python -m pip install --upgrade -r requirements.txt
deactivate
echo "✅ Bot dependencies updated"
echo ""

echo "[11/14] Applying bot parser maintenance patches..."
"$BOT_DIR/discordbotvenv/bin/python" "$BOT_DIR/tool_shims/bot_maintenance.py" "$BOT_DIR"
echo "✅ Bot parser patches applied"
echo ""

echo "[12/14] Re-applying Blackbird wrapper..."
"$BOT_DIR/discordbotvenv/bin/python" -m osintbot_tool_shims --patch-blackbird "$BOT_DIR"
echo "✅ Blackbird wrapper applied"
echo ""

echo "[13/14] Installing child-process SSL patch..."
"$BOT_DIR/discordbotvenv/bin/python" -m osintbot_tool_shims --install-ssl-patch "$BOT_DIR"
echo "✅ SSL patch installed"
echo ""

echo "[14/14] Verifying tool shim entrypoints..."
"$TOOLS_DIR/sherlock/sherlockvenv/bin/sherlock" test --timeout 3 >/dev/null 2>&1 || true
"$TOOLS_DIR/holehe/holehevenv/bin/holehe" test@example.com --timeout 3 >/dev/null 2>&1 || true
"$TOOLS_DIR/user-scanner/userscannervenv/bin/user-scanner" -u test --timeout 3 >/dev/null 2>&1 || true
echo "✅ Shim verification attempted"
echo ""

echo "================================================"
echo "✅ All tools updated successfully!"
echo "================================================"
echo ""
echo "Restart the bot:"
echo "  sudo systemctl start osint-bot"
echo "  sudo systemctl status osint-bot"
echo ""
