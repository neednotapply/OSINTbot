import asyncio

import pytest

from osintbot.models import StatusKind
from osintbot.orchestration import run_tools


@pytest.mark.asyncio
async def test_tools_run_concurrently_with_stable_order() -> None:
    active = 0
    peak = 0

    async def runner(query: str) -> str:
        nonlocal active, peak
        active += 1
        peak = max(peak, active)
        await asyncio.sleep(0.02)
        active -= 1
        return query

    results = await run_tools([("one", runner), ("two", runner), ("three", runner)], "q", max_concurrency=2)
    assert [result.tool for result in results] == ["one", "two", "three"]
    assert all(result.status == StatusKind.OK for result in results)
    assert peak == 2


@pytest.mark.asyncio
async def test_overall_deadline_preserves_partial_results() -> None:
    async def fast(_: str) -> str:
        return "done"

    async def slow(_: str) -> str:
        await asyncio.sleep(1)
        return "late"

    results = await run_tools([("fast", fast), ("slow", slow)], "q", deadline=0.02)
    assert results[0].output == "done"
    assert results[1].status == StatusKind.TIMEOUT
