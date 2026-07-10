from __future__ import annotations

import asyncio
import time
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass

from .models import StatusKind, ToolResult


Runner = Callable[[str], Awaitable[str]]


@dataclass(slots=True, frozen=True)
class ToolAdapter:
    name: str
    search_types: frozenset[str]
    timeout: int
    runner: Runner


async def run_tools(
    tools: Sequence[tuple[str, Runner]],
    query: str,
    *,
    max_concurrency: int = 3,
    deadline: float = 600,
) -> list[ToolResult]:
    """Run tools concurrently and retain partial results at the overall deadline."""
    semaphore = asyncio.Semaphore(max_concurrency)

    async def invoke(name: str, runner: Runner) -> ToolResult:
        started = time.monotonic()
        try:
            async with semaphore:
                output = await runner(query)
            return ToolResult(
                tool=name,
                status=StatusKind.OK,
                output=output,
                duration_seconds=time.monotonic() - started,
            )
        except asyncio.CancelledError:
            raise
        except TimeoutError:
            return ToolResult(
                tool=name,
                status=StatusKind.TIMEOUT,
                detail="timed out",
                duration_seconds=time.monotonic() - started,
                timed_out=True,
            )
        except Exception as exc:
            return ToolResult(
                tool=name,
                status=StatusKind.ERROR,
                detail=f"{type(exc).__name__}: {exc}",
                duration_seconds=time.monotonic() - started,
            )

    tasks = [asyncio.create_task(invoke(name, runner), name=f"osint:{name}") for name, runner in tools]
    done, pending = await asyncio.wait(tasks, timeout=deadline)
    for task in pending:
        task.cancel()
    if pending:
        await asyncio.gather(*pending, return_exceptions=True)

    completed = {task.get_name().removeprefix("osint:"): task.result() for task in done}
    return [
        completed.get(
            name,
            ToolResult(tool=name, status=StatusKind.TIMEOUT, detail="overall search deadline exceeded", timed_out=True),
        )
        for name, _ in tools
    ]
