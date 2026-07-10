from pathlib import Path

import pytest

from osintbot.config import load_settings


def test_environment_token_takes_precedence(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    config = tmp_path / "config.json"
    config.write_text('{"BOT_TOKEN":"file-token","MAX_CONCURRENCY":2}', encoding="utf-8")
    monkeypatch.setenv("OSINTBOT_TOKEN", "environment-token")
    monkeypatch.setenv("OSINTBOT_MAX_CONCURRENCY", "4")
    settings = load_settings(config)
    assert settings.token == "environment-token"
    assert settings.max_concurrency == 4


def test_token_can_be_optional_for_diagnostics(tmp_path: Path) -> None:
    settings = load_settings(tmp_path / "missing.json", require_token=False)
    assert settings.token == ""


def test_invalid_concurrency_is_rejected(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OSINTBOT_MAX_CONCURRENCY", "0")
    with pytest.raises(ValueError, match="between"):
        load_settings(tmp_path / "missing.json", require_token=False)
