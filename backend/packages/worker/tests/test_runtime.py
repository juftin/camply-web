"""The local runner must coalesce work, stay responsive, and stop cleanly."""

import asyncio
import datetime as dt
import time
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from db.config import DatabaseConfig
from worker.runtime import LocalRunner


@pytest.mark.anyio
async def test_catalog_coalesces_and_http_loop_can_run() -> None:
    """Slow catalog work shares a job identity without blocking other coroutines."""
    runner = LocalRunner(DatabaseConfig(HOST=":memory:"), heartbeat=300, cooldown=55)
    first = runner.request_sync()
    assert runner.request_sync() == first
    assert runner.catalog_queue.qsize() == 1


@pytest.mark.anyio
async def test_runner_shutdown_cancels_waiters() -> None:
    """Stop every local task without leaving a blocked queue consumer behind."""
    runner = LocalRunner(DatabaseConfig(HOST=":memory:"), heartbeat=300, cooldown=55)
    with (
        patch("worker.runtime.prune_finished", new_callable=AsyncMock),
        patch("worker.runtime.recover_deliveries", new_callable=AsyncMock),
        patch("worker.runtime.due_targets", new_callable=AsyncMock, return_value=[]),
        patch("worker.runtime.deliver_next", new_callable=AsyncMock, return_value=None),
    ):
        await runner.start()
        await asyncio.sleep(0.01)
        assert runner.healthy
        await runner.close()
        assert all(task.done() for task in runner.tasks)
        assert not runner.healthy


def test_history_is_bounded() -> None:
    """A long-running local process cannot accumulate unbounded operational history."""
    runner = LocalRunner(DatabaseConfig(HOST=":memory:"), heartbeat=300, cooldown=55)
    for _ in range(1010):
        runner.record("synthetic", outcome="success")
    assert len(runner.recent()) == 1000


@pytest.mark.anyio
async def test_discovery_deduplicates_in_flight_targets() -> None:
    """Repeated discovery cannot enqueue a target whose provider call is running."""
    runner = LocalRunner(DatabaseConfig(HOST=":memory:"), heartbeat=300, cooldown=55)
    entered, release = asyncio.Event(), asyncio.Event()

    async def check(*args: object, **kwargs: object) -> dict[str, str]:
        """Hold synthetic provider work across a second discovery pass."""
        entered.set()
        await release.wait()
        return {"status": "success"}

    with (
        patch(
            "worker.runtime.due_targets",
            new_callable=AsyncMock,
            return_value=[SimpleNamespace(id="target")],
        ),
        patch("worker.runtime.check_target", side_effect=check) as provider,
    ):
        discovery = asyncio.create_task(runner._discover())
        scan = asyncio.create_task(runner._scan())
        try:
            await asyncio.wait_for(entered.wait(), timeout=1)
            runner.wake.set()
            await asyncio.sleep(0.01)
            assert provider.await_count == 1
            assert runner.scan_queue.empty()
            release.set()
            await asyncio.wait_for(runner.scan_queue.join(), timeout=1)
        finally:
            discovery.cancel()
            scan.cancel()
            await asyncio.gather(discovery, scan, return_exceptions=True)


@pytest.mark.anyio
async def test_target_backoff_and_catalog_failure_isolation() -> None:
    """Failed targets back off finitely while a failed catalog does not stop others."""
    runner = LocalRunner(DatabaseConfig(HOST=":memory:"), heartbeat=300, cooldown=55)
    with patch(
        "worker.runtime.check_target",
        new_callable=AsyncMock,
        side_effect=ValueError("synthetic"),
    ):
        scan = asyncio.create_task(runner._scan())
        try:
            for attempt, delay in enumerate([60, 120, 240, 300], start=1):
                started = time.monotonic()
                runner.in_flight.add("target")
                runner.scan_queue.put_nowait("target")
                await asyncio.wait_for(runner.scan_queue.join(), timeout=1)
                count, deadline = runner.retries["target"]
                assert count == (attempt if attempt < 4 else 0)
                assert delay - 1 < deadline - started < delay + 1
                assert "target" not in runner.in_flight
        finally:
            scan.cancel()
            await asyncio.gather(scan, return_exceptions=True)
    with (
        patch("worker.runtime.PROVIDERS", {1: object, 2: object}),
        patch(
            "worker.runtime.populate_provider",
            new_callable=AsyncMock,
            side_effect=[ValueError("synthetic"), None],
        ) as populate,
    ):
        catalog = asyncio.create_task(runner._catalog())
        try:
            runner.request_sync()
            await asyncio.wait_for(runner.catalog_queue.join(), timeout=1)
            assert populate.await_count == 2
            assert runner.catalog_job is None
            assert [row["outcome"] for row in runner.recent()[:2]] == [
                "success",
                "error",
            ]
        finally:
            catalog.cancel()
            await asyncio.gather(catalog, return_exceptions=True)


def test_history_expires_after_one_day() -> None:
    """Retained attempts expire even if the process has very little recent work."""
    runner = LocalRunner(DatabaseConfig(HOST=":memory:"), heartbeat=300, cooldown=55)
    runner.record("synthetic", outcome="success")
    runner.history[0]["finished_at"] -= dt.timedelta(hours=25)
    assert runner.recent() == []
