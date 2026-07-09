"""Local bot.py maintenance patches applied by setup/update scripts.

This keeps root-level helper scripts out of the repository while still allowing
setup/update to make deterministic compatibility edits to bot.py.
"""

from __future__ import annotations

import argparse
from pathlib import Path

HUDSONROCK_HELPERS = r'''
HUDSONROCK_DISPLAY_NAME = 'HudsonRock Intel'
HUDSONROCK_API_BASE = 'https://cavalier.hudsonrock.com/api/json/v2/osint-tools'
HUDSONROCK_ENDPOINTS = {
    'username': [f'{HUDSONROCK_API_BASE}/search-by-username'],
    'email': [f'{HUDSONROCK_API_BASE}/search-by-email'],
}
HUDSONROCK_PARAM_NAMES = {
    'username': ('username', 'query', 'q', 'term'),
    'email': ('email', 'query', 'q', 'term'),
}
HUDSONROCK_RESULT_KEYS = (
    'stealers', 'results', 'result', 'data', 'records', 'items', 'computers',
    'compromised_machines', 'infected_machines', 'rows'
)
HUDSONROCK_RECORD_KEYS = {
    'computer_name', 'os', 'operating_system', 'ip', 'country', 'city',
    'date_compromised', 'date', 'timestamp', 'email', 'username', 'domain',
    'url', 'credential', 'credentials', 'passwords', 'logins', 'services'
}
HUDSONROCK_SUMMARY_KEYS = [
    'computer_name', 'os', 'operating_system', 'ip', 'country', 'city',
    'date_compromised', 'date', 'timestamp', 'domain', 'url', 'email', 'username'
]
HUDSONROCK_HEADERS = {
    'User-Agent': 'OSINTbot/1.0 (+https://github.com/neednotapply/OSINTbot)',
    'Accept': 'application/json,text/plain,*/*',
}


def looks_like_hudsonrock_record(value):
    if not isinstance(value, dict):
        return False
    keys = {str(key).lower() for key in value.keys()}
    return bool(keys & HUDSONROCK_RECORD_KEYS)


def iter_hudsonrock_records(value, depth=0):
    if depth > 5:
        return

    if isinstance(value, list):
        for item in value:
            yield from iter_hudsonrock_records(item, depth + 1)
        return

    if not isinstance(value, dict):
        return

    if looks_like_hudsonrock_record(value):
        yield value

    for key in HUDSONROCK_RESULT_KEYS:
        nested = value.get(key)
        if nested is not None:
            yield from iter_hudsonrock_records(nested, depth + 1)


def hudsonrock_shape_summary(data):
    if isinstance(data, dict):
        keys = ','.join(sorted(str(key) for key in data.keys())[:20])
        return f'dict keys=[{keys}]'
    if isinstance(data, list):
        return f'list len={len(data)}'
    return type(data).__name__


def hudsonrock_credential_service_names(record):
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


def format_hudsonrock_record(index, record):
    pieces = [f'Record {index}']

    for key in HUDSONROCK_SUMMARY_KEYS:
        value = record.get(key)
        if isinstance(value, (str, int, float)) and str(value).strip():
            pieces.append(f'{key}={value}')

    services = hudsonrock_credential_service_names(record)
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


async def run_hudsonrock_query(kind, query):
    loop = asyncio.get_event_loop()
    endpoints = HUDSONROCK_ENDPOINTS.get(kind, [f'{HUDSONROCK_API_BASE}/search-by-{kind}'])
    param_names = HUDSONROCK_PARAM_NAMES.get(kind, (kind, 'query', 'q'))
    last_status = None
    last_body = ''
    saw_200 = False

    for endpoint in endpoints:
        for param_name in param_names:
            def _request(endpoint=endpoint, param_name=param_name):
                return session.get(
                    endpoint,
                    params={param_name: query},
                    headers=HUDSONROCK_HEADERS,
                    timeout=20,
                )

            response = await loop.run_in_executor(None, _request)
            last_status = response.status_code
            last_body = response.text or ''
            logger.info(
                '%s %s response status=%s endpoint=%s param=%s query=%s',
                HUDSONROCK_DISPLAY_NAME,
                kind,
                response.status_code,
                endpoint,
                param_name,
                query,
            )

            if response.status_code != 200:
                continue

            saw_200 = True
            try:
                data = response.json()
            except ValueError as exc:
                logger.warning(
                    '%s %s JSON parse failed query=%s error=%s body=%s',
                    HUDSONROCK_DISPLAY_NAME,
                    kind,
                    query,
                    exc,
                    shorten(response.text, limit=500),
                )
                continue

            records = list(iter_hudsonrock_records(data))
            logger.info(
                '%s %s response shape=%s records=%s endpoint=%s param=%s query=%s',
                HUDSONROCK_DISPLAY_NAME,
                kind,
                hudsonrock_shape_summary(data),
                len(records),
                endpoint,
                param_name,
                query,
            )

            if records:
                return '\n'.join(format_hudsonrock_record(idx, record) for idx, record in enumerate(records[:100], 1))

            logger.info(
                '%s %s no parsed records body=%s',
                HUDSONROCK_DISPLAY_NAME,
                kind,
                shorten(json.dumps(data, ensure_ascii=False, sort_keys=True), limit=700),
            )

    if saw_200:
        return 'No results found in HudsonRock Intel.'

    if last_status is not None:
        return f'HudsonRock Intel API returned no usable response. Last status code: {last_status}. Body: {shorten(last_body, limit=300)}'

    return 'HudsonRock Intel API returned no response.'
'''

HUDSONROCK_USERNAME_FUNCTION = r'''
async def run_infostealer_username(username):
    return await run_hudsonrock_query('username', username)


'''

HUDSONROCK_EMAIL_FUNCTION = r'''
async def run_infostealer_email(email):
    return await run_hudsonrock_query('email', email)


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


def patch_hudsonrock_label(text: str) -> tuple[str, bool]:
    updated = text.replace('InfoStealer', 'HudsonRock Intel')
    updated = updated.replace('infostealer databases', 'HudsonRock Intel')
    return updated, updated != text


def strip_existing_hudsonrock_helpers(text: str) -> str:
    helper_markers = [
        'INFOSTEALER_API_BASE =',
        'HUDSONROCK_API_BASE =',
        'HUDSONROCK_DISPLAY_NAME =',
    ]
    function_marker = 'async def run_infostealer_username(username):'

    starts = [text.find(marker) for marker in helper_markers if text.find(marker) != -1]
    if not starts:
        return text

    start = min(starts)
    end = text.find(function_marker, start)
    if end == -1:
        return text

    return text[:start] + text[end:]


def patch_hudsonrock_parser(text: str) -> tuple[str, bool]:
    changed = False

    stripped = strip_existing_hudsonrock_helpers(text)
    if stripped != text:
        text = stripped
        changed = True

    marker = 'async def run_infostealer_username(username):'
    if marker in text:
        text = text.replace(marker, HUDSONROCK_HELPERS + '\n\n' + marker, 1)
        changed = True

    text, replaced_username = replace_between(
        text,
        'async def run_infostealer_username(username):',
        'async def run_user_scanner_username(username):',
        HUDSONROCK_USERNAME_FUNCTION,
    )
    changed = changed or replaced_username

    text, replaced_email = replace_between(
        text,
        'async def run_infostealer_email(email):',
        'async def run_user_scanner_email(email):',
        HUDSONROCK_EMAIL_FUNCTION,
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
    text, changed_hudsonrock_parser = patch_hudsonrock_parser(text)
    text, changed_hudsonrock_label = patch_hudsonrock_label(text)

    if text == original:
        print('[OK] bot.py already has maintenance patches.')
        return 0

    bot_path.write_text(text, encoding='utf-8')
    changes = []
    if changed_cupid:
        changes.append('cupidcr4wl author-url filter')
    if changed_hudsonrock_parser:
        changes.append('HudsonRock Intel tolerant parser')
    if changed_hudsonrock_label:
        changes.append('HudsonRock Intel label rename')
    print('[OK] bot.py patched: ' + ', '.join(changes))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description='Apply OSINTbot bot.py maintenance patches')
    parser.add_argument('base_dir', nargs='?', default='.')
    args = parser.parse_args()
    return patch_bot(Path(args.base_dir).resolve())


if __name__ == '__main__':
    raise SystemExit(main())
