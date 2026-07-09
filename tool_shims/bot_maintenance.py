"""Local bot.py maintenance patches applied by setup/update scripts.

This keeps root-level helper scripts out of the repository while still allowing
setup/update to make deterministic compatibility edits to bot.py.
"""

from __future__ import annotations

import argparse
from pathlib import Path

INFOSTEALER_HELPERS = r'''
INFOSTEALER_API_BASE = 'https://cavalier.hudsonrock.com/api/json/v2/osint-tools'
INFOSTEALER_RESULT_KEYS = (
    'stealers', 'results', 'result', 'data', 'records', 'items', 'computers',
    'compromised_machines', 'infected_machines', 'rows'
)
INFOSTEALER_RECORD_KEYS = {
    'computer_name', 'os', 'operating_system', 'ip', 'country', 'city',
    'date_compromised', 'date', 'timestamp', 'email', 'username', 'domain',
    'url', 'credential', 'credentials', 'passwords', 'logins', 'services'
}
INFOSTEALER_SUMMARY_KEYS = [
    'computer_name', 'os', 'operating_system', 'ip', 'country', 'city',
    'date_compromised', 'date', 'timestamp', 'domain', 'url', 'email', 'username'
]


def looks_like_infostealer_record(value):
    if not isinstance(value, dict):
        return False
    keys = {str(key).lower() for key in value.keys()}
    return bool(keys & INFOSTEALER_RECORD_KEYS)


def iter_infostealer_records(value, depth=0):
    if depth > 4:
        return

    if isinstance(value, list):
        for item in value:
            yield from iter_infostealer_records(item, depth + 1)
        return

    if not isinstance(value, dict):
        return

    if looks_like_infostealer_record(value):
        yield value

    for key in INFOSTEALER_RESULT_KEYS:
        nested = value.get(key)
        if nested is not None:
            yield from iter_infostealer_records(nested, depth + 1)


def infostealer_shape_summary(data):
    if isinstance(data, dict):
        keys = ','.join(sorted(str(key) for key in data.keys())[:20])
        return f'dict keys=[{keys}]'
    if isinstance(data, list):
        return f'list len={len(data)}'
    return type(data).__name__


def credential_service_names(record):
    service_names = []
    credentials = record.get('credentials') or record.get('logins') or record.get('passwords') or record.get('services')
    if not isinstance(credentials, list):
        return service_names

    for item in credentials[:10]:
        if not isinstance(item, dict):
            continue
        candidate = item.get('url') or item.get('domain') or item.get('service') or item.get('site')
        if candidate:
            service_names.append(str(candidate))

    return service_names


def format_infostealer_record(index, record):
    pieces = [f'Record {index}']

    for key in INFOSTEALER_SUMMARY_KEYS:
        value = record.get(key)
        if isinstance(value, (str, int, float)) and str(value).strip():
            pieces.append(f'{key}={value}')

    services = credential_service_names(record)
    if services:
        deduped_services = []
        seen = set()
        for service in services:
            marker = service.lower()
            if marker not in seen:
                seen.add(marker)
                deduped_services.append(service)
        pieces.append('services=' + ', '.join(deduped_services[:5]))

    if len(pieces) == 1:
        compact = json.dumps(record, ensure_ascii=False, sort_keys=True)
        pieces.append('raw=' + shorten(compact, limit=240))

    return ' | '.join(pieces)


async def run_infostealer_query(kind, param_name, query):
    loop = asyncio.get_event_loop()
    endpoint = f'{INFOSTEALER_API_BASE}/search-by-{kind}'

    def _request():
        return session.get(endpoint, params={param_name: query}, timeout=20)

    response = await loop.run_in_executor(None, _request)
    logger.info('InfoStealer %s response status=%s query=%s', kind, response.status_code, query)
    if response.status_code != 200:
        return f"API returned status code: {response.status_code}"

    try:
        data = response.json()
    except ValueError as exc:
        logger.warning('InfoStealer %s JSON parse failed query=%s error=%s body=%s', kind, query, exc, shorten(response.text, limit=500))
        return 'Unable to parse InfoStealer API response as JSON.'

    records = list(iter_infostealer_records(data))
    logger.info(
        'InfoStealer %s response shape=%s records=%s query=%s',
        kind,
        infostealer_shape_summary(data),
        len(records),
        query,
    )

    if records:
        return '\n'.join(format_infostealer_record(idx, record) for idx, record in enumerate(records[:100], 1))

    return 'No results found in infostealer databases.'
'''

INFOSTEALER_USERNAME_FUNCTION = r'''
async def run_infostealer_username(username):
    return await run_infostealer_query('username', 'username', username)


'''

INFOSTEALER_EMAIL_FUNCTION = r'''
async def run_infostealer_email(email):
    return await run_infostealer_query('email', 'email', email)


'''


def replace_between(text: str, start_marker: str, end_marker: str, replacement: str) -> tuple[str, bool]:
    start = text.find(start_marker)
    if start == -1:
        return text, False
    end = text.find(end_marker, start)
    if end == -1:
        return text, False
    return text[:start] + replacement + text[end:], True


def patch_cupid_author_false_positive(text: str) -> tuple[str, bool]:
    changed = False

    helper_marker = 'def is_tool_author_url(url):'
    if helper_marker not in text:
        helper = r'''
def is_tool_author_url(url):
    clean = cleanup_url(url).lower().rstrip('/')
    return clean in {
        'https://github.com/osinti4l',
        'http://github.com/osinti4l',
    }


'''
        marker = 'def parse_cupid_finding(raw_clean):'
        if marker in text:
            text = text.replace(marker, helper + marker, 1)
            changed = True

    old = """    if url:\n        # Prefer a label from the URL host over returning a bare URL.\n        return format_url_finding(url)\n"""
    new = """    if url:\n        if is_tool_author_url(url):\n            return None\n        # Prefer a label from the URL host over returning a bare URL.\n        return format_url_finding(url)\n"""
    if old in text and new not in text:
        text = text.replace(old, new, 1)
        changed = True

    return text, changed


def patch_infostealer(text: str) -> tuple[str, bool]:
    changed = False

    if 'INFOSTEALER_API_BASE' not in text:
        marker = 'async def run_infostealer_username(username):'
        if marker in text:
            text = text.replace(marker, INFOSTEALER_HELPERS + '\n\n' + marker, 1)
            changed = True

    text, replaced_username = replace_between(
        text,
        'async def run_infostealer_username(username):',
        'async def run_user_scanner_username(username):',
        INFOSTEALER_USERNAME_FUNCTION,
    )
    changed = changed or replaced_username

    text, replaced_email = replace_between(
        text,
        'async def run_infostealer_email(email):',
        'async def run_user_scanner_email(email):',
        INFOSTEALER_EMAIL_FUNCTION,
    )
    changed = changed or replaced_email

    return text, changed


def patch_bot(base_dir: Path) -> int:
    bot_path = base_dir / 'bot.py'
    if not bot_path.exists():
        print(f'[SKIP] bot.py not found at {bot_path}')
        return 0

    original = bot_path.read_text(encoding='utf-8', errors='replace')
    text = original

    text, changed_cupid = patch_cupid_author_false_positive(text)
    text, changed_infostealer = patch_infostealer(text)

    if text == original:
        print('[OK] bot.py already has maintenance patches.')
        return 0

    bot_path.write_text(text, encoding='utf-8')
    changes = []
    if changed_cupid:
        changes.append('cupidcr4wl author-url filter')
    if changed_infostealer:
        changes.append('InfoStealer tolerant parser')
    print('[OK] bot.py patched: ' + ', '.join(changes))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description='Apply OSINTbot bot.py maintenance patches')
    parser.add_argument('base_dir', nargs='?', default='.')
    args = parser.parse_args()
    return patch_bot(Path(args.base_dir).resolve())


if __name__ == '__main__':
    raise SystemExit(main())
