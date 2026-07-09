"""Fallback command shims and maintenance helpers for OSINTbot-managed venvs.

The console entrypoints provide small parser-friendly fallbacks for tools whose
Windows wrappers are brittle. The module CLI also performs setup/update
maintenance that used to live in separate root-level helper scripts.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import shutil
import sys
import urllib.parse
from pathlib import Path

import certifi
import requests

USER_AGENT = 'OSINTbot/1.0 (+https://github.com/neednotapply/OSINTbot)'
DEFAULT_TIMEOUT = 8

USERNAME_SITES = [
    ('GitHub', 'https://github.com/{username}'),
    ('Reddit', 'https://www.reddit.com/user/{username}'),
    ('YouTube', 'https://www.youtube.com/@{username}'),
    ('X', 'https://x.com/{username}'),
    ('Instagram', 'https://www.instagram.com/{username}/'),
    ('TikTok', 'https://www.tiktok.com/@{username}'),
    ('Pinterest', 'https://www.pinterest.com/{username}/'),
    ('SteamCommunity', 'https://steamcommunity.com/id/{username}'),
    ('SoundCloud', 'https://soundcloud.com/{username}'),
    ('Linktree', 'https://linktr.ee/{username}'),
    ('Telegram', 'https://t.me/{username}'),
    ('Tumblr', 'https://www.tumblr.com/{username}'),
    ('DeviantArt', 'https://www.deviantart.com/{username}'),
    ('Medium', 'https://medium.com/@{username}'),
    ('Docker Hub', 'https://hub.docker.com/u/{username}'),
    ('PyPI', 'https://pypi.org/user/{username}/'),
    ('npm', 'https://www.npmjs.com/~{username}'),
    ('Keybase', 'https://keybase.io/{username}'),
    ('Pastebin', 'https://pastebin.com/u/{username}'),
    ('Kaggle', 'https://www.kaggle.com/{username}'),
]

EMAIL_SITES = [
    ('Gravatar', 'https://www.gravatar.com/avatar/{md5}?d=404'),
]

# Raw string is intentional: this content is written verbatim into
# osint-tools/blackbird/blackbird.py. In particular, keep '\n' escaped so the
# generated wrapper contains return '\n'.join(...), not an unterminated literal.
BLACKBIRD_WRAPPER = r'''"""OSINTbot wrapper around upstream Blackbird."""

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

SSL_PATCH_CONTENT = r'''"""OSINTbot child-process SSL compatibility patch."""

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


def http_status(url: str, timeout: int) -> tuple[int | None, str | None]:
    try:
        response = requests.get(
            url,
            headers={'User-Agent': USER_AGENT},
            timeout=timeout,
            allow_redirects=True,
            verify=certifi.where(),
        )
        return response.status_code, response.url
    except requests.RequestException as exc:
        return None, str(exc)


def looks_taken(status: int | None) -> bool:
    if status is None:
        return False
    if status in {404, 410, 451}:
        return False
    return 200 <= status < 500


def check_username_site(site: tuple[str, str], username: str, timeout: int) -> tuple[str, str] | None:
    site_name, template = site
    safe_username = urllib.parse.quote(username, safe='')
    url = template.format(username=safe_username)
    status, final_url = http_status(url, timeout=timeout)
    if looks_taken(status):
        return site_name, final_url if final_url and final_url.startswith('http') else url
    return None


def username_findings(username: str, timeout: int = DEFAULT_TIMEOUT) -> list[tuple[str, str]]:
    findings: list[tuple[str, str]] = []
    workers = min(12, len(USERNAME_SITES))
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
        futures = [executor.submit(check_username_site, site, username, timeout) for site in USERNAME_SITES]
        for future in concurrent.futures.as_completed(futures):
            result = future.result()
            if result:
                findings.append(result)
    return sorted(findings, key=lambda item: item[0].lower())


def email_findings(email: str, timeout: int = DEFAULT_TIMEOUT) -> list[tuple[str, str]]:
    email_l = email.strip().lower()
    digest = hashlib.md5(email_l.encode('utf-8')).hexdigest()
    findings: list[tuple[str, str]] = []
    for site_name, template in EMAIL_SITES:
        url = template.format(md5=digest, email=urllib.parse.quote(email_l, safe=''))
        status, final_url = http_status(url, timeout=timeout)
        if looks_taken(status):
            findings.append((site_name, final_url if final_url and final_url.startswith('http') else url))
    return findings


def email_site_statuses(email: str, timeout: int = DEFAULT_TIMEOUT) -> list[tuple[str, bool]]:
    email_l = email.strip().lower()
    digest = hashlib.md5(email_l.encode('utf-8')).hexdigest()
    statuses: list[tuple[str, bool]] = []
    for site_name, template in EMAIL_SITES:
        url = template.format(md5=digest, email=urllib.parse.quote(email_l, safe=''))
        status, _ = http_status(url, timeout=timeout)
        statuses.append((site_name, looks_taken(status)))
    return statuses


def first_query_arg(argv: list[str]) -> str | None:
    for arg in argv:
        if arg.startswith('-'):
            continue
        return arg
    return None


def sherlock_main() -> int:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('username', nargs='?')
    parser.add_argument('--timeout', type=int, default=DEFAULT_TIMEOUT)
    parser.add_argument('--print-found', action='store_true')
    parser.add_argument('--nsfw', action='store_true')
    parser.add_argument('--no-txt', action='store_true')
    args, extras = parser.parse_known_args()

    username = args.username or first_query_arg(extras)
    if not username:
        print('Usage: sherlock USERNAME [--timeout SECONDS]')
        return 2

    findings = username_findings(username, timeout=args.timeout or DEFAULT_TIMEOUT)
    for site_name, url in findings:
        print(f'{site_name}: {url}')

    return 0


def user_scanner_main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('-u', '--username')
    parser.add_argument('-e', '--email')
    parser.add_argument('--timeout', type=int, default=DEFAULT_TIMEOUT)
    args, _ = parser.parse_known_args()

    if args.username:
        for site_name, url in username_findings(args.username, timeout=args.timeout):
            print(f'[✘] {site_name} ({url}): Taken')
        return 0

    if args.email:
        for site_name, url in email_findings(args.email, timeout=args.timeout):
            print(f'[✘] {site_name} ({url}): Taken')
        return 0

    print('Usage: user-scanner -u USERNAME or -e EMAIL')
    return 2


def holehe_main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('email', nargs='?')
    parser.add_argument('--timeout', type=int, default=DEFAULT_TIMEOUT)
    args, extras = parser.parse_known_args()

    email = args.email or first_query_arg(extras)
    if not email:
        print('Usage: holehe EMAIL [--timeout SECONDS]')
        return 2

    for site_name, is_used in email_site_statuses(email, timeout=args.timeout):
        marker = '+' if is_used else '-'
        print(f'[{marker}] {site_name}')

    return 0


def patch_blackbird(base_dir: Path) -> int:
    blackbird_dir = base_dir / 'osint-tools' / 'blackbird'
    blackbird_main = blackbird_dir / 'blackbird.py'
    blackbird_upstream = blackbird_dir / 'blackbird_upstream.py'

    if not blackbird_main.exists():
        print(f'[SKIP] blackbird.py not found at {blackbird_main}')
        return 0

    current = blackbird_main.read_text(encoding='utf-8', errors='replace')
    if 'OSINTbot wrapper around upstream Blackbird' not in current:
        if blackbird_upstream.exists():
            blackbird_upstream.unlink()
        shutil.copy2(blackbird_main, blackbird_upstream)

    blackbird_main.write_text(BLACKBIRD_WRAPPER, encoding='utf-8')
    print('[OK] Blackbird wrapper installed/refreshed.')
    return 0


def site_packages_dirs(venv_dir: Path) -> list[Path]:
    candidates: list[Path] = []

    windows_site = venv_dir / 'Lib' / 'site-packages'
    if windows_site.exists():
        candidates.append(windows_site)

    unix_lib = venv_dir / 'lib'
    if unix_lib.exists():
        candidates.extend(sorted(unix_lib.glob('python*/site-packages')))

    return candidates


def install_ssl_patch(base_dir: Path) -> int:
    print('Installing OSINTbot SSL patch into tool virtualenvs...')
    failures = 0

    for rel_path in VENV_RELATIVE_PATHS:
        venv_dir = base_dir / rel_path
        if not venv_dir.exists():
            print(f'[SKIP] missing venv: {venv_dir}')
            failures += 1
            continue

        targets = site_packages_dirs(venv_dir)
        if not targets:
            print(f'[SKIP] no site-packages found: {venv_dir}')
            failures += 1
            continue

        for site_dir in targets:
            patch_path = site_dir / 'sitecustomize.py'
            patch_path.write_text(SSL_PATCH_CONTENT, encoding='utf-8')

        print(f'[OK] patched {venv_dir}')

    if failures:
        print(f'Completed with {failures} skipped venv(s). Run setup first for missing tools.')
    else:
        print('SSL patch installed into all expected venvs.')

    return 0


def maintenance_main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description='OSINTbot tool shim maintenance helpers')
    parser.add_argument('--patch-blackbird', action='store_true')
    parser.add_argument('--install-ssl-patch', action='store_true')
    parser.add_argument('base_dir', nargs='?', default='.')
    args = parser.parse_args(argv)

    base_dir = Path(args.base_dir).resolve()
    exit_code = 0

    if args.patch_blackbird:
        exit_code = max(exit_code, patch_blackbird(base_dir))

    if args.install_ssl_patch:
        exit_code = max(exit_code, install_ssl_patch(base_dir))

    if not args.patch_blackbird and not args.install_ssl_patch:
        parser.print_help()
        return 2

    return exit_code


def main() -> int:
    maintenance_flags = {'--patch-blackbird', '--install-ssl-patch'}
    if any(arg in maintenance_flags for arg in sys.argv[1:]):
        return maintenance_main(sys.argv[1:])

    # Running this module directly without maintenance flags defaults to the
    # user-scanner style interface for quick local testing.
    return user_scanner_main()


if __name__ == '__main__':
    raise SystemExit(main())
