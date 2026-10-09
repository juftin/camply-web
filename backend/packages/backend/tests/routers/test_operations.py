"""
Tests for read-only Operations inspection endpoints and services.
"""

from __future__ import annotations

import datetime as dt
import uuid
from typing import Generator
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from backend.app import app
from backend.auth import CurrentUser, resolve_current_user
from backend.schemas import (
    AdminDiscoveryMetadata,
    AdminOperationsResponse,
    AdminOperationsTaskDetail,
    AdminOperationsTasksResponse,
    AdminTaskTelemetryItem,
    AdminWorkerItem,
)


@pytest.fixture
def admin_user() -> Generator[CurrentUser, None, None]:
    curr = CurrentUser(
        id=uuid.uuid4(),
        email="ops_admin@camply.local",
        is_early_access_user=True,
        is_admin=True,
        scanning_enabled=True,
    )
    app.dependency_overrides[resolve_current_user] = lambda: curr
    yield curr
    app.dependency_overrides.pop(resolve_current_user, None)


@pytest.fixture
def non_admin_user() -> Generator[CurrentUser, None, None]:
    curr = CurrentUser(
        id=uuid.uuid4(),
        email="regular@camply.local",
        is_early_access_user=True,
        is_admin=False,
        scanning_enabled=True,
    )
    app.dependency_overrides[resolve_current_user] = lambda: curr
    yield curr
    app.dependency_overrides.pop(resolve_current_user, None)


class TestOperationsAuthorization:
    """Verify operations endpoints require administrator permissions."""

    def test_non_admin_forbidden(
        self, test_client: TestClient, non_admin_user: CurrentUser
    ) -> None:
        r1 = test_client.get("/api/admin/operations")
        assert r1.status_code == 403
        assert r1.json()["detail"]["error"] == "ERR_ADMIN_REQUIRED"

        r2 = test_client.get("/api/admin/operations/tasks")
        assert r2.status_code == 403

        r3 = test_client.get("/api/admin/operations/tasks/any-id")
        assert r3.status_code == 403

    def test_absence_of_mutation_routes(
        self, test_client: TestClient, admin_user: CurrentUser
    ) -> None:
        """Operations endpoints must be strictly read-only."""
        assert test_client.post("/api/admin/operations").status_code == 405
        assert test_client.put("/api/admin/operations").status_code == 405
        assert test_client.delete("/api/admin/operations").status_code == 405
        assert test_client.post("/api/admin/operations/tasks").status_code == 405


class TestOperationsEndpoints:
    """Verify operations inspection data and resilience."""

    def test_get_operations_overview(
        self, test_client: TestClient, admin_user: CurrentUser
    ) -> None:
        mock_overview = AdminOperationsResponse(
            workers=[
                AdminWorkerItem(
                    name="celery@worker-1",
                    status="online",
                    active_tasks=2,
                    reserved_tasks=1,
                    scheduled_tasks=0,
                )
            ],
            queue_depth=3,
            active_tasks_total=2,
            reserved_tasks_total=1,
            scheduled_tasks_total=0,
            last_discovery=AdminDiscoveryMetadata(
                timestamp=dt.datetime.now(tz=dt.timezone.utc),
                targets_discovered=5,
                targets_enqueued=5,
                status="success",
            ),
            broker_connected=True,
            snapshot_at=dt.datetime.now(tz=dt.timezone.utc),
        )

        with patch(
            "backend.routers.admin.get_operations_overview",
            return_value=mock_overview,
        ):
            resp = test_client.get("/api/admin/operations")
            assert resp.status_code == 200
            data = resp.json()
            assert data["broker_connected"] is True
            assert data["queue_depth"] == 3
            assert len(data["workers"]) == 1
            assert data["workers"][0]["name"] == "celery@worker-1"
            assert data["last_discovery"]["targets_discovered"] == 5

    def test_get_operations_tasks(
        self, test_client: TestClient, admin_user: CurrentUser
    ) -> None:
        mock_tasks = AdminOperationsTasksResponse(
            tasks=[
                AdminTaskTelemetryItem(
                    task_id="task-1",
                    task_name="worker.tasks.scanner.check_target_availability",
                    worker="celery@worker-1",
                    finished_at=dt.datetime.now(tz=dt.timezone.utc),
                    duration_ms=150.0,
                    entity_type="target",
                    entity_id=str(uuid.uuid4()),
                    outcome="success",
                    reason=None,
                )
            ],
            total=1,
        )

        with patch(
            "backend.routers.admin.get_recent_tasks",
            return_value=mock_tasks,
        ):
            resp = test_client.get("/api/admin/operations/tasks?limit=10")
            assert resp.status_code == 200
            data = resp.json()
            assert data["total"] == 1
            assert data["tasks"][0]["task_id"] == "task-1"
            assert data["tasks"][0]["outcome"] == "success"

    def test_get_task_detail_found_and_not_found(
        self, test_client: TestClient, admin_user: CurrentUser
    ) -> None:
        mock_detail = AdminOperationsTaskDetail(
            task_id="task-found",
            task_name="worker.tasks.notifications.send_alert",
            worker="celery@worker-1",
            finished_at=dt.datetime.now(tz=dt.timezone.utc),
            duration_ms=85.0,
            entity_type="scan",
            entity_id=str(uuid.uuid4()),
            outcome="success",
            reason=None,
        )

        with patch(
            "backend.routers.admin.get_task_detail",
            side_effect=lambda tid: mock_detail if tid == "task-found" else None,
        ):
            resp_found = test_client.get("/api/admin/operations/tasks/task-found")
            assert resp_found.status_code == 200
            assert resp_found.json()["task_id"] == "task-found"

            resp_missing = test_client.get("/api/admin/operations/tasks/task-missing")
            assert resp_missing.status_code == 404


class TestOperationsServiceResilience:
    """Test operations service resilience when broker or workers fail."""

    @pytest.mark.asyncio
    async def test_inspect_celery_broker_failure(self) -> None:
        from backend.services.operations import _inspect_celery_sync

        with patch("backend.services.operations.Celery") as mock_celery:
            mock_app = MagicMock()
            mock_app.control.inspect.side_effect = ConnectionError("Broker unreachable")
            mock_celery.return_value = mock_app

            connected, workers, act_tot, res_tot, sch_tot = _inspect_celery_sync()
            assert connected is False
            assert workers == []
            assert act_tot == 0

    @pytest.mark.asyncio
    async def test_query_valkey_overview_failure(self) -> None:
        from backend.services.operations import _query_valkey_overview_sync

        with patch("backend.services.operations._get_redis_client") as mock_r:
            mock_r.side_effect = ConnectionError("Valkey unreachable")

            depth, disc_meta = _query_valkey_overview_sync()
            assert depth == 0
            assert disc_meta is None
