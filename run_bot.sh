#!/usr/bin/env sh
set -eu
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
cd "$SCRIPT_DIR"
if [ -x "discordbotvenv/bin/python" ]; then
    exec discordbotvenv/bin/python -m osintbot
fi
exec python3 -m osintbot
