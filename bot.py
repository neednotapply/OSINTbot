import asyncio
import base64
import binascii
import hashlib
import io
import json
import logging
import os
import re
import shutil
import ssl
import subprocess
import sys
from logging.handlers import RotatingFileHandler
from urllib.parse import urlparse

# ---------------------------------------------------------------------------
# Startup compatibility
# ---------------------------------------------------------------------------
# discord.py imports aiohttp, and aiohttp creates an SSL context during import.
# On some Windows installs, Python can crash there while loading a malformed
# certificate from the Windows certificate store. Patch before importing discord.
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
                'is not installed. Run: python -m pip install certifi',
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

import discord
import requests
from discord import app_commands

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, 'config.json')
LOG_PATH = os.path.join(BASE_DIR, 'osintbot.log')


# ---------------------------------------------------------------------------
# Logging / config
# ---------------------------------------------------------------------------
def configure_logging():
    logger = logging.getLogger('osintbot')
    if logger.handlers:
        return logger

    log_level_name = os.getenv('OSINTBOT_LOG_LEVEL', 'INFO').upper()
    log_level = getattr(logging, log_level_name, logging.INFO)
    formatter = logging.Formatter('%(asctime)s %(levelname)s [%(name)s] %(message)s')

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)

    file_handler = RotatingFileHandler(LOG_PATH, maxBytes=2_000_000, backupCount=3, encoding='utf-8')
    file_handler.setFormatter(formatter)

    logger.setLevel(log_level)
    logger.addHandler(stream_handler)
    logger.addHandler(file_handler)
    logger.propagate = False
    return logger


logger = configure_logging()


def shorten(text, limit=500):
    if text is None:
        return ''
    cleaned = str(text).replace('\n', '\\n')
    if len(cleaned) <= limit:
        return cleaned
    return f'{cleaned[:limit]}... [truncated {len(cleaned) - limit} chars]'


def load_config(config_path):
    with open(config_path, 'r', encoding='utf-8') as config_file:
        config = json.load(config_file)

    required_keys = ['BOT_TOKEN']
    missing_keys = [key for key in required_keys if key not in config]
    if missing_keys:
        missing_str = ', '.join(missing_keys)
        raise KeyError(f'Missing required config key(s): {missing_str}')

    return config


try:
    config = load_config(CONFIG_PATH)
except (FileNotFoundError, json.JSONDecodeError, KeyError) as config_error:
    raise RuntimeError(
        f'Failed to load configuration from {CONFIG_PATH}. '
        'Create or fix config.json with BOT_TOKEN.'
    ) from config_error

BOT_TOKEN = config['BOT_TOKEN']


# ---------------------------------------------------------------------------
# Tool paths
# ---------------------------------------------------------------------------
IS_WINDOWS = os.name == 'nt'
TOOLS_BASE = os.path.join(BASE_DIR, 'osint-tools')
if not os.path.exists(TOOLS_BASE):
    TOOLS_BASE = os.path.expanduser('~/osint-tools')


def venv_exec(tool_name, venv_name, executable):
    script_dir = 'Scripts' if IS_WINDOWS else 'bin'
    ext = '.exe' if IS_WINDOWS else ''
    return os.path.join(TOOLS_BASE, tool_name, venv_name, script_dir, f'{executable}{ext}')


SHERLOCK_PATH = venv_exec('sherlock', 'sherlockvenv', 'sherlock')
CUPID_PYTHON = venv_exec('cupidcr4wl', 'cupidcr4wlvenv', 'python')
CUPID_SCRIPT = os.path.join(TOOLS_BASE, 'cupidcr4wl', 'cc.py')
CUPID_DIR = os.path.join(TOOLS_BASE, 'cupidcr4wl')
BLACKBIRD_PYTHON = venv_exec('blackbird', 'blackbirdvenv', 'python')
BLACKBIRD_SCRIPT = os.path.join(TOOLS_BASE, 'blackbird', 'blackbird.py')
BLACKBIRD_DIR = os.path.join(TOOLS_BASE, 'blackbird')
HOLEHE_PATH = venv_exec('holehe', 'holehevenv', 'holehe')
USER_SCANNER_PATH = venv_exec('user-scanner', 'userscannervenv', 'user-scanner')
WHOIS_CMD = 'whois' if IS_WINDOWS else '/usr/bin/whois'
THEHARVESTER_CMD = 'theHarvester' if IS_WINDOWS else '/usr/bin/theHarvester'
SUBLIST3R_CMD = 'sublist3r' if IS_WINDOWS else '/usr/bin/sublist3r'
WHOIS_PYTHON = venv_exec('whois', 'whoisvenv', 'python')
THEHARVESTER_PYTHON = venv_exec('theHarvester', 'theharvestervenv', 'python')
SUBLIST3R_PYTHON = venv_exec('sublist3r', 'sublist3rvenv', 'python')

SOURCES_WITH_EMAIL_DETAILS = {'COMB'}

session = requests.Session()

intents = discord.Intents.default()
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)
commands_synced = False


# ---------------------------------------------------------------------------
# Input validation
# ---------------------------------------------------------------------------
def validate_username(username):
    if not username or len(username) > 50:
        return False
    return bool(re.match(r'^[a-zA-Z0-9_\-\.]+$', username))


def validate_email(email):
    if not email or len(email) > 254:
        return False
    return bool(re.match(r'^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$', email))


def validate_phone(phone):
    if not phone or len(phone) > 20:
        return False
    return bool(re.match(r'^[0-9+\-() ]+$', phone)) and any(c.isdigit() for c in phone)


def validate_domain(domain):
    if not domain or len(domain) > 253:
        return False
    return bool(re.match(r'^(?:[a-zA-Z0-9-]+\.)+[a-zA-Z]{2,}$', domain))


# ---------------------------------------------------------------------------
# Subprocess helpers
# ---------------------------------------------------------------------------
def collect_subprocess_output(result, combine_streams=False):
    stdout = result.stdout or ''
    stderr = result.stderr or ''

    if combine_streams:
        return stdout + stderr

    if result.returncode == 0:
        return stdout or stderr

    if stdout and stderr:
        return f'STDOUT:\n{stdout}\nSTDERR:\n{stderr}'

    return stdout or stderr


def summarize_subprocess_failure(output):
    if not output:
        return 'no output captured'

    cleaned = [line.strip() for line in str(output).splitlines() if line.strip()]
    if not cleaned:
        return 'no output captured'

    traceback_start = None
    for idx, line in enumerate(cleaned):
        if line.startswith('Traceback (most recent call last):'):
            traceback_start = idx
            break

    if traceback_start is not None:
        tail = cleaned[traceback_start:]
        exception_line = tail[-1] if tail else cleaned[-1]
        return f'{exception_line} (traceback lines={len(tail)})'

    return cleaned[-1]


def output_looks_like_tool_failure(output):
    if not output:
        return False

    lowered = str(output).lower()
    failure_tokens = (
        'unable to run command',
        'missing executable',
        'return code:',
        'traceback (most recent call last)',
        'filenotfounderror',
        'not recognized as an internal or external command',
        'no such file or directory',
        'permission denied',
        'module not found',
        'no module named',
        'modulenotfounderror',
        'importerror',
    )
    return any(token in lowered for token in failure_tokens)


def classify_tool_run(output, findings_count):
    if findings_count > 0:
        return 'ok', f'{findings_count} parsed finding(s)'

    if output_looks_like_tool_failure(output):
        return 'error', summarize_subprocess_failure(output)

    if not output or not str(output).strip():
        return 'warning', 'ran but produced no output'

    return 'no_findings', 'ran, but no parsed findings'


def render_tool_status_line(status):
    icon_by_status = {
        'ok': '✅',
        'no_findings': '○',
        'warning': '⚠️',
        'error': '❌',
        'timeout': '⏱️',
    }
    icon = icon_by_status.get(status.get('status'), '•')
    detail = status.get('detail') or ''
    if detail:
        return f"{icon} **{escape_for_discord(status['tool'])}** — {escape_for_discord(detail)}"
    return f"{icon} **{escape_for_discord(status['tool'])}**"


def build_subprocess_env(extra_env=None):
    proc_env = os.environ.copy()
    if IS_WINDOWS:
        proc_env.setdefault('PYTHONUTF8', '1')
        proc_env.setdefault('PYTHONIOENCODING', 'utf-8')
    if extra_env:
        proc_env.update(extra_env)
    return proc_env


async def run_subprocess(command, timeout, cwd=None, combine_streams=False, env=None):
    loop = asyncio.get_event_loop()
    logger.info(
        'Running subprocess command=%s timeout=%ss cwd=%s combine_streams=%s',
        command,
        timeout,
        cwd,
        combine_streams
    )

    def _run():
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace',
            timeout=timeout,
            cwd=cwd,
            shell=False,
            env=build_subprocess_env(env)
        )
        output = collect_subprocess_output(result, combine_streams=combine_streams)

        if result.returncode == 0:
            logger.info(
                'Finished subprocess command=%s returncode=%s output=%s',
                command,
                result.returncode,
                shorten(output)
            )
        else:
            logger.warning(
                'Subprocess failed command=%s returncode=%s summary=%s output=%s',
                command,
                result.returncode,
                summarize_subprocess_failure(output),
                shorten(output, limit=900)
            )
            return (
                f"Unable to run command successfully. Command: {command}. "
                f"Return code: {result.returncode}. Output: {shorten(output, limit=900)}"
            )
        return output

    return await loop.run_in_executor(None, _run)


async def run_subprocess_with_fallback(commands, timeout, cwd=None, combine_streams=False):
    loop = asyncio.get_event_loop()
    logger.info(
        'Running fallback subprocess commands=%s timeout=%ss cwd=%s combine_streams=%s',
        commands,
        timeout,
        cwd,
        combine_streams
    )

    def _run():
        missing = []
        last_failure = None
        for command in commands:
            executable = command[0]
            if os.path.isabs(executable) and not os.path.exists(executable):
                logger.warning('Skipping missing absolute executable: %s', executable)
                missing.append(executable)
                continue
            if not os.path.isabs(executable) and shutil.which(executable) is None and executable != sys.executable:
                logger.warning('Skipping missing PATH executable: %s', executable)
                missing.append(executable)
                continue

            try:
                logger.info('Attempting fallback command: %s', command)
                result = subprocess.run(
                    command,
                    capture_output=True,
                    text=True,
                    encoding='utf-8',
                    errors='replace',
                    timeout=timeout,
                    cwd=cwd,
                    shell=False,
                    env=build_subprocess_env()
                )
            except FileNotFoundError:
                logger.warning('FileNotFoundError while running executable: %s', executable)
                missing.append(executable)
                continue

            output = collect_subprocess_output(result, combine_streams=combine_streams)

            if result.returncode == 0:
                logger.info(
                    'Fallback command succeeded command=%s returncode=%s output=%s',
                    command,
                    result.returncode,
                    shorten(output)
                )
                return output

            logger.warning(
                'Fallback command failed command=%s returncode=%s output=%s',
                command,
                result.returncode,
                shorten(output)
            )
            last_failure = (command, result.returncode, output)

        if last_failure:
            failed_command, returncode, output = last_failure
            return (
                f"Unable to run command successfully. Last attempted command: {failed_command}. "
                f"Return code: {returncode}. Output: {shorten(output, limit=400)}"
            )

        checked = ', '.join(sorted(set(missing))) if missing else 'tool executable'
        return (
            f"Unable to run command. Missing executable(s): {checked}. "
            'Install/repair the OSINT tools and retry.'
        )

    return await loop.run_in_executor(None, _run)


# ---------------------------------------------------------------------------
# Tool setup / health checks
# ---------------------------------------------------------------------------
def check_path_exists(path, kind='file'):
    if kind == 'dir':
        return os.path.isdir(path)
    return os.path.exists(path)


def check_executable(path_or_command):
    if os.path.isabs(path_or_command) or os.sep in path_or_command or (os.altsep and os.altsep in path_or_command):
        return os.path.exists(path_or_command)
    return shutil.which(path_or_command) is not None


def tool_health_definitions():
    return [
        {
            'name': 'Sherlock',
            'search_types': ['username'],
            'checks': [('exec', 'sherlock executable', SHERLOCK_PATH)],
            'repair': 'setup.bat step [1/9] or setup.sh Sherlock section',
        },
        {
            'name': 'Blackbird',
            'search_types': ['username', 'email'],
            'checks': [
                ('exec', 'blackbird venv python', BLACKBIRD_PYTHON),
                ('file', 'blackbird.py', BLACKBIRD_SCRIPT),
                ('dir', 'blackbird checkout', BLACKBIRD_DIR),
            ],
            'repair': 'setup.bat step [3/9] or setup.sh blackbird section',
        },
        {
            'name': 'cupidcr4wl',
            'search_types': ['username', 'phone'],
            'checks': [
                ('exec', 'cupidcr4wl venv python', CUPID_PYTHON),
                ('file', 'cc.py', CUPID_SCRIPT),
                ('dir', 'cupidcr4wl checkout', CUPID_DIR),
            ],
            'repair': 'setup.bat step [2/9] or setup.sh cupidcr4wl section',
        },
        {
            'name': 'Holehe',
            'search_types': ['email'],
            'checks': [('exec', 'holehe executable', HOLEHE_PATH)],
            'repair': 'setup.bat step [4/9] or setup.sh holehe section',
        },
        {
            'name': 'user-scanner',
            'search_types': ['username', 'email'],
            'checks': [('exec', 'user-scanner executable', USER_SCANNER_PATH)],
            'repair': 'setup.bat step [5/9] or setup.sh user-scanner section',
        },
        {
            'name': 'WHOIS',
            'search_types': ['domain'],
            'checks': [('exec', 'whois venv python', WHOIS_PYTHON)],
            'optional_checks': [('exec', 'whois command', WHOIS_CMD)],
            'repair': 'setup.bat step [6/9] or setup.sh whois section',
        },
        {
            'name': 'DNS Probe',
            'search_types': ['domain'],
            'checks': [('exec', 'theHarvester venv python', THEHARVESTER_PYTHON)],
            'optional_checks': [('exec', 'theHarvester command', THEHARVESTER_CMD)],
            'repair': 'built in; run update_tools.bat to refresh bot dependencies',
        },
        {
            'name': 'Sublist3r',
            'search_types': ['domain'],
            'checks': [('exec', 'Sublist3r venv python', SUBLIST3R_PYTHON)],
            'optional_checks': [('exec', 'sublist3r command', SUBLIST3R_CMD)],
            'repair': 'setup.bat step [8/9] or setup.sh Sublist3r section',
        },
        {
            'name': 'COMB',
            'search_types': ['username', 'email'],
            'api': 'https://api.proxynova.com/comb',
        },
        {
            'name': 'HudsonRock Intel',
            'search_types': ['username', 'email'],
            'api': 'https://cavalier.hudsonrock.com/api/json/v2/osint-tools/',
        },
    ]


def evaluate_tool_health(tool_def):
    if 'api' in tool_def:
        return {
            'name': tool_def['name'],
            'status': 'api',
            'details': [f"remote API checked at query time: {tool_def['api']}"],
            'ok': True,
        }

    details = []
    ok = True
    for check_type, label, target in tool_def.get('checks', []):
        if check_type == 'exec':
            passed = check_executable(target)
        else:
            passed = check_path_exists(target, kind=check_type)

        ok = ok and passed
        status = 'OK' if passed else 'MISSING'
        details.append(f'{status}: {label} -> {target}')

    for check_type, label, target in tool_def.get('optional_checks', []):
        if check_type == 'exec':
            passed = check_executable(target)
        else:
            passed = check_path_exists(target, kind=check_type)
        status = 'OK' if passed else 'optional missing'
        details.append(f'{status}: {label} -> {target}')

    if not ok and tool_def.get('repair'):
        details.append(f"repair: {tool_def['repair']}")

    return {
        'name': tool_def['name'],
        'status': 'ok' if ok else 'missing',
        'details': details,
        'ok': ok,
    }


def build_tool_health_report(search_type=None):
    lines = [
        '## OSINTbot Tool Status',
        f'Base dir: `{escape_for_discord(BASE_DIR)}`',
        f'Tools dir: `{escape_for_discord(TOOLS_BASE)}`',
    ]

    defs = tool_health_definitions()
    if search_type:
        defs = [tool_def for tool_def in defs if search_type in tool_def.get('search_types', [])]
        lines.append(f'Filter: `{escape_for_discord(search_type)}`')

    lines.append('')

    for tool_def in defs:
        health = evaluate_tool_health(tool_def)
        if health['status'] == 'api':
            icon = '🌐'
        elif health['ok']:
            icon = '✅'
        else:
            icon = '❌'
        search_types = ', '.join(tool_def.get('search_types', []))
        lines.append(f"{icon} **{escape_for_discord(tool_def['name'])}** ({escape_for_discord(search_types)})")
        for detail in health['details']:
            lines.append(f"  - {escape_for_discord(detail)}")

    return lines


def chunk_lines(lines, limit=1800):
    chunks = []
    chunk = ''
    for line in lines:
        candidate = (chunk + '\n' + line).strip()
        if len(candidate) > limit:
            if chunk:
                chunks.append(chunk)
            chunk = line
        else:
            chunk = candidate

    if chunk:
        chunks.append(chunk)
    return chunks or ['']


# ---------------------------------------------------------------------------
# Finding parsing / formatting
# ---------------------------------------------------------------------------
def normalize_finding(line):
    clean = re.sub(r'\x1b\[[0-9;]*m', '', str(line))
    clean = re.sub(r'^\s*\[[*+\-]\]\s*', '', clean)
    clean = re.sub(r'^\s*\d+\.\s*', '', clean)
    clean = clean.replace('`', '').strip()
    clean = re.sub(r'\s+', ' ', clean)
    return clean[:280]


def cleanup_url(url):
    clean = str(url).strip().rstrip(',;')
    while clean and clean[-1] in '.,;:!?':
        clean = clean[:-1]
    return clean


SITE_NAME_OVERRIDES = {
    'chaturbate.com': 'Chaturbate',
    'deviantart.com': 'DeviantArt',
    'eros.com': 'Eros',
    'linktr.ee': 'Linktree',
    'playboy.com': 'Playboy',
    'snapchat.com': 'Snapchat',
    't.me': 'Telegram',
    'telegram.me': 'Telegram',
    'tumblr.com': 'Tumblr',
    'xvideos.com': 'xVideos',
}


def site_name_from_url(url):
    parsed = urlparse(cleanup_url(url))
    host = (parsed.netloc or parsed.path.split('/')[0]).lower()
    if '@' in host:
        host = host.rsplit('@', 1)[-1]
    if ':' in host:
        host = host.split(':', 1)[0]
    host = host.strip('.')
    if not host:
        return None

    host_without_www = re.sub(r'^(?:www|m|mobile)\.', '', host)
    if host_without_www in SITE_NAME_OVERRIDES:
        return SITE_NAME_OVERRIDES[host_without_www]

    parts = host_without_www.split('.')
    if len(parts) >= 2:
        registrable = '.'.join(parts[-2:])
        if registrable in SITE_NAME_OVERRIDES:
            return SITE_NAME_OVERRIDES[registrable]
        name = parts[-2]
    else:
        name = parts[0]

    if not name:
        return None

    known_style = {
        'github': 'GitHub',
        'youtube': 'YouTube',
        'reddit': 'Reddit',
        'instagram': 'Instagram',
        'facebook': 'Facebook',
        'twitter': 'Twitter/X',
        'x': 'X',
        'tiktok': 'TikTok',
        'linkedin': 'LinkedIn',
        'pinterest': 'Pinterest',
        'soundcloud': 'SoundCloud',
        'steamcommunity': 'SteamCommunity',
    }
    return known_style.get(name, name.replace('-', ' ').replace('_', ' ').title())


def format_site_finding(site, value):
    site_clean = normalize_finding(site).strip('[]')
    value_clean = cleanup_url(normalize_finding(value))
    if not site_clean or not value_clean:
        return None
    return f'{site_clean}: {value_clean}'


def format_url_finding(url, site=None):
    url_clean = cleanup_url(url)
    site_clean = site or site_name_from_url(url_clean)
    if not site_clean or not url_clean:
        return None
    return format_site_finding(site_clean, url_clean)


def extract_first_url(text):
    match = re.search(r'https?://[^\s<>()\]]+', str(text))
    return cleanup_url(match.group(0)) if match else None


MIME_EXTENSIONS = {
    'image/png': 'png',
    'image/jpeg': 'jpg',
    'image/gif': 'gif',
    'image/webp': 'webp',
    'image/bmp': 'bmp',
}


def extract_embedded_images(output, tool_name=None):
    if not output or (tool_name or '').lower() != 'blackbird':
        return []

    artifacts = []
    seen_hashes = set()
    clean_output = re.sub(r'\x1b\[[0-9;]*m', '', output)
    pattern = re.compile(r'(data:(image/[a-zA-Z0-9.+-]+);base64,([A-Za-z0-9+/=\s]+))')

    for match in pattern.finditer(clean_output):
        mime = match.group(2).lower()
        encoded = re.sub(r'\s+', '', match.group(3))
        if not encoded:
            continue

        try:
            blob = base64.b64decode(encoded, validate=True)
        except (binascii.Error, ValueError):
            continue

        if not blob or len(blob) > 8 * 1024 * 1024:
            continue

        digest = hashlib.sha256(blob).hexdigest()
        if digest in seen_hashes:
            continue
        seen_hashes.add(digest)

        ext = MIME_EXTENSIONS.get(mime, 'bin')
        artifacts.append({
            'filename': f'blackbird_embedded_{digest[:12]}.{ext}',
            'bytes': blob,
            'mime': mime,
        })

    logger.info('Extracted embedded images tool=%s count=%s', tool_name, len(artifacts))
    return artifacts


def escape_for_discord(text):
    escaped_mentions = discord.utils.escape_mentions(str(text))
    escaped_text = discord.utils.escape_markdown(escaped_mentions)

    def _suppress_embed_for_url(match):
        url = match.group(0)
        trailing_punctuation = ''
        while url and url[-1] in '.,;:!?':
            trailing_punctuation = url[-1] + trailing_punctuation
            url = url[:-1]
        return f'<{url}>{trailing_punctuation}'

    return re.sub(r'https?://[^\s<>]+', _suppress_embed_for_url, escaped_text)


def line_contains_exact_email(line, query_email):
    return any(match.lower() == query_email for match in re.findall(r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}', str(line)))


def extract_primary_email(line):
    match = re.search(r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}', str(line))
    return match.group(0).lower() if match else None


def split_email_finding(finding):
    email = extract_primary_email(finding)
    if not email:
        return finding, None

    detail = None
    if ':' in finding:
        left, right = finding.split(':', 1)
        if extract_primary_email(left):
            right = right.strip()
            if right:
                detail = right

    return email, detail


def render_finding_for_tool(item, tool_name):
    base = f"- {escape_for_discord(item['text'])}"
    details = sorted(item.get('details_by_tool', {}).get(tool_name, set()), key=str.lower)
    if details:
        detail_text = ', '.join(escape_for_discord(detail) for detail in details)
        return f"{base}\n  ↳ {detail_text}"
    return base



def is_tool_author_url(url):
    clean = cleanup_url(url).lower().rstrip('/')
    return clean in {
        'https://github.com/osinti4l',
        'http://github.com/osinti4l',
    }


def parse_cupid_finding(raw_clean):
    # Main cupidcr4wl format:
    # ↳ Account found on Site: https://example.com/user
    cupid_match = re.match(
        r'^↳\s+(?:Possible\s+)?Account\s+found\s+on\s+(.+?):\s*(https?://\S+),?$',
        raw_clean,
        flags=re.IGNORECASE
    )
    if cupid_match:
        site, target = cupid_match.groups()
        return format_site_finding(site, target)

    # Site: URL format.
    site_url_match = re.match(
        r'^(?:[-*•↳]\s*)?(?P<site>[A-Za-z0-9][A-Za-z0-9 ._/\-+&]{1,80}):\s*(?P<url>https?://\S+),?$',
        raw_clean
    )
    if site_url_match:
        return format_site_finding(site_url_match.group('site'), site_url_match.group('url'))

    # Account found: URL / Possible account: URL / plain URL format.
    url = extract_first_url(raw_clean)
    if url:
        if is_tool_author_url(url):
            return None
        # Prefer a label from the URL host over returning a bare URL.
        return format_url_finding(url)

    return None


def extract_findings(output, query, search_type, tool_name=None):
    if not output:
        return []

    if output_looks_like_tool_failure(output):
        logger.info(
            'Skipping finding parsing because tool output looks like failure tool=%s search_type=%s query=%s',
            tool_name,
            search_type,
            query,
        )
        return []

    findings = []
    query_l = query.lower()
    tool_l = (tool_name or '').lower()
    query_is_email = '@' in query_l
    query_is_domain = not query_is_email and bool(re.match(r'^(?:[a-z0-9-]+\.)+[a-z]{2,}$', query_l))
    ignored = (
        'searching', 'checking', 'running', 'elapsed', 'timeout', 'api returned status',
        'no results', 'no breaches found', 'found 0', 'usage:', 'results saved',
        'module', 'warning', 'error', 'version:', 'github :', 'for btc donations',
        'found 10000 result(s):', 'lookup failed', 'unable to', 'not installed',
        'no whois results', 'no dns probe results'
    )
    blackbird_started = False
    pending_blackbird_site = None

    raw_lines = output.splitlines()
    if tool_l == 'user-scanner' and '\\n' in output:
        raw_lines = output.replace('\\n', '\n').splitlines()

    for raw in raw_lines:
        raw_clean = re.sub(r'\x1b\[[0-9;]*m', '', raw).strip()

        if tool_l == 'blackbird' and search_type in {'username', 'email'}:
            lowered = raw_clean.lower()
            if (
                'downloading site list' in lowered
                or 'sites list is up to date' in lowered
                or 'enumerating accounts with username' in lowered
                or 'enumerating accounts with email' in lowered
            ):
                blackbird_started = True

            if not blackbird_started and raw_clean.startswith(('✔', '✅', '[+]', '[!]')):
                blackbird_started = True

            if not blackbird_started:
                continue

            if pending_blackbird_site and re.match(r'^https?://', raw_clean):
                normalized = format_site_finding(pending_blackbird_site, raw_clean)
                if normalized:
                    findings.append(normalized)
                pending_blackbird_site = None
                continue

            if 'enumerating accounts with username' in lowered or 'check completed in' in lowered:
                pending_blackbird_site = None
                continue

            blackbird_match = re.match(r'^\[([+\-])\]\s+(.+)$', raw_clean)
            if blackbird_match:
                status, text = blackbird_match.groups()
                if status == '+':
                    findings.append(normalize_finding(text))
                continue

            if raw_clean.startswith(('✔', '✅')):
                line_without_status = raw_clean[1:].strip(' \t\uFE0F')
                site_match = re.match(r'^\[([^\]]+)\]\s*(.*)$', line_without_status)
                if site_match:
                    site, target = site_match.groups()
                    target = target.strip()
                    if target:
                        normalized = format_site_finding(site, target)
                        if normalized:
                            findings.append(normalized)
                    else:
                        pending_blackbird_site = site
                continue

        if tool_l == 'cupidcr4wl' and search_type in {'username', 'phone'}:
            cupid_finding = parse_cupid_finding(raw_clean)
            if cupid_finding:
                findings.append(cupid_finding)
                continue

        if tool_l == 'user-scanner' and search_type in {'username', 'email'}:
            scanner_match = re.match(r'^\[✘\]\s+(.+?)\s+\(([^)]+)\):\s+Taken\s*$', raw_clean, flags=re.IGNORECASE)
            if scanner_match:
                site, account = scanner_match.groups()
                normalized = format_site_finding(site, account)
                if normalized:
                    findings.append(normalized)
                continue

            if 'available' in raw_clean.lower() or raw_clean.startswith('[✔]'):
                continue

        if search_type == 'email':
            holehe_match = re.match(r'^\[([+\-!x])\]\s+(.+)$', raw_clean)
            if holehe_match:
                status, site = holehe_match.groups()
                site = site.strip()
                site_low = site.lower()

                if 'email used' in site_low or 'email not used' in site_low or 'rate limit' in site_low:
                    continue

                if extract_primary_email(site):
                    continue

                if status == '+':
                    findings.append(site)
                elif status == '!':
                    findings.append(f'{site} (rate-limited/blocked)')
                continue

        line = normalize_finding(raw)
        if not line or len(line) < 3:
            continue

        is_structured_record = bool(re.match(r'^record\s+\d+\b', line, flags=re.IGNORECASE)) or (' | ' in line and '=' in line)

        if search_type == 'email':
            normalized_line = line.strip().lower().rstrip(':')
            if normalized_line == query_l:
                continue

        low = line.lower()
        if any(token in low for token in ignored):
            continue

        has_query = query_l in low
        has_url = 'http://' in low or 'https://' in low
        looks_record = ':' in line or '@' in line

        if search_type == 'email' and not line_contains_exact_email(line, query_l) and not is_structured_record:
            continue

        if search_type in {'username', 'phone'} and not has_query and not is_structured_record:
            continue

        # As a last-resort cleanup, label URL-only username/phone hits rather than
        # returning bare links.
        if tool_l == 'cupidcr4wl' and has_url:
            labeled = format_url_finding(extract_first_url(line))
            if labeled:
                findings.append(labeled)
                continue

        if has_query:
            findings.append(line)
            continue

        if (query_is_email or query_is_domain) and not has_query and not is_structured_record:
            continue

        if has_url or looks_record or is_structured_record:
            findings.append(line)

    logger.info(
        'Parsed findings tool=%s search_type=%s query=%s findings=%s',
        tool_name,
        search_type,
        query,
        len(findings)
    )
    return findings


async def send_consolidated_results(interaction, query, aggregated, image_artifacts=None, tool_statuses=None):
    query_header = f"\n`{escape_for_discord(query)}`"

    by_source = {}
    multi_source = []
    sorted_items = sorted(aggregated.values(), key=lambda x: (-len(x['tools']), x['text'].lower()))
    for item in sorted_items:
        if len(item['tools']) > 1:
            multi_source.append(item)
            continue

        for tool in item['tools']:
            by_source.setdefault(tool, []).append(item)

    lines = [query_header]

    if not aggregated:
        logger.info('No consolidated findings query=%s user_id=%s', query, interaction.user.id)
        lines.append('')
        lines.append('✅ No consolidated findings across selected sources.')

    if multi_source:
        lines.append('## Found on Multiple Sources')
        for item in multi_source:
            details = sorted(
                {
                    detail
                    for tool_details in item.get('details_by_tool', {}).values()
                    for detail in tool_details
                },
                key=str.lower
            )
            base = f"- {escape_for_discord(item['text'])}"
            if details:
                detail_text = ', '.join(escape_for_discord(detail) for detail in details)
                lines.append(f"{base}\n  ↳ {detail_text}")
            else:
                lines.append(base)

    for tool in sorted(by_source):
        lines.append(f'## {escape_for_discord(tool)}')
        unique_items = {item['text'].lower(): item for item in by_source[tool]}
        for key in sorted(unique_items, key=str.lower):
            lines.append(render_finding_for_tool(unique_items[key], tool))

    if tool_statuses:
        lines.append('## Tool Status')
        for status in tool_statuses:
            lines.append(render_tool_status_line(status))

    chunks = chunk_lines(lines, limit=1800)

    await interaction.edit_original_response(content=chunks[0])
    logger.info(
        'Sending consolidated results query=%s user_id=%s findings=%s chunks=%s statuses=%s',
        query,
        interaction.user.id,
        len(aggregated),
        len(chunks),
        len(tool_statuses or [])
    )

    for extra_chunk in chunks[1:]:
        await interaction.followup.send(extra_chunk)

    if image_artifacts:
        for artifact in image_artifacts:
            file_obj = discord.File(io.BytesIO(artifact['bytes']), filename=artifact['filename'])
            await interaction.followup.send(
                content=f"🖼️ Decoded embedded image from {artifact.get('source', 'Blackbird')} ({artifact['mime']})",
                file=file_obj
            )


# ---------------------------------------------------------------------------
# Tool runners
# ---------------------------------------------------------------------------
async def run_sherlock(username):
    return await run_subprocess(
        [SHERLOCK_PATH, username, '--timeout', '10', '--nsfw', '--no-txt'],
        timeout=120,
        combine_streams=True
    )


BLACKBIRD_ENV = {
    'PYTHONUTF8': '1',
    'PYTHONIOENCODING': 'utf-8',
    'TERM': 'dumb',
    'NO_COLOR': '1',
}


async def run_blackbird_username(username):
    return await run_subprocess(
        [BLACKBIRD_PYTHON, BLACKBIRD_SCRIPT, '--username', username],
        timeout=240,
        cwd=BLACKBIRD_DIR,
        env=BLACKBIRD_ENV
    )


async def run_cupid_username(username):
    return await run_subprocess([CUPID_PYTHON, CUPID_SCRIPT, '-u', username], timeout=180, cwd=CUPID_DIR)


async def run_breaches(query):
    loop = asyncio.get_event_loop()

    def _request():
        return session.get('https://api.proxynova.com/comb', params={'query': query, 'start': 0, 'limit': 100}, timeout=20)

    response = await loop.run_in_executor(None, _request)
    logger.info('COMB response status=%s query=%s', response.status_code, query)
    if response.status_code != 200:
        return f"API returned status code: {response.status_code}"

    data = response.json()
    if 'lines' in data and data['lines']:
        result_lines = [f"Found {data.get('count', len(data['lines']))} result(s):", ""]
        for idx, line in enumerate(data['lines'][:100], 1):
            result_lines.append(f"{idx}. {line}")
        return '\n'.join(result_lines)

    return 'No breaches found in COMB database.'






HUDSONROCK_DISPLAY_NAME = 'HudsonRock Intel'
HUDSONROCK_API_BASE = 'https://cavalier.hudsonrock.com/api/json/v2/osint-tools'
HUDSONROCK_ENDPOINTS = {
    'username': [f'{HUDSONROCK_API_BASE}/search-by-username'],
    'email': [f'{HUDSONROCK_API_BASE}/search-by-email'],
}
HUDSONROCK_PARAM_NAMES = {
    'username': ('username',),
    'email': ('email',),
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
    param_names = HUDSONROCK_PARAM_NAMES.get(kind, (kind,))
    last_status = None
    last_body = ''

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
                '%s %s valid no-hit response body=%s',
                HUDSONROCK_DISPLAY_NAME,
                kind,
                shorten(json.dumps(data, ensure_ascii=False, sort_keys=True), limit=700),
            )
            return 'No results found in HudsonRock Intel.'

    if last_status is not None:
        return f'HudsonRock Intel API returned no usable response. Last status code: {last_status}. Body: {shorten(last_body, limit=300)}'

    return 'HudsonRock Intel API returned no response.'



async def run_infostealer_username(username):
    return await run_hudsonrock_query('username', username)


async def run_user_scanner_username(username):
    return await run_subprocess([USER_SCANNER_PATH, '-u', username], timeout=300)


async def run_blackbird_email(email):
    return await run_subprocess(
        [BLACKBIRD_PYTHON, BLACKBIRD_SCRIPT, '--email', email],
        timeout=240,
        cwd=BLACKBIRD_DIR,
        env=BLACKBIRD_ENV
    )


async def run_holehe(email):
    return await run_subprocess([HOLEHE_PATH, email], timeout=180)







async def run_infostealer_email(email):
    return await run_hudsonrock_query('email', email)


async def run_user_scanner_email(email):
    return await run_subprocess([USER_SCANNER_PATH, '-e', email], timeout=300)


async def run_cupid_phone(phone):
    return await run_subprocess([CUPID_PYTHON, CUPID_SCRIPT, '-p', phone], timeout=180, cwd=CUPID_DIR)




DOMAIN_DNS_PROBE_HOSTS = [
    '', 'www', 'mail', 'mx', 'smtp', 'imap', 'pop', 'ftp', 'vpn', 'portal',
    'login', 'accounts', 'admin', 'api', 'dev', 'test', 'staging', 'cdn'
]
DOMAIN_WHOIS_KEYS = [
    'domain_name', 'registrar', 'creation_date', 'expiration_date',
    'updated_date', 'name_servers', 'emails', 'status'
]


def domain_list_value(value):
    if value is None:
        return []
    if isinstance(value, (list, tuple, set)):
        values = []
        for item in value:
            values.extend(domain_list_value(item))
        return values
    return [str(value)]


def format_domain_values(values, max_items=8):
    cleaned = []
    seen = set()
    for value in values:
        text = str(value).strip()
        if not text:
            continue
        marker = text.lower()
        if marker in seen:
            continue
        seen.add(marker)
        cleaned.append(text)
    return ', '.join(cleaned[:max_items])


async def run_whois(domain):
    loop = asyncio.get_event_loop()

    def _lookup():
        try:
            import whois
        except Exception as exc:
            return f'No WHOIS results for {domain}: python-whois unavailable ({type(exc).__name__}: {exc})'

        try:
            data = whois.whois(domain)
        except Exception as exc:
            return f'No WHOIS results for {domain}: lookup failed ({type(exc).__name__}: {exc})'

        if not data:
            return f'No WHOIS results for {domain}.'

        lines = []
        if hasattr(data, 'items'):
            source = dict(data)
        else:
            source = getattr(data, '__dict__', {}) or {}

        for key in DOMAIN_WHOIS_KEYS:
            rendered = format_domain_values(domain_list_value(source.get(key)))
            if rendered:
                lines.append(f'{domain} WHOIS {key}: {rendered}')

        if not lines:
            return f'No WHOIS results for {domain}.'

        return '\n'.join(lines)

    return await loop.run_in_executor(None, _lookup)


async def run_dns_probe(domain):
    loop = asyncio.get_event_loop()

    def _probe():
        import socket

        lines = []
        seen = set()
        for prefix in DOMAIN_DNS_PROBE_HOSTS:
            hostname = domain if not prefix else f'{prefix}.{domain}'
            try:
                answers = socket.getaddrinfo(hostname, None, proto=socket.IPPROTO_TCP)
            except OSError:
                continue

            ips = sorted({answer[4][0] for answer in answers if answer and answer[4]})
            if not ips:
                continue

            key = (hostname.lower(), tuple(ips))
            if key in seen:
                continue
            seen.add(key)
            lines.append(f'{domain} DNS {hostname}: ' + ', '.join(ips[:8]))

        if not lines:
            return f'No DNS probe results for {domain}.'
        return '\n'.join(lines[:50])

    return await loop.run_in_executor(None, _probe)


async def run_sublist3r(domain):
    return await run_subprocess_with_fallback(
        [
            [SUBLIST3R_PYTHON, '-m', 'sublist3r', '-d', domain],
            [SUBLIST3R_CMD, '-d', domain],
            [sys.executable, '-m', 'sublist3r', '-d', domain]
        ],
        timeout=600,
        combine_streams=True
    )


# ---------------------------------------------------------------------------
# Discord commands# ---------------------------------------------------------------------------
# Discord commands# ---------------------------------------------------------------------------
# Discord commands
# ---------------------------------------------------------------------------
@client.event
async def on_ready():
    global commands_synced
    logger.info('Bot is online as %s', client.user)
    logger.info('Monitoring commands.')

    if not commands_synced:
        await tree.sync()
        commands_synced = True
        logger.info('Slash commands synced.')


@tree.command(name='help', description='Show /osint usage and sources')
async def help_command(interaction: discord.Interaction):
    await interaction.response.send_message(
        '## OSINTbot Help\n\n'
        '**Main command:** `/osint`\n'
        '**Status command:** `/osint-status`\n'
        '**Search type options:** Username, Email, Phone, Domain\n\n'
        '**Sources:**\n'
        '- **Username**: Sherlock, Blackbird, cupidcr4wl, COMB, HudsonRock Intel, user-scanner\n'
        '- **Email**: Blackbird, Holehe, COMB, HudsonRock Intel, user-scanner\n'
        '- **Phone**: cupidcr4wl\n'
        '- **Domain**: WHOIS, DNS Probe, Sublist3r\n\n'
        'Results are consolidated so identical findings from multiple tools are grouped with source attribution. '
        'Each `/osint` result now includes a Tool Status section showing which tools ran, failed, timed out, or returned no parsed findings.'
    )


@tree.command(name='osint-status', description='Check configured OSINT tool paths and setup status')
@app_commands.describe(search_type='Optional category filter')
@app_commands.choices(search_type=[
    app_commands.Choice(name='All', value='all'),
    app_commands.Choice(name='Username', value='username'),
    app_commands.Choice(name='Email', value='email'),
    app_commands.Choice(name='Phone', value='phone'),
    app_commands.Choice(name='Domain', value='domain'),
])
async def osint_status(interaction: discord.Interaction, search_type: app_commands.Choice[str] = None):
    selected_type = None
    if search_type and search_type.value != 'all':
        selected_type = search_type.value

    lines = build_tool_health_report(selected_type)
    chunks = chunk_lines(lines, limit=1800)
    await interaction.response.send_message(chunks[0])
    for chunk in chunks[1:]:
        await interaction.followup.send(chunk)


@tree.command(name='osint', description='Run an OSINT search by category')
@app_commands.describe(search_type='Choose search category', query='Username, email, phone number, or domain')
@app_commands.choices(search_type=[
    app_commands.Choice(name='Username', value='username'),
    app_commands.Choice(name='Email', value='email'),
    app_commands.Choice(name='Phone', value='phone'),
    app_commands.Choice(name='Domain', value='domain'),
])
async def osint(interaction: discord.Interaction, search_type: app_commands.Choice[str], query: str):
    await interaction.response.defer(thinking=True)
    selected_type = search_type.value
    query = query.strip()
    logger.info(
        'Received /osint request type=%s query=%s user=%s user_id=%s',
        selected_type,
        query,
        interaction.user,
        interaction.user.id
    )

    if selected_type == 'username' and not validate_username(query):
        await interaction.edit_original_response(content='❌ Invalid username. Use letters, numbers, underscores, hyphens, and periods (max 50 chars).')
        return
    if selected_type == 'email' and not validate_email(query):
        await interaction.edit_original_response(content='❌ Invalid email format.')
        return
    if selected_type == 'phone' and not validate_phone(query):
        await interaction.edit_original_response(content='❌ Invalid phone number. Use digits and common separators (+, -, (, ), spaces).')
        return
    if selected_type == 'domain' and not validate_domain(query):
        await interaction.edit_original_response(content='❌ Invalid domain format.')
        return

    if selected_type == 'username':
        tools = [
            ('Sherlock', run_sherlock),
            ('Blackbird', run_blackbird_username),
            ('cupidcr4wl', run_cupid_username),
            ('COMB', run_breaches),
            ('HudsonRock Intel', run_infostealer_username),
            ('user-scanner', run_user_scanner_username),
        ]
    elif selected_type == 'email':
        tools = [
            ('Blackbird', run_blackbird_email),
            ('Holehe', run_holehe),
            ('COMB', run_breaches),
            ('HudsonRock Intel', run_infostealer_email),
            ('user-scanner', run_user_scanner_email),
        ]
    elif selected_type == 'phone':
        tools = [('cupidcr4wl', run_cupid_phone)]
    else:
        tools = [('WHOIS', run_whois), ('DNS Probe', run_dns_probe), ('Sublist3r', run_sublist3r)]

    await interaction.edit_original_response(content=f"🔎 Running **{selected_type.title()}** searches for `{query}` across {len(tools)} tools.")

    aggregated = {}
    image_artifacts = []
    tool_statuses = []

    for tool_name, tool_func in tools:
        try:
            logger.info('Starting tool=%s search_type=%s query=%s', tool_name, selected_type, query)
            output = await tool_func(query)
            logger.debug('Raw output tool=%s query=%s output=%s', tool_name, query, shorten(output, limit=1200))

            extracted_images = extract_embedded_images(output, tool_name)
            for image in extracted_images:
                image['source'] = tool_name
                image_artifacts.append(image)

            findings = extract_findings(output, query, selected_type, tool_name)
            if extracted_images:
                findings.append(f"Embedded image decoded ({len(extracted_images)})")

            status, detail = classify_tool_run(output, len(findings))
            tool_statuses.append({'tool': tool_name, 'status': status, 'detail': detail})

            logger.info('Tool completed tool=%s findings=%s status=%s query=%s images=%s', tool_name, len(findings), status, query, len(extracted_images))
            for finding in findings:
                aggregate_text = finding
                aggregate_key = finding.lower()
                detail = None

                if tool_name in SOURCES_WITH_EMAIL_DETAILS:
                    aggregate_text, detail = split_email_finding(finding)
                    aggregate_key = aggregate_text.lower()

                if aggregate_key not in aggregated:
                    aggregated[aggregate_key] = {
                        'text': aggregate_text,
                        'tools': set(),
                        'details_by_tool': {}
                    }

                aggregated[aggregate_key]['tools'].add(tool_name)

                if detail:
                    aggregated[aggregate_key]['details_by_tool'].setdefault(tool_name, set()).add(detail)

        except subprocess.TimeoutExpired:
            logger.warning('Timeout running tool=%s search_type=%s query=%s', tool_name, selected_type, query)
            tool_statuses.append({'tool': tool_name, 'status': 'timeout', 'detail': 'timed out'})
        except Exception as exc:
            logger.exception(
                'Error running tool=%s search_type=%s query=%s user=%s user_id=%s',
                tool_name,
                selected_type,
                query,
                interaction.user,
                interaction.user.id
            )
            tool_statuses.append({'tool': tool_name, 'status': 'error', 'detail': f'{type(exc).__name__}: {exc}'})

    logger.info(
        'Finished /osint request type=%s query=%s user_id=%s aggregated_findings=%s tool_statuses=%s',
        selected_type,
        query,
        interaction.user.id,
        len(aggregated),
        len(tool_statuses)
    )
    await send_consolidated_results(interaction, query, aggregated, image_artifacts=image_artifacts, tool_statuses=tool_statuses)


logger.info('Starting bot... logs at %s level=%s', LOG_PATH, logging.getLevelName(logger.level))
client.run(BOT_TOKEN)
