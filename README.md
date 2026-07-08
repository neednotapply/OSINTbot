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
python bot.py
```

#### Windows
```bat
cd /d C:\path\to\OSINTbot
run_bot.bat
```

Or run the venv interpreter directly:
```bat
discordbotvenv\Scripts\python.exe bot.py
```

Do not use bare `py bot.py` unless you intentionally want to use the global Python environment instead of the repo virtual environment.

## Windows SSL note

If Python crashes during `import discord` with:

```text
ssl.SSLError: [ASN1] nested asn1 error
```

that usually means Python hit a malformed certificate while loading the Windows certificate store. The repository includes `sitecustomize.py`, which Python imports before `bot.py`; it retries SSL context creation with the `certifi` CA bundle so `discord.py` / `aiohttp` can finish importing.

The workaround is not a substitute for eventually cleaning the bad certificate from Windows, but it should get the bot running.

## Logging

The bot writes detailed execution logs to both stdout and `osintbot.log` (rotated at ~2MB with 3 backups).

- Set `OSINTBOT_LOG_LEVEL` to control verbosity (`DEBUG`, `INFO`, `WARNING`, `ERROR`).
- Default level is `INFO`.
- Use `DEBUG` when diagnosing silent failures, parser misses, or tool subprocess issues.

Windows example:
```bat
set OSINTBOT_LOG_LEVEL=DEBUG
run_bot.bat
```

Linux/macOS example:
```bash
OSINTBOT_LOG_LEVEL=DEBUG python bot.py
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
- **Windows import-time SSL crash**: pull the latest repo changes, run `setup.bat`, then use `run_bot.bat` instead of `py bot.py`.
