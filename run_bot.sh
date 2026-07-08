#!/usr/bin/env sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
cd "$SCRIPT_DIR"

if [ -x "discordbotvenv/bin/python" ]; then
  exec "discordbotvenv/bin/python" bot.py
fi

printf '%s\n' '[WARN] discordbotvenv was not found. Falling back to the active Python on PATH.' >&2
printf '%s\n' '[WARN] For the expected setup, run ./setup.sh first.' >&2

if command -v python3 >/dev/null 2>&1; then
  exec python3 bot.py
fi

if command -v python >/dev/null 2>&1; then
  exec python bot.py
fi

printf '%s\n' '[ERROR] No Python interpreter found. Install Python 3 and re-run.' >&2
exit 1
