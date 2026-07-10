from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent


def _integer(name: str, value: object, default: int, minimum: int, maximum: int) -> int:
    raw = os.getenv(name, str(value if value is not None else default))
    try:
        parsed = int(raw)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be an integer") from exc
    if not minimum <= parsed <= maximum:
        raise ValueError(f"{name} must be between {minimum} and {maximum}")
    return parsed


def _boolean(name: str, value: object, default: bool) -> bool:
    raw = os.getenv(name, str(value if value is not None else default)).strip().lower()
    if raw in {"1", "true", "yes", "on"}:
        return True
    if raw in {"0", "false", "no", "off"}:
        return False
    raise ValueError(f"{name} must be true or false")


@dataclass(slots=True, frozen=True)
class Settings:
    token: str
    tools_dir: Path
    log_path: Path
    log_level: str = "INFO"
    max_concurrency: int = 3
    search_deadline: int = 600
    debug_data_logging: bool = False
    log_max_bytes: int = 2_000_000
    log_backups: int = 3
    tool_timeouts: dict[str, int] = field(default_factory=dict)


def load_settings(config_path: Path | None = None, require_token: bool = True) -> Settings:
    path = config_path or BASE_DIR / "config.json"
    data: dict[str, object] = {}
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError(f"Invalid configuration file: {path}") from exc

    token = os.getenv("OSINTBOT_TOKEN", str(data.get("BOT_TOKEN", ""))).strip()
    if require_token and not token:
        raise ValueError("Set OSINTBOT_TOKEN or BOT_TOKEN in config.json")

    tools_default = BASE_DIR / "osint-tools"
    tools_dir = Path(os.getenv("OSINTBOT_TOOLS_DIR", str(data.get("TOOLS_DIR", tools_default)))).expanduser()
    log_path = Path(os.getenv("OSINTBOT_LOG_PATH", str(data.get("LOG_PATH", BASE_DIR / "osintbot.log")))).expanduser()
    level = os.getenv("OSINTBOT_LOG_LEVEL", str(data.get("LOG_LEVEL", "INFO"))).upper()
    if level not in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}:
        raise ValueError("OSINTBOT_LOG_LEVEL is invalid")

    timeouts = data.get("TOOL_TIMEOUTS", {})
    if not isinstance(timeouts, dict) or any(not isinstance(v, int) or v < 1 for v in timeouts.values()):
        raise ValueError("TOOL_TIMEOUTS must map tool names to positive integer seconds")

    return Settings(
        token=token,
        tools_dir=tools_dir,
        log_path=log_path,
        log_level=level,
        max_concurrency=_integer("OSINTBOT_MAX_CONCURRENCY", data.get("MAX_CONCURRENCY"), 3, 1, 16),
        search_deadline=_integer("OSINTBOT_SEARCH_DEADLINE", data.get("SEARCH_DEADLINE"), 600, 10, 3600),
        debug_data_logging=_boolean("OSINTBOT_DEBUG_DATA_LOGGING", data.get("DEBUG_DATA_LOGGING"), False),
        log_max_bytes=_integer("OSINTBOT_LOG_MAX_BYTES", data.get("LOG_MAX_BYTES"), 2_000_000, 10_000, 100_000_000),
        log_backups=_integer("OSINTBOT_LOG_BACKUPS", data.get("LOG_BACKUPS"), 3, 0, 30),
        tool_timeouts={str(k): v for k, v in timeouts.items()},
    )
