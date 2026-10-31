"""Standalone operations distinguish absent services from actual local failures."""

from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import Response

from camply.db.config import DatabaseConfig
from camply.db.migration import upgrade_database
from camply.server.config import RuntimeMode, backend_config
from camply.server.routers import health
from camply.server.services import local_operations, operations, trends
from camply.worker.runtime import LocalRunner


def test_local_overview_and_disabled_trends(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Do not query monitoring services when they are intentionally unavailable."""
    import asyncio

    database = DatabaseConfig(HOST=str(tmp_path / "state.db"))
    upgrade_database(database_config=database)
    monkeypatch.setattr(backend_config, "runtime_mode", RuntimeMode.STANDALONE)

    async def verify() -> None:
        """Run the application-scoped DB and local state within one event loop."""
        database.open()
        runner = LocalRunner(database, heartbeat=300, cooldown=55)
        monkeypatch.setattr(local_operations, "runner", runner)
        try:
            with (
                patch(
                    "camply.worker.runtime.due_targets",
                    new_callable=AsyncMock,
                    return_value=[],
                ),
                patch(
                    "camply.worker.runtime.populate_provider", new_callable=AsyncMock
                ),
            ):
                await runner.start()
                async with database.get_session() as session:
                    assert (
                        await health.healthcheck(
                            Response(status_code=200), session=session
                        )
                    ).status == 200
                overview = await operations.get_operations_overview()
                assert overview.runtime_mode == "standalone"
                assert overview.broker_connected is None
                assert not overview.capabilities.historical_trends
                first = await operations.trigger_provider_sync()
                assert await operations.trigger_provider_sync() == first
                response = await trends.get_admin_trends()
                assert not response.available and not response.metrics
                runner.record("synthetic", outcome="failure", task_id="failed-job")
                runner.record("synthetic", outcome="retry", task_id="retry-job")
                assert (await operations.get_recent_tasks(outcome="error")).total == 1
                assert (
                    await operations.get_recent_tasks(outcome="retrying")
                ).total == 1
                runner.tasks[0].cancel()
                await asyncio.gather(runner.tasks[0], return_exceptions=True)
                async with database.get_session() as session:
                    assert (
                        await health.healthcheck(
                            Response(status_code=200), session=session
                        )
                    ).status == 503
                assert (
                    await operations.get_operations_overview()
                ).scheduler_status == "failed"
                await runner.close()
                assert (await operations.get_operations_overview()).stale
        finally:
            await database.close()

    asyncio.run(verify())
