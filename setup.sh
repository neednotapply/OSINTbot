#!/usr/bin/env sh
set -eu
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
cd "$SCRIPT_DIR"
if [ ! -x "discordbotvenv/bin/python" ]; then
    python3 -m venv discordbotvenv
fi
discordbotvenv/bin/python -m pip install -e .
exec discordbotvenv/bin/python -m osintbot.maintenance install
