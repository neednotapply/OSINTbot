#!/bin/bash

# OSINT Discord Bot - Tool Update Script
# Updates all OSINT tools to their latest versions

set -e  # Exit on any error

echo "================================================"
echo "  OSINT Tool Update Script"
echo "================================================"
echo ""

# Stop the bot before updating
echo "[0/7] Stopping Discord bot..."
sudo systemctl stop osint-bot 2>/dev/null && echo "✅ Bot stopped" || echo "ℹ️  Bot was not running"
echo ""

echo "[1/7] Updating Sherlock..."
pipx upgrade sherlock-project
echo "✅ Sherlock updated"
echo ""

echo "[2/7] Updating cupidcr4wl..."
cd ~/osint-tools/cupidcr4wl || exit
git pull origin main
source cupidcr4wlvenv/bin/activate
pip install --upgrade -r requirements.txt
deactivate
echo "✅ cupidcr4wl updated"
echo ""

echo "[3/7] Updating blackbird..."
cd ~/osint-tools/blackbird || exit
git pull origin main
source blackbirdvenv/bin/activate
pip install --upgrade -r requirements.txt
deactivate
echo "✅ blackbird updated"
echo ""

echo "[4/7] Updating holehe..."
cd ~/osint-tools/holehe || exit
source holehevenv/bin/activate
pip install --upgrade holehe
deactivate
echo "✅ holehe updated"
echo ""

echo "[5/7] Updating user-scanner..."
cd ~/osint-tools/user-scanner || exit
source userscannervenv/bin/activate
pip install --upgrade user-scanner
deactivate
echo "✅ user-scanner updated"
echo ""

echo "[6/7] Updating system tools (whois, theHarvester, sublist3r)..."
sudo apt update
sudo apt upgrade -y whois sublist3r theHarvester
echo "✅ System tools updated"
echo ""

echo "[7/7] Updating Discord bot dependencies..."
cd ~/discord-bot || exit
source discordbotvenv/bin/activate
pip install --upgrade discord.py requests
deactivate
echo "✅ Bot dependencies updated"
echo ""

echo "================================================"
echo "✅ All tools updated successfully!"
echo "================================================"
echo ""
echo "Restart the bot:"
echo "  sudo systemctl start osint-bot"
echo "  sudo systemctl status osint-bot"
echo ""
