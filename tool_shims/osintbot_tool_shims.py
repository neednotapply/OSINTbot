"""Fallback command shims for OSINTbot-managed tool venvs.

These are intentionally small username/email checkers used when upstream Windows
console entrypoints are brittle or mismatched. They emit formats that bot.py
already knows how to parse.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import sys
import urllib.parse

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


if __name__ == '__main__':
    # Running this module directly defaults to the user-scanner style interface.
    raise SystemExit(user_scanner_main())
