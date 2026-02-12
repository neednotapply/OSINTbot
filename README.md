# OSINT Discord Bot

A Discord bot that runs OSINT searches with a single slash command and consolidated results.  
Original bot created by [OSINTI4L](https://github.com/OSINTI4L) (not hosted on GitHub). This repository contains my modified version.

## Commands

- `/osint` — run a search
- `/help` — show search options and coverage

`/osint` prompts for:
- `Search type`: `Username`, `Email`, `Phone`, `Domain`
- `Query`: the value to search

Results are consolidated: if the same finding appears in multiple tools, it is grouped once with all matching sources listed.
Where possible, URL-style findings are sent as clickable Discord hyperlinks.

## Sources

- **Username**: Sherlock, Blackbird, cupidcr4wl, COMB, InfoStealer, user-scanner
- **Email**: Blackbird, Holehe, COMB, InfoStealer, user-scanner
- **Phone**: cupidcr4wl
- **Domain**: whois, theHarvester, Sublist3r

## Quick Start

### 1) Create your Discord bot
Use the official Discord docs for bot setup, intents, and OAuth scopes:
- https://discord.com/developers/docs/quick-start/getting-started
- https://discordpy.readthedocs.io/en/stable/discord.html

Make sure your bot has slash command support (`applications.commands`) and can send messages in channels where it will be used.

### 2) Install dependencies

#### Linux
```bash
chmod +x setup.sh
./setup.sh
```

#### Windows
```bat
setup.bat
```

### 3) Configure the bot
Edit `config.json`:
```json
{
  "BOT_TOKEN": "YOUR_BOT_TOKEN_HERE"
}
```

### 4) Run the bot

#### Linux
```bash
cd /path/to/OSINTbot
source discordbotvenv/bin/activate
python osint_bot.py
```

#### Windows
```bat
cd /d C:\path\to\OSINTbot
discordbotvenv\Scripts\python osint_bot.py
```

## Updating

#### Linux
```bash
chmod +x update_tools.sh
./update_tools.sh
```

#### Windows
```bat
update_tools.bat
```

## Troubleshooting

- **Slash commands not visible**: re-invite bot with `applications.commands` scope.
- **No bot response in server channels**: verify channel permissions (View Channel, Send Messages).
- **Tool errors/timeouts**: check your bot logs and re-run update scripts.
