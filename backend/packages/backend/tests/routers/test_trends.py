"""
Unit tests for the Admin Trends & Prometheus Proxy API.
"""

from __future__ import annotations

import uuid
from typing import Generator
from unittest.mock import AsyncMock, patch

import httpx
import pytest
from fastapi.testclient import TestClient

from backend.app import app
from backend.auth import CurrentUser, resolve_current_user
from backend.services.trends import _TRENDS_CACHE, get_admin_trends


@pytest.fixture(autouse=True)
def clear_trends_cache() -> None:
    """Ensure in-memory trends cache is cleared between tests."""
    _TRENDS_CACHE.clear()


@pytest.fixture
def admin_user() -> Generator[CurrentUser, None, None]:
    """Provide an authenticated admin user dependency override."""
    curr = CurrentUser(
        id=uuid.uuid4(),
        email="trends_admin@camply.local",
        is_early_access_user=True,
        is_admin=True,
        scanning_enabled=True,
    )
    app.dependency_overrides[resolve_current_user] = lambda: curr
    yield curr
    app.dependency_overrides.pop(resolve_current_user, None)


@pytest.fixture
def non_admin_user() -> Generator[CurrentUser, None, None]:
    """Provide an authenticated non-admin user dependency override."""
    curr = CurrentUser(
        id=uuid.uuid4(),
        email="trends_user@camply.local",
        is_early_access_user=True,
        is_admin=False,
        scanning_enabled=True,
    )
    app.dependency_overrides[resolve_current_user] = lambda: curr
    yield curr
    app.dependency_overrides.pop(resolve_current_user, None)


def test_trends_authorization_required(
    test_client: TestClient, non_admin_user: CurrentUser
) -> None:
    """Non-admin user cannot access trends endpoint."""
    resp = test_client.get("/api/admin/trends")
    assert resp.status_code == 403


def test_trends_usage_group_success(
    test_client: TestClient, admin_user: CurrentUser
) -> None:
    """Admin user can query usage trends with mocked Prometheus."""
    fake_prometheus_data = {
        "status": "success",
        "data": {
            "resultType": "matrix",
            "result": [
                {
                    "metric": {},
                    "values": [
                        [1760000000.0, "10"],
                        [1760000900.0, "15"],
                    ],
                }
            ],
        },
    }

    mock_resp = httpx.Response(
        status_code=200,
        json=fake_prometheus_data,
        request=httpx.Request("GET", "http://localhost:9090"),
    )

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_resp
        resp = test_client.get("/api/admin/trends?group=usage&range=24h")

    assert resp.status_code == 200
    data = resp.json()
    assert data["group"] == "usage"
    assert data["range"] == "24h"
    assert data["step_seconds"] == 900
    assert data["available"] is True
    assert data["error_message"] is None
    assert len(data["metrics"]) > 0

    # Check registered_users metric
    reg_users_m = next(
        (m for m in data["metrics"] if m["metric_id"] == "registered_users"),
        None,
    )
    assert reg_users_m is not None
    assert reg_users_m["unit"] == "users"
    assert len(reg_users_m["series"]) == 1
    assert reg_users_m["series"][0]["points"][0]["value"] == 10.0
    assert reg_users_m["series"][0]["points"][1]["value"] == 15.0


def test_trends_api_group_and_range_params(
    test_client: TestClient, admin_user: CurrentUser
) -> None:
    """Admin user can query api group trends over 7d."""
    fake_prometheus_data = {
        "status": "success",
        "data": {
            "resultType": "matrix",
            "result": [
                {
                    "metric": {"endpoint": "/api/scans"},
                    "values": [[1760000000.0, "2.5"]],
                }
            ],
        },
    }

    mock_resp = httpx.Response(
        status_code=200,
        json=fake_prometheus_data,
        request=httpx.Request("GET", "http://localhost:9090"),
    )

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_resp
        resp = test_client.get("/api/admin/trends?group=api&range=7d")

    assert resp.status_code == 200
    data = resp.json()
    assert data["group"] == "api"
    assert data["range"] == "7d"
    assert data["step_seconds"] == 3600
    assert data["available"] is True


def test_trends_worker_and_provider_groups(
    test_client: TestClient, admin_user: CurrentUser
) -> None:
    """Worker and provider groups execute their allowlisted queries."""
    fake_prometheus_data = {
        "status": "success",
        "data": {"resultType": "matrix", "result": []},
    }

    mock_resp = httpx.Response(
        status_code=200,
        json=fake_prometheus_data,
        request=httpx.Request("GET", "http://localhost:9090"),
    )

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_resp
        resp_worker = test_client.get("/api/admin/trends?group=worker&range=24h")
        assert resp_worker.status_code == 200
        assert resp_worker.json()["group"] == "worker"

        resp_provider = test_client.get("/api/admin/trends?group=provider&range=24h")
        assert resp_provider.status_code == 200
        assert resp_provider.json()["group"] == "provider"


def test_trends_prometheus_outage_handling(
    test_client: TestClient, admin_user: CurrentUser
) -> None:
    """When Prometheus is unreachable, returns 200 with available=False."""
    with patch(
        "httpx.AsyncClient.get",
        side_effect=httpx.ConnectError("Connection refused to Prometheus"),
    ):
        resp = test_client.get("/api/admin/trends?group=usage&range=24h")

    assert resp.status_code == 200
    data = resp.json()
    assert data["available"] is False
    assert data["metrics"] == []
    assert "Prometheus service unreachable" in data["error_message"]


@pytest.mark.asyncio
async def test_trends_caching() -> None:
    """Repeated calls within TTL use cached response."""
    with patch(
        "backend.services.trends._query_prometheus_range",
        new_callable=AsyncMock,
    ) as mock_query:
        mock_query.return_value = [{"metric": {}, "values": [[1760000000.0, "5.0"]]}]

        resp1 = await get_admin_trends(group="usage", range_param="24h")
        assert resp1.available is True

        # Second call should not invoke query again
        resp2 = await get_admin_trends(group="usage", range_param="24h")
        assert resp2.available is True
        assert resp1.metrics[0].title == resp2.metrics[0].title

        # Query should have been called only during the first pass
        call_count_1 = mock_query.call_count
        await get_admin_trends(group="usage", range_param="24h")
        assert mock_query.call_count == call_count_1


def test_trends_invalid_parameters(
    test_client: TestClient, admin_user: CurrentUser
) -> None:
    """Invalid group or range parameters are rejected with 422."""
    resp_bad_group = test_client.get("/api/admin/trends?group=arbitrary_promql")
    assert resp_bad_group.status_code == 422

    resp_bad_range = test_client.get("/api/admin/trends?range=100y")
    assert resp_bad_range.status_code == 422
