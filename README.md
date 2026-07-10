# OSINT Discord Bot

OSINTbot runs several locally installed OSINT sources from one Discord slash
command, consolidates duplicate findings, and reports the status of every source.
Windows and Linux are first-class platforms; macOS is best effort.

The available commands are:

- `/osint` — search by Username, Email, Phone, or Domain.
- `/osint-status` — diagnose installed sources, optionally by category.
- `/help` — show supported categories and sources.

Results are visible in the channel where the command is invoked. Anyone with
Discord permission to invoke the command can use it.

## Sources

- Username: Sherlock, Blackbird, cupidcr4wl, COMB, HudsonRock Intel, user-scanner
- Email: Blackbird, Holehe, COMB, HudsonRock Intel, user-scanner
- Phone: cupidcr4wl
- Domain: WHOIS, DNS Probe, Sublist3r

## Installation

Python 3.11 or newer and Git are required. The setup launchers create the bot
environment and install known-good tool versions from
`osintbot/tool_manifest.json`.

Windows:

```bat
setup.bat
```

Linux:

```sh
chmod +x setup.sh run_bot.sh update_tools.sh
./setup.sh
```

Setup and updates are idempotent. Git-based tool checkouts are pinned to exact
commits, and maintenance refuses to overwrite a dirty checkout. It never resets
application source.

## Configuration

Set the token through the environment whenever possible:

```bat
set OSINTBOT_TOKEN=your-token
run_bot.bat
```

```sh
OSINTBOT_TOKEN=your-token ./run_bot.sh
```

An ignored `config.json` based on `example.config.json` remains supported for
backward compatibility. Environment values take precedence.

| Variable | Default | Purpose |
| --- | ---: | --- |
| `OSINTBOT_TOKEN` | required | Discord bot token |
| `OSINTBOT_TOOLS_DIR` | `./osint-tools` | Local tool installations |
| `OSINTBOT_LOG_LEVEL` | `INFO` | DEBUG, INFO, WARNING, ERROR, or CRITICAL |
| `OSINTBOT_LOG_PATH` | `./osintbot.log` | Rotating log location |
| `OSINTBOT_MAX_CONCURRENCY` | `3` | Simultaneous source runners |
| `OSINTBOT_SEARCH_DEADLINE` | `600` | Overall search deadline in seconds |
| `OSINTBOT_DEBUG_DATA_LOGGING` | `false` | Include raw queries and shortened output at DEBUG |

At INFO, logs contain request IDs, user IDs, categories, durations, statuses,
and counts—not raw queries or findings. Enabling both DEBUG log level and debug
data logging writes sensitive search data to disk. Protect and rotate those logs.

## Running and diagnostics

Use `run_bot.bat` or `./run_bot.sh`. `bot.py` remains a compatibility launcher;
the canonical entry point is:

```sh
python -m osintbot
```

Maintenance commands are shared across platforms:

```sh
python -m osintbot.maintenance install
python -m osintbot.maintenance update
python -m osintbot.maintenance doctor
python -m osintbot.maintenance verify
```

On Linux, `python -m osintbot.maintenance service` prints a systemd unit for
explicit administrator review and installation. Setup does not install or start
a service automatically.

## Development

```sh
python -m pip install -e ".[dev]"
python -m pytest
python -m ruff check osintbot tests
python -m mypy osintbot/config.py osintbot/models.py osintbot/orchestration.py osintbot/process.py osintbot/maintenance.py
```

CI runs these checks and a package build on Python 3.11 and 3.12 for Windows and
Linux. See `docs/ARCHITECTURE.md` for adding adapters and
`docs/MAINTENANCE.md` for the release/update checklist.

## Upstream and responsible use

The original bot was created by [OSINTI4L](https://github.com/OSINTI4L); this
repository contains a modified version. Use OSINTbot only where you have lawful
authority, follow source terms, and remember that channel-visible results and
DEBUG logs can contain personal information.
