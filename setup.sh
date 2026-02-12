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
    pipx \
    curl

# Ensure pipx is in PATH
pipx ensurepath
export PATH="$HOME/.local/bin:$PATH"

echo ""
echo "[3/5] Creating directory structure..."
mkdir -p ~/discord-bot
mkdir -p ~/osint-tools

echo ""
echo "[4/5] Installing OSINT tools..."

echo ""
echo "  [4a] Installing Sherlock via pipx..."
pipx install sherlock-project

echo ""
echo "  [4b] Cloning and setting up cupidcr4wl..."
cd ~/osint-tools
git clone https://github.com/OSINTI4L/cupidcr4wl
cd cupidcr4wl
python3 -m venv cupidcr4wlvenv
source cupidcr4wlvenv/bin/activate
pip install -r requirements.txt
deactivate

echo ""
echo "  [4c] Cloning and setting up blackbird..."
cd ~/osint-tools || exit
git clone https://github.com/p1ngul1n0/blackbird
cd blackbird || exit
python3 -m venv blackbirdvenv
source blackbirdvenv/bin/activate
pip install -r requirements.txt
deactivate

echo ""
echo "  [4d] Setting up holehe..."
cd ~/osint-tools || exit
mkdir holehe && cd holehe
python3 -m venv holehevenv
source holehevenv/bin/activate
pip3 install holehe
deactivate

echo ""
echo "[5/5] Setting up Discord bot virtual environment..."
cd ~/discord-bot
python3 -m venv discordbotvenv
source discordbotvenv/bin/activate
pip install discord.py requests
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
WorkingDirectory=/home/$USER/discord-bot
Environment="PATH=/home/$USER/.local/bin:/usr/local/bin:/usr/bin:/bin"
ExecStart=/home/$USER/discord-bot/discordbotvenv/bin/python /home/$USER/discord-bot/osint_bot.py
Restart=always
RestartSec=10
StandardOutput=append:/home/$USER/discord-bot/bot.log
StandardError=append:/home/$USER/discord-bot/bot.log

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
echo "   ~/discord-bot/discordbotvenv/  (Discord.py environment)"
echo "   ~/osint-tools/cupidcr4wl/      (cupidcr4wl + venv)"
echo "   ~/osint-tools/blackbird/       (blackbird + venv)"
echo "   ~/osint-tools/holehe/          (holehe + venv)"
echo "   ~/.local/bin/sherlock          (Sherlock via pipx)"
echo ""
echo "⚙️  Next Steps:"
echo "   1. Add your bot script to ~/discord-bot/osint_bot.py"
echo "   2. Edit and configure:"
echo "      nano ~/discord-bot/osint_bot.py"
echo "      - Set BOT_TOKEN"
echo "      - Set ADMIN_CHANNEL_ID"
echo "      - Set ADMIN_USER_ID"
echo ""
echo "   3. Test the bot manually first:"
echo "      cd ~/discord-bot"
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
echo "   tail -f ~/discord-bot/bot.log     # View logs"
echo ""
echo "================================================"
