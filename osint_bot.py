import discord
import subprocess
import asyncio
import os
import requests
import json
import re

BOT_TOKEN = 'YOUR_BOT_TOKEN_HERE' # Replace with bot token
ADMIN_CHANNEL_ID = 123456789  # Replace with your admin channel ID
ADMIN_USER_ID = 123456789  # Replace with your Discord user ID

# Tool paths (portable - works on any system)
SHERLOCK_PATH = os.path.expanduser('~/.local/bin/sherlock')
CUPID_PYTHON = os.path.expanduser('~/osint-tools/cupidcr4wl/cupidcr4wlvenv/bin/python')
CUPID_SCRIPT = os.path.expanduser('~/osint-tools/cupidcr4wl/cc.py')
CUPID_DIR = os.path.expanduser('~/osint-tools/cupidcr4wl')
BLACKBIRD_PYTHON = os.path.expanduser('~/osint-tools/blackbird/blackbirdvenv/bin/python')
BLACKBIRD_SCRIPT = os.path.expanduser('~/osint-tools/blackbird/blackbird.py')
BLACKBIRD_DIR = os.path.expanduser('~/osint-tools/blackbird')
HOLEHE_PATH = os.path.expanduser('~/osint-tools/holehe/holehevenv/bin/holehe')
USER_SCANNER_PATH = os.path.expanduser('~/osint-tools/user-scanner/userscannervenv/bin/user-scanner')

# Configure requests session
session = requests.Session()

# Track users who have been welcomed
welcomed_users = set()

# Setup bot
intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

# ============================================================
# INPUT VALIDATION
# ============================================================

def validate_username(username):
    """Only allow alphanumeric, underscore, hyphen, period. Max 50 chars."""
    if not username or len(username) > 50:
        return False
    return bool(re.match(r'^[a-zA-Z0-9_\-\.]+$', username))

def validate_email(email):
    """Basic email format check. Max 254 chars."""
    if not email or len(email) > 254:
        return False
    return bool(re.match(r'^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$', email))

def validate_phone(phone):
    """Only allow digits and common separators. Max 20 chars."""
    if not phone or len(phone) > 20:
        return False
    return bool(re.match(r'^[0-9+\-() ]+$', phone)) and any(c.isdigit() for c in phone)

def validate_query(query):
    """For breach search - allow email or alphanumeric username. Max 254 chars."""
    if not query or len(query) > 254:
        return False
    return validate_email(query) or bool(re.match(r'^[a-zA-Z0-9_\-\.]+$', query))

# ============================================================

@client.event
async def on_ready():
    print(f'Bot is online as {client.user}')
    print(f'Monitoring DMs and logging to channel: {ADMIN_CHANNEL_ID}')

@client.event
async def on_message(message):
    # Ignore bot's own messages
    if message.author == client.user:
        return

    # Only respond to DMs (ignore server channels)
    if message.guild is not None:
        return

    # Send welcome message on first DM
    if message.author.id not in welcomed_users:
        welcomed_users.add(message.author.id)
        welcome_msg = """
## 🤖 Welcome to BOTINT 🤖

`!help` - Show this help message

## 🛠️ Available Tools 🧰

### Username Search:
🕵️‍♂️ **Sherlock** - Search for usernames across multiple platforms
     `!sherlock <username>`

🐦 **Blackbird** - Search for usernames across multiple platforms
     `!blackbird-username <username>`

💘 **cupidcr4wl** - Search for usernames on adult content platforms
     `!cupidcr4wl-username <username>`

💥 **Breaches** - Search COMB breach database
     `!breaches <username>`

🏴‍☠️ **InfoStealer** - Check username in infostealer logs
     `!infostealer-username <username>`

🔎 **user-scanner** - Scan for username across platforms
     `!user-scanner-username <username>`

### Email Search:
🐦 **Blackbird** - Search an email across multiple platforms
     `!blackbird-email <email>`

✉️ **Holehe** - Check email registration on multiple platforms
     `!holehe <email>`

💥 **Breaches** - Search COMB breach database
     `!breaches <email>`

🏴‍☠️ **InfoStealer** - Check email in infostealer logs
     `!infostealer-email <email>`

🔎 **user-scanner** - Scan for email across platforms
     `!user-scanner-email <email>`

### Phone Search:
💘 **cupidcr4wl** - Search for phone numbers on adult content platforms
     `!cupidcr4wl-phone <phonenumber>`

### Website / Domain:
🌐 **Whois** - Domain registration info
     `!whois <domain>`

🌾 **theHarvester** - Emails, subdomains, hosts, and more
     `!theharvester <domain>`

🔍 **Sublist3r** - Subdomain enumeration
     `!sublist3r <domain>`

**Note:** Searches may take 1-2 minutes depending on the tool and number of sites checked.
        """
        await message.channel.send(welcome_msg)

    # --------------------------------------------------------
    # Log ALL ! commands to admin channel before anything else
    # --------------------------------------------------------
    async def log_command(command, search_term, status="🔍"):
        admin_channel = client.get_channel(ADMIN_CHANNEL_ID)
        if admin_channel:
            log_msg = (
                f"{status} **User:** {message.author} (`{message.author.id}`)\n"
                f"**Command:** `{command} {search_term}`\n"
                f"**Time:** <t:{int(message.created_at.timestamp())}:F>"
            )
            await admin_channel.send(log_msg)

    if message.content.startswith('!'):
        parts = message.content.split(' ', 1)
        cmd = parts[0]
        args = parts[1] if len(parts) > 1 else ''
        await log_command(cmd, args)

    # --------------------------------------------------------
    # Helper: send long output in chunks
    # --------------------------------------------------------
    async def send_output(output, tool_name):
        if not output:
            await message.channel.send(f"❌ No results returned from {tool_name}.")
            return
        chunk_size = 1900
        for i in range(0, len(output), chunk_size):
            chunk = output[i:i+chunk_size]
            await message.channel.send(f'```\n{chunk}\n```')

    # --------------------------------------------------------
    # Commands
    # --------------------------------------------------------

    # !sherlock
    if message.content.startswith('!sherlock '):
        username = message.content[10:].strip()

        if not validate_username(username):
            await message.channel.send("❌ Invalid username. Only letters, numbers, underscores, hyphens, and periods allowed (max 50 chars).")
            return

        await message.channel.send(f'🕵️‍♂️ Searching for `{username}` with Sherlock...\nThis may take a minute.')
        loop = asyncio.get_event_loop()

        try:
            result = await loop.run_in_executor(
                None,
                lambda: subprocess.run(
                    [SHERLOCK_PATH, username, '--timeout', '10', '--nsfw', '--no-txt'],
                    capture_output=True,
                    text=True,
                    timeout=120,
                    shell=False
                )
            )
            output = result.stdout if result.stdout else result.stderr
            await send_output(output, "Sherlock")

        except subprocess.TimeoutExpired:
            await message.channel.send("⏱️ Sherlock search timed out. Try again later.")
        except Exception as e:
            await message.channel.send("❌ Error running Sherlock.")
            admin_channel = client.get_channel(ADMIN_CHANNEL_ID)
            if admin_channel:
                await admin_channel.send(f"🚨 **Sherlock Error** for user {message.author}: {str(e)}")

    # !cupidcr4wl-username
    elif message.content.startswith('!cupidcr4wl-username '):
        username = message.content[21:].strip()

        if not validate_username(username):
            await message.channel.send("❌ Invalid username. Only letters, numbers, underscores, hyphens, and periods allowed (max 50 chars).")
            return

        await message.channel.send(f'💘 Searching for username `{username}` with cupidcr4wl...\nThis may take a few minutes.')
        loop = asyncio.get_event_loop()

        try:
            result = await loop.run_in_executor(
                None,
                lambda: subprocess.run(
                    [CUPID_PYTHON, CUPID_SCRIPT, '-u', username],
                    capture_output=True,
                    text=True,
                    timeout=180,
                    cwd=CUPID_DIR,
                    shell=False
                )
            )
            output = result.stdout if result.stdout else result.stderr
            await send_output(output, "cupidcr4wl")

        except subprocess.TimeoutExpired:
            await message.channel.send("⏱️ cupidcr4wl search timed out. Try again later.")
        except Exception as e:
            await message.channel.send("❌ Error running cupidcr4wl.")
            admin_channel = client.get_channel(ADMIN_CHANNEL_ID)
            if admin_channel:
                await admin_channel.send(f"🚨 **cupidcr4wl Error** for user {message.author}: {str(e)}")

    # !cupidcr4wl-phone
    elif message.content.startswith('!cupidcr4wl-phone '):
        phone = message.content[18:].strip()

        if not validate_phone(phone):
            await message.channel.send("❌ Invalid phone number. Only digits and common separators (+, -, (, ), spaces) allowed (max 20 chars).")
            return

        await message.channel.send(f'📱 Searching for phone number `{phone}` with cupidcr4wl...\nThis may take a few minutes.')
        loop = asyncio.get_event_loop()

        try:
            result = await loop.run_in_executor(
                None,
                lambda: subprocess.run(
                    [CUPID_PYTHON, CUPID_SCRIPT, '-p', phone],
                    capture_output=True,
                    text=True,
                    timeout=180,
                    cwd=CUPID_DIR,
                    shell=False
                )
            )
            output = result.stdout if result.stdout else result.stderr
            await send_output(output, "cupidcr4wl")

        except subprocess.TimeoutExpired:
            await message.channel.send("⏱️ cupidcr4wl search timed out. Try again later.")
        except Exception as e:
            await message.channel.send("❌ Error running cupidcr4wl.")
            admin_channel = client.get_channel(ADMIN_CHANNEL_ID)
            if admin_channel:
                await admin_channel.send(f"🚨 **cupidcr4wl Error** for user {message.author}: {str(e)}")

    # !blackbird-username
    elif message.content.startswith('!blackbird-username '):
        username = message.content[20:].strip()

        if not validate_username(username):
            await message.channel.send("❌ Invalid username. Only letters, numbers, underscores, hyphens, and periods allowed (max 50 chars).")
            return

        await message.channel.send(f'🐦 Searching for username `{username}` with Blackbird...\nThis may take a few minutes.')
        loop = asyncio.get_event_loop()

        try:
            result = await loop.run_in_executor(
                None,
                lambda: subprocess.run(
                    [BLACKBIRD_PYTHON, BLACKBIRD_SCRIPT, '--username', username],
                    capture_output=True,
                    text=True,
                    timeout=240,
                    cwd=BLACKBIRD_DIR,
                    shell=False
                )
            )
            output = result.stdout if result.stdout else result.stderr
            await send_output(output, "Blackbird")

        except subprocess.TimeoutExpired:
            await message.channel.send("⏱️ Blackbird search timed out. Try again later.")
        except Exception as e:
            await message.channel.send("❌ Error running Blackbird.")
            admin_channel = client.get_channel(ADMIN_CHANNEL_ID)
            if admin_channel:
                await admin_channel.send(f"🚨 **Blackbird Error** for user {message.author}: {str(e)}")

    # !blackbird-email
    elif message.content.startswith('!blackbird-email '):
        email = message.content[17:].strip()

        if not validate_email(email):
            await message.channel.send("❌ Invalid email format.")
            return

        await message.channel.send(f'🐦 Searching for email `{email}` with Blackbird...\nThis may take a few minutes.')
        loop = asyncio.get_event_loop()

        try:
            result = await loop.run_in_executor(
                None,
                lambda: subprocess.run(
                    [BLACKBIRD_PYTHON, BLACKBIRD_SCRIPT, '--email', email],
                    capture_output=True,
                    text=True,
                    timeout=240,
                    cwd=BLACKBIRD_DIR,
                    shell=False
                )
            )
            output = result.stdout if result.stdout else result.stderr
            await send_output(output, "Blackbird")

        except subprocess.TimeoutExpired:
            await message.channel.send("⏱️ Blackbird search timed out. Try again later.")
        except Exception as e:
            await message.channel.send("❌ Error running Blackbird.")
            admin_channel = client.get_channel(ADMIN_CHANNEL_ID)
            if admin_channel:
                await admin_channel.send(f"🚨 **Blackbird Error** for user {message.author}: {str(e)}")

    # !holehe
    elif message.content.startswith('!holehe '):
        email = message.content[8:].strip()

        if not validate_email(email):
            await message.channel.send("❌ Invalid email format.")
            return

        await message.channel.send(f'✉️ Checking email `{email}` with Holehe...\nThis may take a few minutes.')
        loop = asyncio.get_event_loop()

        try:
            result = await loop.run_in_executor(
                None,
                lambda: subprocess.run(
                    [HOLEHE_PATH, email],
                    capture_output=True,
                    text=True,
                    timeout=180,
                    shell=False
                )
            )
            output = result.stdout if result.stdout else result.stderr
            await send_output(output, "Holehe")

        except subprocess.TimeoutExpired:
            await message.channel.send("⏱️ Holehe search timed out. Try again later.")
        except Exception as e:
            await message.channel.send("❌ Error running Holehe.")
            admin_channel = client.get_channel(ADMIN_CHANNEL_ID)
            if admin_channel:
                await admin_channel.send(f"🚨 **Holehe Error** for user {message.author}: {str(e)}")

    # !breaches
    elif message.content.startswith('!breaches '):
        query = message.content[10:].strip()

        if not validate_query(query):
            await message.channel.send("❌ Invalid input. Please provide a valid email or username.")
            return

        await message.channel.send(f'💥 Searching COMB database for `{query}`...\n*Note: You can use email or username*')

        try:
            response = session.get(
                'https://api.proxynova.com/comb',
                params={'query': query, 'start': 0, 'limit': 100},
                timeout=20
            )

            if response.status_code == 200:
                data = response.json()
                if 'lines' in data and data['lines']:
                    result_text = f"**Found {data.get('count', len(data['lines']))} result(s):**\n\n"
                    for idx, line in enumerate(data['lines'][:100], 1):
                        result_text += f"{idx}. {line}\n"
                    await send_output(result_text, "Breaches")
                else:
                    await message.channel.send("✅ No breaches found in COMB database.")
            else:
                await message.channel.send(f"❌ API returned status code: {response.status_code}")

        except requests.Timeout:
            await message.channel.send("⏱️ Request timed out. Try again later.")
        except Exception as e:
            await message.channel.send("❌ Error querying breaches API.")
            admin_channel = client.get_channel(ADMIN_CHANNEL_ID)
            if admin_channel:
                await admin_channel.send(f"🚨 **Breaches API Error** for user {message.author}: {str(e)}")

    # !infostealer-email
    elif message.content.startswith('!infostealer-email '):
        email = message.content[19:].strip()

        if not validate_email(email):
            await message.channel.send("❌ Invalid email format.")
            return

        await message.channel.send(f'🏴‍☠️ Searching infostealer logs for email `{email}`...')

        try:
            response = session.get(
                'https://cavalier.hudsonrock.com/api/json/v2/osint-tools/search-by-email',
                params={'email': email},
                timeout=20
            )

            if response.status_code == 200:
                data = response.json()
                if 'stealers' in data and isinstance(data['stealers'], list) and len(data['stealers']) > 0:
                    raw_output = json.dumps(data, indent=2)
                    await send_output(raw_output, "InfoStealer")
                else:
                    await message.channel.send("✅ No results found in infostealer databases.")
            else:
                await message.channel.send(f"❌ API returned status code: {response.status_code}")

        except requests.Timeout:
            await message.channel.send("⏱️ Request timed out. Try again later.")
        except Exception as e:
            await message.channel.send("❌ Error querying infostealer API.")
            admin_channel = client.get_channel(ADMIN_CHANNEL_ID)
            if admin_channel:
                await admin_channel.send(f"🚨 **InfoStealer API Error** for user {message.author}: {str(e)}")

    # !infostealer-username
    elif message.content.startswith('!infostealer-username '):
        username = message.content[22:].strip()

        if not validate_username(username):
            await message.channel.send("❌ Invalid username. Only letters, numbers, underscores, hyphens, and periods allowed (max 50 chars).")
            return

        await message.channel.send(f'🏴‍☠️ Searching infostealer logs for username `{username}`...')

        try:
            response = session.get(
                'https://cavalier.hudsonrock.com/api/json/v2/osint-tools/search-by-username',
                params={'username': username},
                timeout=20
            )

            if response.status_code == 200:
                data = response.json()
                if 'stealers' in data and isinstance(data['stealers'], list) and len(data['stealers']) > 0:
                    raw_output = json.dumps(data, indent=2)
                    await send_output(raw_output, "InfoStealer")
                else:
                    await message.channel.send("✅ No results found in infostealer databases.")
            else:
                await message.channel.send(f"❌ API returned status code: {response.status_code}")

        except requests.Timeout:
            await message.channel.send("⏱️ Request timed out. Try again later.")
        except Exception as e:
            await message.channel.send("❌ Error querying infostealer API.")
            admin_channel = client.get_channel(ADMIN_CHANNEL_ID)
            if admin_channel:
                await admin_channel.send(f"🚨 **InfoStealer API Error** for user {message.author}: {str(e)}")

    # !user-scanner-username
    elif message.content.startswith('!user-scanner-username '):
        username = message.content[23:].strip()

        if not validate_username(username):
            await message.channel.send("❌ Invalid username. Only letters, numbers, underscores, hyphens, and periods allowed (max 50 chars).")
            return

        await message.channel.send(f'🔎 Scanning for username `{username}` with user-scanner...\nThis may take a few minutes.')
        loop = asyncio.get_event_loop()

        try:
            result = await loop.run_in_executor(
                None,
                lambda: subprocess.run(
                    [USER_SCANNER_PATH, '-u', username],
                    capture_output=True,
                    text=True,
                    timeout=300,
                    shell=False
                )
            )
            output = result.stdout if result.stdout else result.stderr
            await send_output(output, "user-scanner")

        except subprocess.TimeoutExpired:
            await message.channel.send("⏱️ user-scanner timed out. Try again later.")
        except Exception as e:
            await message.channel.send("❌ Error running user-scanner.")
            admin_channel = client.get_channel(ADMIN_CHANNEL_ID)
            if admin_channel:
                await admin_channel.send(f"🚨 **user-scanner Error** for user {message.author}: {str(e)}")

    # !user-scanner-email
    elif message.content.startswith('!user-scanner-email '):
        email = message.content[20:].strip()

        if not validate_email(email):
            await message.channel.send("❌ Invalid email format.")
            return

        await message.channel.send(f'🔎 Scanning for email `{email}` with user-scanner...\nThis may take a few minutes.')
        loop = asyncio.get_event_loop()

        try:
            result = await loop.run_in_executor(
                None,
                lambda: subprocess.run(
                    [USER_SCANNER_PATH, '-e', email],
                    capture_output=True,
                    text=True,
                    timeout=300,
                    shell=False
                )
            )
            output = result.stdout if result.stdout else result.stderr
            await send_output(output, "user-scanner")

        except subprocess.TimeoutExpired:
            await message.channel.send("⏱️ user-scanner timed out. Try again later.")
        except Exception as e:
            await message.channel.send("❌ Error running user-scanner.")
            admin_channel = client.get_channel(ADMIN_CHANNEL_ID)
            if admin_channel:
                await admin_channel.send(f"🚨 **user-scanner Error** for user {message.author}: {str(e)}")

    # !whois
    elif message.content.startswith('!whois '):
        domain = message.content[7:].strip()

        await message.channel.send(f'🌐 Running whois on `{domain}`...')
        loop = asyncio.get_event_loop()

        try:
            result = await loop.run_in_executor(
                None,
                lambda: subprocess.run(
                    ['/usr/bin/whois', domain],
                    capture_output=True,
                    text=True,
                    timeout=600,
                    shell=False
                )
            )
            output = result.stdout if result.stdout else result.stderr
            await send_output(output, "whois")

        except subprocess.TimeoutExpired:
            await message.channel.send("⏱️ whois timed out. Try again later.")
        except Exception as e:
            await message.channel.send("❌ Error running whois.")
            admin_channel = client.get_channel(ADMIN_CHANNEL_ID)
            if admin_channel:
                await admin_channel.send(f"🚨 **whois Error** for user {message.author}: {str(e)}")

    # !theharvester
    elif message.content.startswith('!theharvester '):
        domain = message.content[14:].strip()

        await message.channel.send(f'🌾 Running theHarvester on `{domain}`...\nThis may take a few minutes.')
        loop = asyncio.get_event_loop()

        try:
            result = await loop.run_in_executor(
                None,
                lambda: subprocess.run(
                    ['/usr/bin/theHarvester', '-d', domain, '-b', 'all'],
                    capture_output=True,
                    text=True,
                    timeout=600,
                    shell=False
                )
            )
            output = result.stdout if result.stdout else result.stderr
            await send_output(output, "theHarvester")

        except subprocess.TimeoutExpired:
            await message.channel.send("⏱️ theHarvester timed out. Try again later.")
        except Exception as e:
            await message.channel.send("❌ Error running theHarvester.")
            admin_channel = client.get_channel(ADMIN_CHANNEL_ID)
            if admin_channel:
                await admin_channel.send(f"🚨 **theHarvester Error** for user {message.author}: {str(e)}")

    # !sublist3r
    elif message.content.startswith('!sublist3r '):
        domain = message.content[11:].strip()

        await message.channel.send(f'🔍 Running Sublist3r on `{domain}`...\nThis may take a few minutes.')
        loop = asyncio.get_event_loop()

        try:
            result = await loop.run_in_executor(
                None,
                lambda: subprocess.run(
                    ['/usr/bin/sublist3r', '-d', domain, '-o', '/dev/stdout'],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    timeout=600,
                    shell=False
                )
            )
            # Combine stdout and stderr — sublist3r sends status to stderr, results to stdout
            output = (result.stdout or '') + (result.stderr or '')
            await send_output(output, "Sublist3r")

        except subprocess.TimeoutExpired:
            await message.channel.send("⏱️ Sublist3r timed out. Try again later.")
        except Exception as e:
            await message.channel.send("❌ Error running Sublist3r.")
            admin_channel = client.get_channel(ADMIN_CHANNEL_ID)
            if admin_channel:
                await admin_channel.send(f"🚨 **Sublist3r Error** for user {message.author}: {str(e)}")

    # !help
    elif message.content.strip() == '!help':
        help_text = """
## 🛠️ Available Tools 🛠️

### Username Search:
🕵️‍♂️ **Sherlock** - `!sherlock <username>`
🐦 **Blackbird** - `!blackbird-username <username>`
💘 **cupidcr4wl** - `!cupidcr4wl-username <username>`
💥 **Breaches** - `!breaches <username>`
🏴‍☠️ **InfoStealer** - `!infostealer-username <username>`
🔎 **user-scanner** - `!user-scanner-username <username>`

### Email Search:
🐦 **Blackbird** - `!blackbird-email <email>`
✉️ **Holehe** - `!holehe <email>`
💥 **Breaches** - `!breaches <email>`
🏴‍☠️ **InfoStealer** - `!infostealer-email <email>`
🔎 **user-scanner** - `!user-scanner-email <email>`

### Phone Search:
💘 **cupidcr4wl** - `!cupidcr4wl-phone <phonenumber>`

### Website / Domain:
🌐 **Whois** - `!whois <domain>`
🌾 **theHarvester** - `!theharvester <domain>`
🔍 **Sublist3r** - `!sublist3r <domain>`

**Note:** Searches may take 1-2 minutes depending on the tool.
        """
        await message.channel.send(help_text)

    # Unknown command
    elif message.content.startswith('!'):
        await message.channel.send("❓ Unknown command. Type `!help` for available commands.")

# Run the bot
print("Starting bot...")
client.run(BOT_TOKEN)
