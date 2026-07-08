"""Cross-platform launcher for OSINTbot.

This wrapper makes startup deterministic before bot.py imports discord.py/aiohttp.
It imports sitecustomize explicitly so SSL compatibility patches are installed even
when Python does not auto-import sitecustomize from the current directory.
"""

from __future__ import annotations

import os
import runpy
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BOT_PATH = os.path.join(BASE_DIR, 'bot.py')

# Make repo-local helper modules importable even when launched from another cwd.
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

# Force-load repo startup hooks before bot.py imports discord/aiohttp.
try:
    import sitecustomize  # noqa: F401
except Exception as exc:
    print(f'[OSINTbot] Warning: failed to import sitecustomize.py: {exc}', file=sys.stderr)

if not os.path.exists(BOT_PATH):
    print(f'[OSINTbot] ERROR: bot.py not found at {BOT_PATH}', file=sys.stderr)
    raise SystemExit(1)

runpy.run_path(BOT_PATH, run_name='__main__')
