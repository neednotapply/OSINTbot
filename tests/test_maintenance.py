import json
from pathlib import Path

import pytest

from osintbot.maintenance import load_manifest, main


def test_manifest_has_pinned_sources() -> None:
    tools = load_manifest()
    assert tools
    for tool in tools:
        if tool["kind"] == "pypi":
            assert "==" in tool["package"]
        else:
            assert len(tool["revision"]) == 40


def test_invalid_manifest_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps({"schema": 999, "tools": []}), encoding="utf-8")
    with pytest.raises(ValueError, match="Unsupported"):
        load_manifest(path)


def test_doctor_does_not_mutate_tool_directory(tmp_path: Path) -> None:
    before = list(tmp_path.iterdir())
    assert main(["doctor", "--tools-dir", str(tmp_path)]) == 1
    assert list(tmp_path.iterdir()) == before
