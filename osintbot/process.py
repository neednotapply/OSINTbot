from __future__ import annotations

import os
import signal
import subprocess
import time
from collections.abc import Mapping, Sequence
from pathlib import Path

from .models import ProcessResult


MAX_CAPTURE_BYTES = 2_000_000


def _trim(value: str, limit: int = MAX_CAPTURE_BYTES) -> str:
    encoded = value.encode("utf-8", errors="replace")
    if len(encoded) <= limit:
        return value
    return encoded[:limit].decode("utf-8", errors="replace") + "\n[output truncated]"


def _terminate_tree(process: subprocess.Popen[str]) -> None:
    if process.poll() is not None:
        return
    if os.name == "nt":
        subprocess.run(
            ["taskkill", "/PID", str(process.pid), "/T", "/F"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
    else:
        try:
            os.killpg(process.pid, signal.SIGKILL)  # type: ignore[attr-defined]
        except ProcessLookupError:
            pass


def run_process(
    command: Sequence[str],
    *,
    timeout: float,
    cwd: str | Path | None = None,
    env: Mapping[str, str] | None = None,
) -> ProcessResult:
    started = time.monotonic()
    popen_kwargs: dict[str, object] = {"start_new_session": os.name != "nt"}
    if os.name == "nt":
        popen_kwargs["creationflags"] = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
    try:
        process = subprocess.Popen(  # type: ignore[call-overload]
            list(command),
            cwd=cwd,
            env=dict(env) if env is not None else None,
            shell=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            **popen_kwargs,
        )
    except FileNotFoundError:
        return ProcessResult(tuple(command), "", "", None, time.monotonic() - started, missing=True)

    try:
        stdout, stderr = process.communicate(timeout=timeout)
        return ProcessResult(
            tuple(command), _trim(stdout), _trim(stderr), process.returncode, time.monotonic() - started
        )
    except subprocess.TimeoutExpired:
        _terminate_tree(process)
        stdout, stderr = process.communicate()
        return ProcessResult(
            tuple(command), _trim(stdout), _trim(stderr), None, time.monotonic() - started, timed_out=True
        )
