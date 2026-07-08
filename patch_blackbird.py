"""Patch local Blackbird checkout for OSINTbot subprocess use.

Blackbird's update check or local JSON state can fail on Windows and return a
non-zero exit code even when useful stdout is produced. OSINTbot parses stdout,
so this wrapper forces --no-update, filters splash/banner noise, and treats
upstream failures as a clean exit while keeping failure detail compact on stderr.
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

import contextlib
import io
import os
import runpy
import sys
import traceback

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

SPLASH_CHARS = set('▄█▓▒░▀▐▌▙▛▜▟▚▞')


def _looks_like_splash(line: str) -> bool:
    stripped = line.strip()
    if not stripped:
        return False
    if 'lucas antoniaci' in stripped.lower():
        return True
    splash_count = sum(1 for ch in stripped if ch in SPLASH_CHARS)
    return splash_count >= max(3, len(stripped) // 6)


def _filter_stdout(text: str) -> str:
    clean_lines = []
    saw_interesting = False
    skipped_prefix = False

    interesting_markers = (
        'downloading site list',
        'sites list is up to date',
        'enumerating accounts',
        'check completed',
        '[+',
        '[-',
        '[!',
        '✔',
        '✅',
        'http://',
        'https://',
    )

    for line in text.splitlines():
        stripped = line.strip()
        lowered = stripped.lower()

        if _looks_like_splash(line):
            skipped_prefix = True
            continue

        if lowered.startswith('⏭') or 'skipping update' in lowered:
            skipped_prefix = True
            continue

        if not saw_interesting:
            if any(marker in lowered for marker in interesting_markers):
                saw_interesting = True
            elif skipped_prefix and not stripped:
                continue
            elif not stripped:
                continue
            else:
                # Drop arbitrary preamble/splash text before Blackbird begins useful output.
                skipped_prefix = True
                continue

        clean_lines.append(line)

    return '\n'.join(clean_lines).strip()


sys.argv[0] = UPSTREAM
_buffer = io.StringIO()
try:
    with contextlib.redirect_stdout(_buffer):
        runpy.run_path(UPSTREAM, run_name='__main__')
except SystemExit as exc:
    filtered = _filter_stdout(_buffer.getvalue())
    if filtered:
        print(filtered)
    if exc.code not in (None, 0):
        print(f'[OSINTbot] Blackbird exited with code {exc.code}; preserving stdout for parser.', file=sys.stderr)
    raise SystemExit(0)
except Exception as exc:
    filtered = _filter_stdout(_buffer.getvalue())
    if filtered:
        print(filtered)
    short_trace = ''.join(traceback.format_exception_only(type(exc), exc)).strip()
    print(f'[OSINTbot] Blackbird suppressed upstream exception: {short_trace}', file=sys.stderr)
    raise SystemExit(0)
else:
    filtered = _filter_stdout(_buffer.getvalue())
    if filtered:
        print(filtered)
'''


def main() -> int:
    if not BLACKBIRD_MAIN.exists():
        print(f'[SKIP] blackbird.py not found at {BLACKBIRD_MAIN}')
        return 0

    current = BLACKBIRD_MAIN.read_text(encoding='utf-8', errors='replace')
    if 'OSINTbot wrapper around upstream Blackbird' in current:
        # Refresh wrapper content in case the wrapper implementation changed.
        BLACKBIRD_MAIN.write_text(WRAPPER, encoding='utf-8')
        print('[OK] Blackbird wrapper refreshed.')
        return 0

    if BLACKBIRD_UPSTREAM.exists():
        BLACKBIRD_UPSTREAM.unlink()

    shutil.copy2(BLACKBIRD_MAIN, BLACKBIRD_UPSTREAM)
    BLACKBIRD_MAIN.write_text(WRAPPER, encoding='utf-8')
    print(f'[OK] Blackbird wrapper installed. Upstream saved as {BLACKBIRD_UPSTREAM}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
