"""Install OSINTbot's Windows SSL fallback into tool virtualenvs.

Several bundled OSINT tools run as child Python processes. On Windows, those child
processes can hit the same malformed-certificate ASN.1 crash that bot.py works
around before importing discord.py/aiohttp. This script writes a small
sitecustomize.py into each venv's site-packages so the SSL fallback is active
before tools such as Blackbird import aiohttp.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
TOOLS_DIR = BASE_DIR / 'osint-tools'

PATCH_CONTENT = r'''"""OSINTbot child-process SSL compatibility patch."""

import os
import ssl
import sys

_ORIGINAL_CREATE_DEFAULT_CONTEXT = ssl.create_default_context


def _create_default_context_with_certifi_fallback(*args, **kwargs):
    try:
        return _ORIGINAL_CREATE_DEFAULT_CONTEXT(*args, **kwargs)
    except ssl.SSLError as exc:
        message = str(exc).lower()
        if os.name != 'nt' or 'asn1' not in message:
            raise

        try:
            import certifi
        except Exception:
            print(
                '[OSINTbot] Windows certificate store failed to load and certifi '
                'is not installed in this tool venv.',
                file=sys.stderr,
            )
            raise

        patched_kwargs = dict(kwargs)
        if not any(patched_kwargs.get(key) for key in ('cafile', 'capath', 'cadata')):
            patched_kwargs['cafile'] = certifi.where()

        print(
            '[OSINTbot] Warning: Windows certificate store failed to load; '
            'using certifi CA bundle instead.',
            file=sys.stderr,
        )
        return _ORIGINAL_CREATE_DEFAULT_CONTEXT(*args, **patched_kwargs)


ssl.create_default_context = _create_default_context_with_certifi_fallback
'''

VENV_RELATIVE_PATHS = [
    Path('discordbotvenv'),
    Path('osint-tools/sherlock/sherlockvenv'),
    Path('osint-tools/cupidcr4wl/cupidcr4wlvenv'),
    Path('osint-tools/blackbird/blackbirdvenv'),
    Path('osint-tools/holehe/holehevenv'),
    Path('osint-tools/user-scanner/userscannervenv'),
    Path('osint-tools/whois/whoisvenv'),
    Path('osint-tools/theHarvester/theharvestervenv'),
    Path('osint-tools/sublist3r/sublist3rvenv'),
]


def site_packages_dirs(venv_dir: Path) -> list[Path]:
    candidates: list[Path] = []

    windows_site = venv_dir / 'Lib' / 'site-packages'
    if windows_site.exists():
        candidates.append(windows_site)

    unix_lib = venv_dir / 'lib'
    if unix_lib.exists():
        candidates.extend(sorted(unix_lib.glob('python*/site-packages')))

    return candidates


def install_patch(venv_dir: Path) -> tuple[bool, str]:
    if not venv_dir.exists():
        return False, f'missing venv: {venv_dir}'

    targets = site_packages_dirs(venv_dir)
    if not targets:
        return False, f'no site-packages found: {venv_dir}'

    for site_dir in targets:
        patch_path = site_dir / 'sitecustomize.py'
        patch_path.write_text(PATCH_CONTENT, encoding='utf-8')

    return True, f'patched {venv_dir}'


def main() -> int:
    print('Installing OSINTbot SSL patch into tool virtualenvs...')
    failures = 0

    for rel_path in VENV_RELATIVE_PATHS:
        ok, message = install_patch(BASE_DIR / rel_path)
        status = 'OK' if ok else 'SKIP'
        print(f'[{status}] {message}')
        if not ok:
            failures += 1

    if failures:
        print(f'Completed with {failures} skipped venv(s). Run setup first for missing tools.')
    else:
        print('SSL patch installed into all expected venvs.')

    return 0


if __name__ == '__main__':
    raise SystemExit(main())
