"""Patch local Blackbird checkout for OSINTbot subprocess use.

Blackbird's update check can fail on Windows and return a non-zero exit code even
when useful stdout is produced. OSINTbot parses stdout, so this wrapper forces
--no-update and treats Blackbird's SystemExit as success so stdout is preserved.
"""

from __future__ import annotations

import shutil
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
BLACKBIRD_DIR = BASE_DIR / 'osint-tools' / 'blackbird'
BLACKBIRD_MAIN = BLACKBIRD_DIR / 'blackbird.py'
BLACKBIRD_UPSTREAM = BLACKBIRD_DIR / 'blackbird_upstream.py'

WRAPPER = '''"""OSINTbot wrapper around upstream Blackbird."""

from __future__ import annotations

import os
import runpy
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPSTREAM = os.path.join(BASE_DIR, 'blackbird_upstream.py')

# Avoid update-check failures from causing empty/failed Discord results.
if '--no-update' not in sys.argv:
    sys.argv.append('--no-update')

# Keep output deterministic for subprocess capture.
os.environ.setdefault('PYTHONUTF8', '1')
os.environ.setdefault('PYTHONIOENCODING', 'utf-8')
os.environ.setdefault('TERM', 'dumb')
os.environ.setdefault('NO_COLOR', '1')

sys.argv[0] = UPSTREAM
try:
    runpy.run_path(UPSTREAM, run_name='__main__')
except SystemExit as exc:
    if exc.code not in (None, 0):
        print(f'[OSINTbot] Blackbird exited with code {exc.code}; preserving stdout for parser.', file=sys.stderr)
    raise SystemExit(0)
'''


def main() -> int:
    if not BLACKBIRD_MAIN.exists():
        print(f'[SKIP] blackbird.py not found at {BLACKBIRD_MAIN}')
        return 0

    current = BLACKBIRD_MAIN.read_text(encoding='utf-8', errors='replace')
    if 'OSINTbot wrapper around upstream Blackbird' in current:
        print('[OK] Blackbird wrapper already installed.')
        return 0

    if BLACKBIRD_UPSTREAM.exists():
        BLACKBIRD_UPSTREAM.unlink()

    shutil.copy2(BLACKBIRD_MAIN, BLACKBIRD_UPSTREAM)
    BLACKBIRD_MAIN.write_text(WRAPPER, encoding='utf-8')
    print(f'[OK] Blackbird wrapper installed. Upstream saved as {BLACKBIRD_UPSTREAM}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
