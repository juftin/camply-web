"""
Health check tests
"""

from collections.abc import AsyncGenerator
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.anyio
@pytest.mark.parametrize("path", ["/api/health", "/api/ping"])
async def test_health_check(test_client: TestClient, path: str) -> None:
    """
    Test health check
    """
    response = test_client.get(path)
    assert response.status_code == 200
    json_response = response.json()
    assert json_response["status"] == 200


@pytest.mark.parametrize(
    "error", [ConnectionError("synthetic outage"), TimeoutError("synthetic timeout")]
)
def test_database_outage_blocks_readiness_only(
    test_client: TestClient, monkeypatch: pytest.MonkeyPatch, error: Exception
) -> None:
    """Database failures remove readiness without causing liveness restarts or leaking errors."""
    from camply.db.config import db
    from camply.server.app import app

    session = AsyncMock()
    session.execute.side_effect = error

    async def unavailable_session() -> AsyncGenerator[AsyncSession, None]:
        """Yield a synthetic failing database session."""
        yield session

    monkeypatch.setitem(app.dependency_overrides, db.yield_session, unavailable_session)
    ready = test_client.get("/api/health")
    assert ready.status_code == 503
    assert ready.json()["status"] == 503
    assert "synthetic" not in ready.text
    assert test_client.get("/api/ping").status_code == 200


def test_readiness_bounds_stalled_database(
    test_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A stalled query returns unavailable rather than occupying a probe indefinitely."""
    import asyncio
    import time

    from camply.db.config import db
    from camply.server.app import app

    async def stalled_query(*args: object) -> None:
        """Represent a connection that never completes within the probe budget."""
        await asyncio.sleep(30)

    session = AsyncMock()
    session.execute.side_effect = stalled_query

    async def unavailable_session() -> AsyncGenerator[AsyncSession, None]:
        """Yield a synthetic stalled session without opening a real database."""
        yield session

    monkeypatch.setitem(app.dependency_overrides, db.yield_session, unavailable_session)
    started = time.monotonic()
    assert test_client.get("/api/health").status_code == 503
    assert time.monotonic() - started < 5
