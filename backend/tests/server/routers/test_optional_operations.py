"""Keep admin operations usable when distributed dependencies are absent."""

from collections.abc import Generator
from unittest.mock import patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from camply.server.app import app
from camply.server.auth import CurrentUser, resolve_current_user
from camply.server.services import operations


@pytest.fixture
def missing_distributed() -> Generator[None, None, None]:
    """Simulate the dependency set of a server-only installation."""
    with (
        patch.object(operations, "Celery", None),
        patch.object(operations, "redis", None),
    ):
        yield


@pytest.fixture
def operations_admin() -> Generator[None, None, None]:
    """Authenticate a synthetic administrator for optional-feature requests."""
    user = CurrentUser(
        id=uuid4(),
        email="optional@example.test",
        is_admin=True,
        is_invited=True,
        scanning_enabled=True,
    )
    app.dependency_overrides[resolve_current_user] = lambda: user
    yield
    app.dependency_overrides.pop(resolve_current_user, None)


def test_server_only_operations_report_unavailable(
    test_client: TestClient,
    missing_distributed: None,
    operations_admin: None,
) -> None:
    """Missing worker support yields explicit unavailable data, without a broker."""
    overview = test_client.get("/api/admin/operations")
    assert overview.status_code == 200
    assert not overview.json()["inspection_available"]
    assert not overview.json()["telemetry_available"]
    assert not overview.json()["broker_connected"]
    assert overview.json()["stale"]
    assert "camply[distributed]" in overview.json()["error_message"]
    tasks = test_client.get("/api/admin/operations/tasks")
    assert tasks.status_code == 200
    assert not tasks.json()["available"]
    assert "camply[distributed]" in tasks.json()["error_message"]


def test_server_only_optional_actions_return_installation_hint(
    test_client: TestClient,
    missing_distributed: None,
    operations_admin: None,
) -> None:
    """Unavailable task detail and dispatch return 503 instead of missing-task 404."""
    for method, path in (
        ("get", "/api/admin/operations/tasks/synthetic-task"),
        ("post", "/api/admin/operations/sync-providers"),
    ):
        response = getattr(test_client, method)(path)
        assert response.status_code == 503
        assert "camply[distributed]" in response.json()["detail"]


def test_server_only_operations_preserve_authorization(
    test_client: TestClient,
    missing_distributed: None,
) -> None:
    """Dependency absence must not bypass admin permission checks."""
    user = CurrentUser(
        id=uuid4(),
        email="regular@example.test",
        is_admin=False,
        is_invited=True,
        scanning_enabled=True,
    )
    app.dependency_overrides[resolve_current_user] = lambda: user
    try:
        assert test_client.get("/api/admin/operations").status_code == 403
        assert test_client.get("/api/admin/operations/tasks").status_code == 403
        assert (
            test_client.get("/api/admin/operations/tasks/synthetic").status_code == 403
        )
        assert (
            test_client.post("/api/admin/operations/sync-providers").status_code == 403
        )
    finally:
        app.dependency_overrides.pop(resolve_current_user, None)
