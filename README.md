# OSINT Discord Bot

A Discord bot that runs OSINT searches with a single slash command and consolidated results.  
Original bot created by [OSINTI4L](https://github.com/OSINTI4L) (not hosted on GitHub). This repository contains my modified version.

## Commands

- `/osint` — run a search
- `/osint-status` — check local OSINT tool paths and setup status
- `/help` — show search options and coverage

`/osint` prompts for:
- `Search type`: `Username`, `Email`, `Phone`, `Domain`
- `Query`: the value to search

`/osint-status` can check all configured tools or filter by category. Use it when a source is not appearing in results.

Results are consolidated: if the same finding appears in multiple tools, it is grouped once with all matching sources listed.
Where possible, URL-style findings are sent as clickable Discord hyperlinks.
Every `/osint` result includes a **Tool Status** section showing which tools ran, failed, timed out, or returned no parsed findings.

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

#### Linux/macOS/Unix-like shells
```bash
cd /path/to/OSINTbot
chmod +x run_bot.sh
./run_bot.sh
```

Or run the venv interpreter directly:
```bash
discordbotvenv/bin/python bot.py
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

Do not use bare `py bot.py` or bare `python bot.py` unless you intentionally want to use the global Python environment instead of the repo virtual environment.

## Diagnostics

Run this in Discord after the bot starts:

```text
/osint-status
```

Useful filters:

```text
/osint-status search_type:Username
/osint-status search_type:Email
/osint-status search_type:Domain
```

The command reports expected paths under `osint-tools`, missing executables/scripts, and which setup step should repair each missing local tool.

### Parser-friendly fallback shims

`setup.bat`, `update_tools.bat`, `setup.sh`, and `update_tools.sh` install a small local package from `tool_shims/` into the Sherlock, Holehe, and user-scanner venvs. This replaces brittle Windows entrypoints with parser-friendly commands that emit output formats `bot.py` already understands.

Blackbird is patched by the setup/update scripts via `python -m osintbot_tool_shims --patch-blackbird`. The wrapper preserves upstream Blackbird as `blackbird_upstream.py`, adds `--no-update`, filters splash/banner noise, and exits cleanly so parseable stdout is not discarded when Blackbird's update check fails.

### Windows child-process SSL repair

If a child OSINT tool fails with:

```text
ssl.SSLError: [ASN1] nested asn1 error
```

run:

```bat
update_tools.bat
```

That installs/updates `certifi` in each tool venv and runs the consolidated maintenance helper:

```bat
discordbotvenv\Scripts\python.exe -m osintbot_tool_shims --install-ssl-patch "%CD%"
```

The patch writes `sitecustomize.py` into each expected venv's `site-packages` directory so child tools like Blackbird get the same certificate fallback that `bot.py` uses.

## Launchers

- `run_bot.sh` is the Unix launcher for Linux/macOS-style shells. It uses `discordbotvenv/bin/python bot.py` when available, then falls back to `python3` or `python`.
- `run_bot.bat` is the Windows launcher. It uses `discordbotvenv\Scripts\python.exe bot.py` when available, then falls back to `py`.

## Windows SSL note

If Python crashes during `import discord` with:

```text
ssl.SLError: [ASN1] nested asn1 error
```

that usually means Python hit a malformed certificate while loading the Windows certificate store. `bot.py` patches Python SSL before importing `discord.py` / `aiohttp` and retries SSL context creation with the `certifi` CA bundle.

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
OSINTBOT_LOG_LEVEL=DEBUG ./run_bot.sh
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

- **Slash commands not visible**: re-invite bot with `applications.commands` scope, then restart the bot so slash commands sync.
- **No bot response in server channels**: verify channel permissions (View Channel, Send Messages).
- **Only some sources appear**: check the **Tool Status** section in `/osint` output, then run `/osint-status`.
- **Sherlock/Holehe/user-scanner return code 1 with empty output**: run `update_tools.bat` to reinstall the parser-friendly shims.
- **Blackbird exits 1 after printing a banner/update error**: run `update_tools.bat` to reinstall the Blackbird wrapper.
- **Child tool SSL crash**: run `update_tools.bat` so the consolidated maintenance helper patches every tool venv.
- **Tool errors/timeouts**: check your bot logs and re-run update scripts.
- **Windows import-time SSL crash**: pull the latest repo changes, run `discordbotvenv\Scripts\python.exe -m pip install -r requirements.txt`, then use `run_bot.bat` instead of `py bot.py`.
