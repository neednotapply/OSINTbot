"""Startup compatibility fixes for OSINTbot.

Python imports this module automatically from the script directory before
``bot.py`` runs. That lets us patch Windows SSL startup before discord.py imports
aiohttp, which creates an SSL context during import.
"""

import os
import ssl
import sys

_ORIGINAL_CREATE_DEFAULT_CONTEXT = ssl.create_default_context


def _create_default_context_with_certifi_fallback(*args, **kwargs):
    """Retry with certifi if Windows has a malformed certificate in its store."""
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
