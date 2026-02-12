# OSINT Discord Bot - Setup Guide

A Discord bot that provides OSINT (Open Source Intelligence) tools through direct messages. Users can search for usernames, emails, phone numbers, and domains across multiple platforms.

## Features

**Username Search:**
- Sherlock - Multi-platform username search
- Blackbird - Username enumeration
- cupidcr4wl - Adult platform search
- Breaches - COMB database lookup
- InfoStealer - Infostealer log search
- user-scanner - Cross-platform scanner

**Email Search:**
- Blackbird - Email platform search
- Holehe - Email registration checker
- Breaches - COMB database lookup
- InfoStealer - Infostealer log search
- user-scanner - Email scanner

**Phone Search:**
- cupidcr4wl - Adult platform phone search

**Website/Domain:**
- Whois - Domain registration info
- theHarvester - Email/subdomain harvesting
- Sublist3r - Subdomain enumeration

---

## Prerequisites

- **VPS or dedicated server** running Kali Linux
- **Discord account** with server admin permissions

---

## Part 1: Create Discord Bot

### 1. Go to Discord Developer Portal
Visit: https://discord.com/developers/applications

### 2. Create New Application
- Click **"New Application"**
- Name it (e.g., "BOTINT")
- Click **"Create"**

### 3. Configure Bot
- Go to **"Bot"** tab in left sidebar
- Click **"Add Bot"** → Confirm
- **Important Settings:**
  - ✅ Enable **"MESSAGE CONTENT INTENT"** (under Privileged Gateway Intents)
  - Click **"Reset Token"** and copy the token — you'll need this later
  - ⚠️ **Save this token securely** — you can't see it again

### 4. Invite Bot to Your Server
- Go to **"OAuth2"** → **"URL Generator"**
- Select scopes:
  - ✅ `bot`
- Select permissions:
  - ✅ Send Messages
  - ✅ Read Message History
- Copy the generated URL at the bottom
- Paste URL in browser and select your server
- Authorize the bot

### 5. Get Channel ID
- In Discord, go to **Settings** → **Advanced** → Enable **"Developer Mode"**
- Create a private channel for admin logs (e.g., "logs")
- Right-click the channel → **"Copy Channel ID"**
- Save this ID

### 6. Get Your User ID
- Right-click your username anywhere in Discord
- Click **"Copy User ID"**
- Save this ID

---

## Part 2: VPS Setup

### 1. Connect to Your VPS
```bash
ssh user@your-vps-ip
```
Replace `user` with your actual username on the VPS.

### 2. Create Setup Script
```bash
nano ~/setup.sh
```
Paste the entire `setup.sh` script content, then save with `Ctrl+O`, `Enter`, `Ctrl+X`

Make it executable:
```bash
chmod +x setup.sh
```

### 3. Run Setup Script
```bash
./setup.sh
```

This will:
- Update system packages
- Install all dependencies
- Clone and set up OSINT tools
- Create systemd service
- Prompt for reboot

**Choose to reboot when prompted**

---

## Part 3: Configure Bot

### 1. Create Bot Script
After reboot, SSH back in:
```bash
nano ~/discord-bot/osint_bot.py
```
Paste the entire `osint_bot.py` script content, then save with `Ctrl+O`, `Enter`, `Ctrl+X`

### 2. Edit Configuration
```bash
nano ~/discord-bot/osint_bot.py
```

Update these three lines at the top:
```python
BOT_TOKEN = 'YOUR_BOT_TOKEN_HERE'           # Paste Discord bot token
ADMIN_CHANNEL_ID = 123456789                # Paste channel ID (numbers only)
ADMIN_USER_ID = 123456789                   # Paste your user ID (numbers only)
```

Save: `Ctrl+O` → `Enter` → `Ctrl+X`

### 3. Test the Bot Manually
```bash
cd ~/discord-bot
source discordbotvenv/bin/activate
python osint_bot.py
```

You should see:
```
Bot is online as [BotName]
Monitoring DMs and logging to channel: [ChannelID]
```

**Test it:**
- Send a DM to your bot on Discord
- Type `!help`
- You should get the welcome message

If it works, press `Ctrl+C` to stop the bot.

---

## Part 4: Start Bot as Service

### 1. Enable and Start Service
```bash
sudo systemctl start osint-bot
sudo systemctl status osint-bot
```

You should see `active (running)` in green.

### 2. View Logs
```bash
tail -f ~/discord-bot/bot.log
```

Press `Ctrl+C` to exit log view.

---

## Usage

### Commands

All commands are used via **DM (Direct Message)** to the bot.

**Username Search:**
```
!sherlock username
!blackbird-username username
!cupidcr4wl-username username
!breaches username
!infostealer-username username
!user-scanner-username username
```

**Email Search:**
```
!blackbird-email email@example.com
!holehe email@example.com
!breaches email@example.com
!infostealer-email email@example.com
!user-scanner-email email@example.com
```

**Phone Search:**
```
!cupidcr4wl-phone +1234567890
```

**Domain Search:**
```
!whois example.com
!theharvester example.com
!sublist3r example.com
```

**Help:**
```
!help
```

---

## Maintenance

### Update All Tools
Create the update script:
```bash
nano ~/update_tools.sh
```
Paste the entire `update_tools.sh` script content, then save with `Ctrl+O`, `Enter`, `Ctrl+X`

Make it executable and run:
```bash
chmod +x update_tools.sh
./update_tools.sh
```

### Manual Tool Updates

**Sherlock:**
```bash
pipx upgrade sherlock-project
```

**cupidcr4wl:**
```bash
cd ~/osint-tools/cupidcr4wl
git pull
source cupidcr4wlvenv/bin/activate
pip install --upgrade -r requirements.txt
deactivate
```

**blackbird:**
```bash
cd ~/osint-tools/blackbird
git pull
source blackbirdvenv/bin/activate
pip install --upgrade -r requirements.txt
deactivate
```

**holehe:**
```bash
cd ~/osint-tools/holehe
source holehevenv/bin/activate
pip install --upgrade holehe
deactivate
```

**user-scanner:**
```bash
cd ~/osint-tools/user-scanner
source userscannervenv/bin/activate
pip install --upgrade user-scanner
deactivate
```

After updating, restart the bot:
```bash
sudo systemctl restart osint-bot
```

### Useful Commands

**Start bot:**
```bash
sudo systemctl start osint-bot
```

**Stop bot:**
```bash
sudo systemctl stop osint-bot
```

**Restart bot:**
```bash
sudo systemctl restart osint-bot
```

**Check status:**
```bash
sudo systemctl status osint-bot
```

**View live logs:**
```bash
tail -f ~/discord-bot/bot.log
```

**View all logs:**
```bash
cat ~/discord-bot/bot.log
```

---

## Troubleshooting

### Bot won't start
```bash
sudo systemctl status osint-bot
cat ~/discord-bot/bot.log
```

Common issues:
- **Invalid token** - Double-check `BOT_TOKEN` in `osint_bot.py`
- **Missing permissions** - Ensure MESSAGE CONTENT INTENT is enabled
- **Module not found** - Rerun: `cd ~/discord-bot && source discordbotvenv/bin/activate && pip install discord.py requests`

### Bot doesn't respond to DMs
- Make sure you're DMing the bot, not messaging it in a server
- Check admin log channel for errors
- Verify bot is online (green dot in Discord)

### Tools timing out
- Some tools can take 5-10 minutes on large searches
- If using VPN, this can add latency
- Check `~/discord-bot/bot.log` for actual errors

### Admin logs not showing
- Verify `ADMIN_CHANNEL_ID` is correct (right-click channel → Copy ID)
- Make sure bot has permissions in that channel
- Bot must be added to the server where the admin channel exists


