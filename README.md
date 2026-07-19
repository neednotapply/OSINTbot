# OSINT Discord Bot

OSINTbot runs several locally installed OSINT sources from one Discord slash
command, consolidates duplicate findings, and highlights actionable source
problems.
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

## Install, configure, and run

Python 3.11 or newer and Git are required. Clone the repository, then run one
setup command. It creates an isolated environment and installs the pinned
tools from `osintbot/tool_manifest.json`.

Windows (Command Prompt):

```bat
git clone https://github.com/neednotapply/OSINTbot.git
cd OSINTbot
setup.bat
copy example.config.json config.json
notepad config.json
run_bot.bat
```

Linux:

```sh
git clone https://github.com/neednotapply/OSINTbot.git
cd OSINTbot
chmod +x setup.sh run_bot.sh update_tools.sh
./setup.sh
cp example.config.json config.json
${EDITOR:-nano} config.json
./run_bot.sh
```

Set `BOT_TOKEN` in `config.json` before running. The file is ignored by Git.

## Configuration

For deployments, set the token through the environment instead of storing it
in `config.json`:

```bat
set OSINTBOT_TOKEN=your-token
run_bot.bat
```

```sh
OSINTBOT_TOKEN=your-token ./run_bot.sh
```

Environment values take precedence over `config.json`.

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

## Updates and diagnostics

Run updates with `update_tools.bat` on Windows or `./update_tools.sh` on Linux.
Both setup and updates are idempotent. Git-based tool checkouts are pinned to
exact commits, and updates refuse to overwrite a dirty tool checkout. They
never reset application source.

The launchers above are recommended. `bot.py` remains a compatibility launcher;
the module entry point is `python -m osintbot` when using the setup virtual
environment:

```text
Windows: discordbotvenv\Scripts\python.exe -m osintbot
Linux:   discordbotvenv/bin/python -m osintbot
```

Maintenance commands use the same virtual-environment Python:

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
