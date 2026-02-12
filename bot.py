import asyncio
import json
import logging
import os
import re
import shutil
import subprocess
import sys
from logging.handlers import RotatingFileHandler

import discord
import requests
from discord import app_commands

CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.json')
LOG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'osintbot.log')


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
# Tool paths (portable - supports Linux and Windows)
IS_WINDOWS = os.name == 'nt'
TOOLS_BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'osint-tools')
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

# Source-specific finding parsers
SOURCES_WITH_EMAIL_DETAILS = {'COMB'}

# Configure requests session
session = requests.Session()

# Setup bot
intents = discord.Intents.default()
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)
commands_synced = False


# ============================================================
# INPUT VALIDATION
# ============================================================
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


# ============================================================
# HELPERS
# ============================================================


async def run_subprocess(command, timeout, cwd=None, combine_streams=False):
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
            timeout=timeout,
            cwd=cwd,
            shell=False
        )
        if combine_streams:
            output = (result.stdout or '') + (result.stderr or '')
        else:
            output = result.stdout if result.stdout else result.stderr

        logger.info(
            'Finished subprocess command=%s returncode=%s output=%s',
            command,
            result.returncode,
            shorten(output)
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
                    timeout=timeout,
                    cwd=cwd,
                    shell=False
                )
            except FileNotFoundError:
                logger.warning('FileNotFoundError while running executable: %s', executable)
                missing.append(executable)
                continue

            if combine_streams:
                output = (result.stdout or '') + (result.stderr or '')
            else:
                output = result.stdout if result.stdout else result.stderr

            logger.info(
                'Fallback command succeeded command=%s returncode=%s output=%s',
                command,
                result.returncode,
                shorten(output)
            )
            return output

        checked = ', '.join(sorted(set(missing))) if missing else 'tool executable'
        return (
            f"Unable to run command. Missing executable(s): {checked}. "
            'Install/repair the OSINT tools and retry.'
        )

    return await loop.run_in_executor(None, _run)


def normalize_finding(line):
    clean = re.sub(r'\x1b\[[0-9;]*m', '', line)
    clean = re.sub(r'^\s*\[[*+\-]\]\s*', '', clean)
    clean = re.sub(r'^\s*\d+\.\s*', '', clean)
    clean = clean.replace('`', '').strip()
    clean = re.sub(r'\s+', ' ', clean)
    return clean[:280]



def escape_for_discord(text):
    escaped_mentions = discord.utils.escape_mentions(text)
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
    return any(match.lower() == query_email for match in re.findall(r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}', line))


def extract_primary_email(line):
    match = re.search(r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}', line)
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


def extract_findings(output, query, search_type, tool_name=None):
    if not output:
        return []

    findings = []
    query_l = query.lower()
    tool_l = (tool_name or '').lower()
    query_is_email = '@' in query_l
    query_is_domain = not query_is_email and bool(re.match(r'^(?:[a-z0-9-]+\.)+[a-z]{2,}$', query_l))
    ignored = (
        'searching', 'checking', 'running', 'elapsed', 'timeout', 'api returned status',
        'no results', 'no breaches found', 'found 0', 'usage:',
        'results saved', 'module', 'warning', 'error', 'version:', 'github :',
        'for btc donations', 'found 10000 result(s):'
    )

    for raw in output.splitlines():
        raw_clean = re.sub(r'\x1b\[[0-9;]*m', '', raw).strip()

        if tool_l == 'blackbird' and search_type in {'username', 'email'}:
            blackbird_match = re.match(r'^\[([+\-])\]\s+(.+)$', raw_clean)
            if blackbird_match:
                status, text = blackbird_match.groups()
                if status == '+':
                    findings.append(normalize_finding(text))
                continue

        if search_type == 'email':
            holehe_match = re.match(r'^\[([+\-!x])\]\s+(.+)$', raw_clean)
            if holehe_match:
                status, site = holehe_match.groups()
                site = site.strip()
                site_low = site.lower()

                # Holehe includes legend/output helper lines that are not actual findings.
                if 'email used' in site_low or 'email not used' in site_low or 'rate limit' in site_low:
                    continue

                # Do not emit the queried email address as a finding.
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


async def send_consolidated_results(interaction, query, aggregated):
    query_header = f"## Search Term\n`{escape_for_discord(query)}`"

    if not aggregated:
        logger.info('No consolidated findings query=%s user_id=%s', query, interaction.user.id)
        await interaction.edit_original_response(
            content=f"{query_header}\n\n✅ No consolidated findings across selected sources."
        )
        return

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

    chunks = []
    chunk = ''
    for line in lines:
        candidate = (chunk + '\n' + line).strip()
        if len(candidate) > 1800:
            if chunk:
                chunks.append(chunk)
            chunk = line
        else:
            chunk = candidate

    if chunk:
        chunks.append(chunk)

    if not chunks:
        chunks = [f"{query_header}\n\n✅ No consolidated findings across selected sources."]

    await interaction.edit_original_response(content=chunks[0])
    logger.info(
        'Sending consolidated results query=%s user_id=%s findings=%s chunks=%s',
        query,
        interaction.user.id,
        len(aggregated),
        len(chunks)
    )

    for extra_chunk in chunks[1:]:
        await interaction.followup.send(extra_chunk)


# ============================================================
# TOOL RUNNERS
# ============================================================
async def run_sherlock(username):
    return await run_subprocess(
        [SHERLOCK_PATH, username, '--timeout', '10', '--nsfw', '--no-txt'],
        timeout=120,
        combine_streams=True
    )


async def run_blackbird_username(username):
    return await run_subprocess([BLACKBIRD_PYTHON, BLACKBIRD_SCRIPT, '--username', username], timeout=240, cwd=BLACKBIRD_DIR)


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
        result_text = f"Found {data.get('count', len(data['lines']))} result(s):\n\n"
        for idx, line in enumerate(data['lines'][:100], 1):
            result_text += f"{idx}. {line}\n"
        return result_text

    return 'No breaches found in COMB database.'


async def run_infostealer_username(username):
    loop = asyncio.get_event_loop()

    def _request():
        return session.get(
            'https://cavalier.hudsonrock.com/api/json/v2/osint-tools/search-by-username',
            params={'username': username},
            timeout=20
        )

    response = await loop.run_in_executor(None, _request)
    logger.info('InfoStealer username response status=%s query=%s', response.status_code, username)
    if response.status_code != 200:
        return f"API returned status code: {response.status_code}"

    data = response.json()
    if 'stealers' in data and isinstance(data['stealers'], list) and len(data['stealers']) > 0:
        lines = []
        important_keys = ['computer_name', 'os', 'operating_system', 'ip', 'country', 'city', 'date_compromised']
        username_l = username.lower()

        for idx, stealer in enumerate(data['stealers'][:100], 1):
            if not isinstance(stealer, dict):
                continue

            pieces = [f'Record {idx}']
            for key in important_keys:
                value = stealer.get(key)
                if isinstance(value, (str, int, float)) and str(value).strip():
                    pieces.append(f'{key}={value}')

            blob = json.dumps(stealer, ensure_ascii=False).lower()
            if username_l not in blob:
                continue

            lines.append(' | '.join(pieces))

        if lines:
            return '\n'.join(lines)
    return 'No results found in infostealer databases.'


async def run_user_scanner_username(username):
    return await run_subprocess([USER_SCANNER_PATH, '-u', username], timeout=300)


async def run_blackbird_email(email):
    return await run_subprocess([BLACKBIRD_PYTHON, BLACKBIRD_SCRIPT, '--email', email], timeout=240, cwd=BLACKBIRD_DIR)


async def run_holehe(email):
    return await run_subprocess([HOLEHE_PATH, email], timeout=180)


async def run_infostealer_email(email):
    loop = asyncio.get_event_loop()

    def _request():
        return session.get(
            'https://cavalier.hudsonrock.com/api/json/v2/osint-tools/search-by-email',
            params={'email': email},
            timeout=20
        )

    response = await loop.run_in_executor(None, _request)
    logger.info('InfoStealer email response status=%s query=%s', response.status_code, email)
    if response.status_code != 200:
        return f"API returned status code: {response.status_code}"

    data = response.json()
    if 'stealers' in data and isinstance(data['stealers'], list) and len(data['stealers']) > 0:
        lines = []
        important_keys = ['computer_name', 'os', 'operating_system', 'ip', 'country', 'city', 'date_compromised']
        email_l = email.lower()

        for idx, stealer in enumerate(data['stealers'][:100], 1):
            if not isinstance(stealer, dict):
                continue

            blob = json.dumps(stealer, ensure_ascii=False)
            if not line_contains_exact_email(blob, email_l):
                continue

            pieces = [f'Record {idx}']
            for key in important_keys:
                value = stealer.get(key)
                if isinstance(value, (str, int, float)) and str(value).strip():
                    pieces.append(f'{key}={value}')

            lines.append(' | '.join(pieces))

        if lines:
            return '\n'.join(lines)
    return 'No results found in infostealer databases.'


async def run_user_scanner_email(email):
    return await run_subprocess([USER_SCANNER_PATH, '-e', email], timeout=300)


async def run_cupid_phone(phone):
    return await run_subprocess([CUPID_PYTHON, CUPID_SCRIPT, '-p', phone], timeout=180, cwd=CUPID_DIR)


async def run_whois(domain):
    return await run_subprocess_with_fallback(
        [
            [WHOIS_PYTHON, '-m', 'whois', domain],
            [WHOIS_CMD, domain],
            [sys.executable, '-m', 'whois', domain]
        ],
        timeout=600
    )


async def run_theharvester(domain):
    return await run_subprocess_with_fallback(
        [
            [THEHARVESTER_PYTHON, '-m', 'theHarvester', '-d', domain, '-b', 'all'],
            [THEHARVESTER_CMD, '-d', domain, '-b', 'all'],
            [sys.executable, '-m', 'theHarvester', '-d', domain, '-b', 'all']
        ],
        timeout=600
    )


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
        '**Search type options:** Username, Email, Phone, Domain\n\n'
        '**Sources:**\n'
        '- **Username**: Sherlock, Blackbird, cupidcr4wl, COMB, InfoStealer, user-scanner\n'
        '- **Email**: Blackbird, Holehe, COMB, InfoStealer, user-scanner\n'
        '- **Phone**: cupidcr4wl\n'
        '- **Domain**: whois, theHarvester, Sublist3r\n\n'
        'Results are consolidated so identical findings from multiple tools are grouped with source attribution.'
    )


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
            ('InfoStealer', run_infostealer_username),
            ('user-scanner', run_user_scanner_username),
        ]
    elif selected_type == 'email':
        tools = [
            ('Blackbird', run_blackbird_email),
            ('Holehe', run_holehe),
            ('COMB', run_breaches),
            ('InfoStealer', run_infostealer_email),
            ('user-scanner', run_user_scanner_email),
        ]
    elif selected_type == 'phone':
        tools = [('cupidcr4wl', run_cupid_phone)]
    else:
        tools = [('whois', run_whois), ('theHarvester', run_theharvester), ('Sublist3r', run_sublist3r)]

    await interaction.edit_original_response(content=f"🔎 Running **{selected_type.title()}** searches for `{query}` across {len(tools)} tools.")

    aggregated = {}
    for tool_name, tool_func in tools:
        try:
            logger.info('Starting tool=%s search_type=%s query=%s', tool_name, selected_type, query)
            output = await tool_func(query)
            logger.debug('Raw output tool=%s query=%s output=%s', tool_name, query, shorten(output, limit=1200))
            findings = extract_findings(output, query, selected_type, tool_name)
            logger.info('Tool completed tool=%s findings=%s query=%s', tool_name, len(findings), query)
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
        except Exception as exc:
            logger.exception(
                'Error running tool=%s search_type=%s query=%s user=%s user_id=%s',
                tool_name,
                selected_type,
                query,
                interaction.user,
                interaction.user.id
            )

    logger.info(
        'Finished /osint request type=%s query=%s user_id=%s aggregated_findings=%s',
        selected_type,
        query,
        interaction.user.id,
        len(aggregated)
    )
    await send_consolidated_results(interaction, query, aggregated)


logger.info('Starting bot... logs at %s level=%s', LOG_PATH, logging.getLevelName(logger.level))
client.run(BOT_TOKEN)
