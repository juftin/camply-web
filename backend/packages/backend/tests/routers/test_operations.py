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
        is_invited=True,
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
        is_invited=True,
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
                    task_name="search.check-availability",
                    worker="celery@worker-1",
                    finished_at=dt.datetime.now(tz=dt.timezone.utc),
                    duration_ms=150.0,
                    entity_type="target",
                    entity_id=str(uuid.uuid4()),
                    outcome="success",
                    reason=None,
                    provider_id=1,
                    provider_name="Recreation.gov",
                    search_name="Lower Pines",
                    search_dates="2026-07-01 → 2026-07-03",
                )
            ],
            total=1,
        )

        with patch(
            "backend.routers.admin.get_recent_tasks",
            return_value=mock_tasks,
        ) as mock_get_recent:
            resp = test_client.get(
                "/api/admin/operations/tasks?limit=10&provider=recreation_gov&search=pines"
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["total"] == 1
            assert data["tasks"][0]["task_id"] == "task-1"
            assert data["tasks"][0]["outcome"] == "success"
            assert data["tasks"][0]["provider_id"] == 1
            assert data["tasks"][0]["provider_name"] == "Recreation.gov"
            assert data["tasks"][0]["search_name"] == "Lower Pines"
            assert data["tasks"][0]["search_dates"] == "2026-07-01 → 2026-07-03"
            mock_get_recent.assert_called_once_with(
                limit=10,
                offset=0,
                outcome=None,
                task_name=None,
                provider="recreation_gov",
                search="pines",
            )

    def test_get_task_detail_found_and_not_found(
        self, test_client: TestClient, admin_user: CurrentUser
    ) -> None:
        mock_detail = AdminOperationsTaskDetail(
            task_id="task-found",
            task_name="notifications.send-pushover",
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
            assert act_tot is None

    @pytest.mark.asyncio
    async def test_query_valkey_overview_failure(self) -> None:
        from backend.services.operations import _query_valkey_overview_sync

        with patch("backend.services.operations._get_redis_client") as mock_r:
            mock_r.side_effect = ConnectionError("Valkey unreachable")

            with pytest.raises(ConnectionError):
                _query_valkey_overview_sync()


@pytest.mark.asyncio
async def test_overview_outage_preserves_last_successful_snapshot() -> None:
    """Unavailable telemetry is marked stale without replacing known depth by zero."""
    from backend.services import operations

    with (
        patch.object(operations, "_cached_overview", None),
        patch.object(operations, "_cached_overview_time", 0),
    ):
        with (
            patch.object(
                operations, "_inspect_celery_sync", return_value=(True, [], 0, 0, 0)
            ),
            patch.object(
                operations, "_query_valkey_overview_sync", return_value=(7, None)
            ),
        ):
            healthy = await operations.get_operations_overview()
        operations._cached_overview_time = 0
        with (
            patch.object(
                operations, "_inspect_celery_sync", return_value=(False, [], 0, 0, 0)
            ),
            patch.object(
                operations,
                "_query_valkey_overview_sync",
                side_effect=ConnectionError("synthetic outage"),
            ),
        ):
            unavailable = await operations.get_operations_overview()
        assert unavailable.stale
        assert not unavailable.telemetry_available
        assert not unavailable.inspection_available
        assert not unavailable.broker_connected
        assert unavailable.queue_depth == 7
        assert unavailable.last_successful_at == healthy.last_successful_at


def test_partial_worker_inspection_retains_successful_replies() -> None:
    """A failed inspection call does not erase successful worker workload replies."""
    from backend.services.operations import _inspect_celery_sync

    with patch("backend.services.operations.Celery") as factory:
        inspector = factory.return_value.control.inspect.return_value
        inspector.ping.return_value = {"worker-1": {"ok": "pong"}}
        inspector.active.return_value = {"worker-1": [{"id": "synthetic-task"}]}
        inspector.reserved.side_effect = ConnectionError("synthetic outage")
        inspector.scheduled.return_value = {}
        available, workers, active, _, _ = _inspect_celery_sync()
    assert not available
    assert workers[0].name == "worker-1"
    assert active == 1


@pytest.mark.parametrize(
    "missing_reply", [None, {}, {"worker-1": {"error": "Unavailable"}}]
)
def test_unanswered_workload_is_unknown(missing_reply: dict | None) -> None:
    """Ping alone cannot establish that a worker has no running tasks."""
    from backend.services.operations import _inspect_celery_sync

    with patch("backend.services.operations.Celery") as factory:
        inspector = factory.return_value.control.inspect.return_value
        inspector.ping.return_value = {"worker-1": {"ok": "pong"}}
        inspector.active.return_value = missing_reply
        inspector.reserved.return_value = {"worker-1": []}
        inspector.scheduled.return_value = {"worker-1": []}
        available, workers, active, reserved, scheduled = _inspect_celery_sync()
    assert not available
    assert workers[0].active_tasks is None
    assert active is None
    assert reserved == scheduled == 0


def test_task_telemetry_outage_is_not_an_empty_success() -> None:
    """An unreadable telemetry stream exposes an outage rather than an idle queue."""
    from backend.services.operations import _get_recent_tasks_sync

    with patch(
        "backend.services.operations._get_redis_client",
        side_effect=ConnectionError("synthetic outage"),
    ):
        response = _get_recent_tasks_sync()
    assert not response.available
    assert response.error_message


def test_task_history_excludes_expired_records_and_identifies_attempts() -> None:
    """Legacy retry records have distinct event IDs and obey the visible 24-hour window."""
    from backend.services.operations import _get_recent_tasks_sync

    now = dt.datetime.now(tz=dt.timezone.utc)

    def record(finished_at: dt.datetime, outcome: str) -> dict[str, str]:
        """Build a synthetic telemetry record from a previous producer version."""
        return {
            "task_id": "same-task",
            "task_name": "synthetic.task",
            "finished_at": finished_at.isoformat(),
            "outcome": outcome,
        }

    with patch("backend.services.operations._get_redis_client") as client:
        client.return_value.xrevrange.return_value = [
            ("3-0", record(now, "success")),
            ("2-0", record(now - dt.timedelta(minutes=1), "retrying")),
            ("1-0", record(now - dt.timedelta(hours=25), "error")),
        ]
        response = _get_recent_tasks_sync()
    assert response.total == 2
    assert [task.event_id for task in response.tasks] == ["3-0", "2-0"]
    assert response.tasks[0].attempt is None


def test_idle_worker_reports_measured_zero() -> None:
    """Empty task lists from a responding worker are measured zeros."""
    from backend.services.operations import _inspect_celery_sync

    with patch("backend.services.operations.Celery") as factory:
        inspector = factory.return_value.control.inspect.return_value
        inspector.ping.return_value = {"worker-1": {"ok": "pong"}}
        for method in ("active", "reserved", "scheduled"):
            getattr(inspector, method).return_value = {"worker-1": []}
        available, _, active, reserved, scheduled = _inspect_celery_sync()
    assert available
    assert active == reserved == scheduled == 0
