#!/usr/bin/env sh
set -eu
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
cd "$SCRIPT_DIR"
if [ ! -x "discordbotvenv/bin/python" ]; then
    echo "[ERROR] Run ./setup.sh first." >&2
    exit 1
fi
discordbotvenv/bin/python -m pip install -e .
exec discordbotvenv/bin/python -m osintbot.maintenance update
