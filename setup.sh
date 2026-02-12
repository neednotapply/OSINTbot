#!/bin/bash

# OSINT Discord Bot - Environment Setup Script for Kali Linux
# This script installs all dependencies and OSINT tools

set -e  # Exit on any error

echo "================================================"
echo "  OSINT Discord Bot - Environment Setup"
echo "  Host OS: Kali Linux"
echo "================================================"
echo ""

echo "[1/5] Updating system packages..."
sudo apt update
sudo apt dist-upgrade -y

echo ""
echo "[2/5] Installing dependencies..."
sudo apt install -y \
    python3 \
    python3-pip \
    python3-venv \
    git \
    curl

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BOT_DIR="$SCRIPT_DIR"
TOOLS_DIR="$SCRIPT_DIR/osint-tools"

echo ""
echo "[3/5] Creating directory structure..."
mkdir -p "$BOT_DIR"
mkdir -p "$TOOLS_DIR"

echo ""
echo "[4/5] Installing OSINT tools..."

echo ""
echo "  [4a] Installing Sherlock..."
mkdir -p "$TOOLS_DIR/sherlock"
cd "$TOOLS_DIR/sherlock"
python3 -m venv sherlockvenv
source sherlockvenv/bin/activate
python -m pip install --upgrade pip
python -m pip install sherlock-project
deactivate

echo ""
echo "  [4b] Cloning and setting up cupidcr4wl..."
cd "$TOOLS_DIR"
git clone https://github.com/OSINTI4L/cupidcr4wl
cd cupidcr4wl
python3 -m venv cupidcr4wlvenv
source cupidcr4wlvenv/bin/activate
python -m pip install -r requirements.txt
deactivate

echo ""
echo "  [4c] Cloning and setting up blackbird..."
cd "$TOOLS_DIR" || exit
git clone https://github.com/p1ngul1n0/blackbird
cd blackbird || exit
python3 -m venv blackbirdvenv
source blackbirdvenv/bin/activate
python -m pip install -r requirements.txt
deactivate

echo ""
echo "  [4d] Setting up holehe..."
cd "$TOOLS_DIR" || exit
mkdir holehe && cd holehe
python3 -m venv holehevenv
source holehevenv/bin/activate
python -m pip install holehe
deactivate



echo ""
echo "  [4f] Setting up whois in virtualenv..."
cd "$TOOLS_DIR" || exit
mkdir -p whois && cd whois
python3 -m venv whoisvenv
source whoisvenv/bin/activate
python -m pip install python-whois
deactivate

echo ""
echo "  [4g] Setting up theHarvester in virtualenv..."
cd "$TOOLS_DIR" || exit
mkdir -p theHarvester && cd theHarvester
python3 -m venv theharvestervenv
source theharvestervenv/bin/activate
python -m pip install theHarvester
deactivate

echo ""
echo "  [4h] Setting up Sublist3r in virtualenv..."
cd "$TOOLS_DIR" || exit
mkdir -p sublist3r && cd sublist3r
python3 -m venv sublist3rvenv
source sublist3rvenv/bin/activate
python -m pip install sublist3r
deactivate

echo ""
echo "[5/5] Setting up Discord bot virtual environment..."
cd "$BOT_DIR"
python3 -m venv discordbotvenv
source discordbotvenv/bin/activate
python -m pip install discord.py requests
deactivate

echo ""
echo "[6/6] Creating systemd service for Discord bot..."

# Create systemd service file
sudo tee /etc/systemd/system/osint-bot.service > /dev/null << EOF
[Unit]
Description=OSINT Discord Bot
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$BOT_DIR
Environment="PATH=/home/$USER/.local/bin:/usr/local/bin:/usr/bin:/bin"
ExecStart=$BOT_DIR/discordbotvenv/bin/python $BOT_DIR/osint_bot.py
Restart=always
RestartSec=10
StandardOutput=append:$BOT_DIR/bot.log
StandardError=append:$BOT_DIR/bot.log

[Install]
WantedBy=multi-user.target
EOF

# Reload systemd and enable (but don't start yet - user needs to configure first)
sudo systemctl daemon-reload
sudo systemctl enable osint-bot.service

echo "✅ Systemd service created and enabled"
echo "   Service will auto-start on boot after you configure the bot"

echo ""
echo "================================================"
echo "✅ Setup Complete!"
echo "================================================"
echo ""
echo "📁 Directory Structure Created:"
echo "   $BOT_DIR/discordbotvenv/        (Discord.py environment)"
echo "   $TOOLS_DIR/sherlock/            (Sherlock + venv)"
echo "   $TOOLS_DIR/cupidcr4wl/          (cupidcr4wl + venv)"
echo "   $TOOLS_DIR/blackbird/           (blackbird + venv)"
echo "   $TOOLS_DIR/holehe/              (holehe + venv)"
echo ""
echo "⚙️  Next Steps:"
echo "   1. Add your bot script to $BOT_DIR/osint_bot.py"
echo "   2. Edit and configure:"
echo "      nano $BOT_DIR/osint_bot.py"
echo "      - Update config.json (BOT_TOKEN)"
echo "      - Update config.json (ADMIN_CHANNEL_ID)"
echo "      - Update config.json (ADMIN_USER_ID)"
echo ""
echo "   3. Test the bot manually first:"
echo "      cd $BOT_DIR"
echo "      source discordbotvenv/bin/activate"
echo "      python osint_bot.py"
echo ""
echo "   4. Once working, start the systemd service:"
echo "      sudo systemctl start osint-bot"
echo "      sudo systemctl status osint-bot"
echo ""
echo "📊 Useful Commands:"
echo "   sudo systemctl start osint-bot    # Start bot"
echo "   sudo systemctl stop osint-bot     # Stop bot"
echo "   sudo systemctl restart osint-bot  # Restart bot"
echo "   sudo systemctl status osint-bot   # Check status"
echo "   tail -f $BOT_DIR/bot.log          # View logs"
echo ""
echo "================================================"
