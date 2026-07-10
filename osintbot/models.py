from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class StatusKind(StrEnum):
    OK = "ok"
    EMPTY = "empty"
    ERROR = "error"
    TIMEOUT = "timeout"


@dataclass(slots=True, frozen=True)
class Finding:
    text: str
    source: str
    detail: str | None = None


@dataclass(slots=True)
class ToolResult:
    tool: str
    status: StatusKind
    output: str = ""
    findings: list[Finding] = field(default_factory=list)
    detail: str = ""
    duration_seconds: float = 0.0
    exit_code: int | None = None
    stderr: str = ""
    timed_out: bool = False


@dataclass(slots=True)
class SearchResult:
    request_id: str
    category: str
    tools: list[ToolResult] = field(default_factory=list)


@dataclass(slots=True, frozen=True)
class ProcessResult:
    command: tuple[str, ...]
    stdout: str
    stderr: str
    exit_code: int | None
    duration_seconds: float
    timed_out: bool = False
    missing: bool = False

    @property
    def output(self) -> str:
        return "\n".join(part for part in (self.stdout, self.stderr) if part).strip()
