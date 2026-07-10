from __future__ import annotations

import argparse
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import venv
from pathlib import Path

from .config import BASE_DIR, load_settings


MANIFEST_PATH = Path(__file__).with_name("tool_manifest.json")


def load_manifest(path: Path = MANIFEST_PATH) -> list[dict[str, object]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema") != 1 or not isinstance(data.get("tools"), list):
        raise ValueError("Unsupported tool manifest")
    return data["tools"]


def _python(venv_dir: Path) -> Path:
    return venv_dir / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def _executable(tool_dir: Path, tool: dict[str, object]) -> Path:
    executable = str(tool["executable"])
    if executable.endswith(".py"):
        return tool_dir / executable
    suffix = ".exe" if os.name == "nt" else ""
    return tool_dir / str(tool["venv"]) / ("Scripts" if os.name == "nt" else "bin") / f"{executable}{suffix}"


def _run(args: list[str], cwd: Path | None = None) -> None:
    subprocess.run(args, cwd=cwd, check=True)


def install_tool(tool: dict[str, object], tools_dir: Path, update: bool = False) -> None:
    tool_dir = tools_dir / str(tool["name"])
    tool_dir.mkdir(parents=True, exist_ok=True)
    if tool["kind"] == "git":
        if not (tool_dir / ".git").exists():
            if any(tool_dir.iterdir()):
                raise RuntimeError(f"Refusing to replace non-Git directory: {tool_dir}")
            tool_dir.rmdir()
            _run(["git", "clone", str(tool["url"]), str(tool_dir)])
        if subprocess.run(["git", "diff", "--quiet"], cwd=tool_dir).returncode != 0:
            raise RuntimeError(f"Refusing to update dirty tool checkout: {tool_dir}")
        _run(["git", "fetch", "--tags", "origin"], cwd=tool_dir)
        _run(["git", "checkout", "--detach", str(tool["revision"])], cwd=tool_dir)

    venv_dir = tool_dir / str(tool["venv"])
    if not _python(venv_dir).exists():
        venv.EnvBuilder(with_pip=True).create(venv_dir)
    python = str(_python(venv_dir))
    if tool["kind"] == "pypi":
        _run([python, "-m", "pip", "install", str(tool["package"])])
    else:
        requirements = tool_dir / "requirements.txt"
        if requirements.exists():
            _run([python, "-m", "pip", "install", "-r", str(requirements)])

    if tool["name"] in {"sherlock", "blackbird", "holehe", "user-scanner"}:
        _run([python, "-m", "pip", "install", "--force-reinstall", str(BASE_DIR / "tool_shims")])


def apply_compatibility_repairs() -> None:
    """Apply maintained upstream wrappers without modifying application source."""
    source = BASE_DIR / "tool_shims" / "osintbot_tool_shims.py"
    spec = importlib.util.spec_from_file_location("osintbot_tool_shims", source)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load compatibility helpers from {source}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.patch_blackbird(BASE_DIR)
    module.install_ssl_patch(BASE_DIR)


def doctor(tools_dir: Path) -> int:
    failures = 0
    for tool in load_manifest():
        path = _executable(tools_dir / str(tool["name"]), tool)
        state = "OK" if path.exists() else "MISSING"
        print(f"[{state}] {tool['name']}: {path}")
        failures += state == "MISSING"
    return int(bool(failures))


def verify(tools_dir: Path) -> int:
    failures = doctor(tools_dir)
    if not shutil.which("git"):
        print("[MISSING] git")
        failures = 1
    try:
        load_settings(require_token=False)
        print("[OK] configuration")
    except ValueError as exc:
        print(f"[ERROR] configuration: {exc}")
        failures = 1
    return failures


def install_service() -> int:
    if os.name == "nt":
        print("systemd service installation is only available on Linux", file=sys.stderr)
        return 2
    service = "\n".join([
        "[Unit]", "Description=OSINT Discord Bot", "After=network-online.target", "",
        "[Service]", f"WorkingDirectory={BASE_DIR}", f"ExecStart={sys.executable} -m osintbot",
        "Restart=on-failure", "EnvironmentFile=-/etc/osintbot.env", "", "[Install]", "WantedBy=multi-user.target", "",
    ])
    print(service)
    print("Save as /etc/systemd/system/osintbot.service, then enable it explicitly.", file=sys.stderr)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Install and verify pinned OSINTbot tools")
    parser.add_argument("command", choices=["install", "update", "doctor", "verify", "service"])
    parser.add_argument("--tools-dir", type=Path)
    args = parser.parse_args(argv)
    tools_dir = (args.tools_dir or load_settings(require_token=False).tools_dir).resolve()
    if args.command in {"install", "update"}:
        tools_dir.mkdir(parents=True, exist_ok=True)
        for tool in load_manifest():
            install_tool(tool, tools_dir, update=args.command == "update")
        apply_compatibility_repairs()
        return verify(tools_dir)
    if args.command == "doctor":
        return doctor(tools_dir)
    if args.command == "verify":
        return verify(tools_dir)
    return install_service()


if __name__ == "__main__":
    raise SystemExit(main())
