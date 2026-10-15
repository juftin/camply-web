"""Read local runner state without importing a broker or monitoring client."""

import datetime as dt

from fastapi import HTTPException
from sqlalchemy import func, select

from backend.schemas import (
    AdminDiscoveryMetadata,
    AdminOperationsResponse,
    AdminOperationsTaskDetail,
    AdminOperationsTasksResponse,
    AdminTaskTelemetryItem,
    AdminWorkerItem,
    RuntimeCapabilities,
)
from db.models import NotificationOutbox
from worker.runtime import LocalRunner

runner: LocalRunner | None = None
("""Lifespan-owned runtime, absent during schema export and unit-level API imports.""")


def get_runner() -> LocalRunner:
    """Require a running application lifespan for local operations."""
    if runner is None:
        raise HTTPException(status_code=503, detail="Local runner is not initialized")
    return runner


async def get_operations_overview() -> AdminOperationsResponse:
    """Report local health and measured workload, without pretending a broker exists."""
    local = get_runner()
    now = dt.datetime.now(dt.timezone.utc)
    async with local.database.get_session() as session:
        pending = (
            await session.scalar(
                select(func.count())
                .select_from(NotificationOutbox)
                .where(
                    NotificationOutbox.status.in_(["pending", "retry"]),
                    NotificationOutbox.next_attempt_at <= now,
                )
            )
            or 0
        )
        sending = (
            await session.scalar(
                select(func.count())
                .select_from(NotificationOutbox)
                .where(NotificationOutbox.status == "sending")
            )
            or 0
        )
    healthy = local.healthy
    active = local.active + sending if healthy else None
    return AdminOperationsResponse(
        runtime_mode="standalone",
        capabilities=RuntimeCapabilities(
            broker=False, historical_trends=False, persistent_job_history=False
        ),
        scheduler_status="stopping"
        if local.stopping
        else "running"
        if healthy
        else "failed",
        workers=[
            AdminWorkerItem(
                name="local",
                status="online" if healthy else "unresponsive",
                active_tasks=active,
                reserved_tasks=None,
                scheduled_tasks=None,
            )
        ],
        queue_depth=local.scan_queue.qsize() + local.catalog_queue.qsize() + pending,
        active_tasks_total=active,
        reserved_tasks_total=None,
        scheduled_tasks_total=None,
        last_discovery=AdminDiscoveryMetadata.model_validate(local.last_discovery)
        if local.last_discovery
        else None,
        broker_connected=None,
        snapshot_at=now,
        inspection_available=healthy,
        telemetry_available=True,
        stale=not healthy,
        last_successful_at=local.last_discovery["timestamp"]
        if local.last_discovery
        else None,
        error_message=None if healthy else "Local scheduler is not running",
    )


async def get_recent_tasks(
    limit: int = 50,
    offset: int = 0,
    task_name: str | None = None,
    outcome: str | None = None,
    provider: str | None = None,
    search: str | None = None,
) -> AdminOperationsTasksResponse:
    """Apply the existing task-history filters to bounded local attempt records."""
    items = [
        AdminTaskTelemetryItem.model_validate(row) for row in get_runner().recent()
    ]
    if task_name:
        items = [item for item in items if task_name in item.task_name]
    if outcome:
        items = [item for item in items if item.outcome == outcome]
    if provider:
        items = [
            item
            for item in items
            if provider == str(item.provider_id)
            or provider.lower() in (item.provider_name or "").lower()
        ]
    if search:
        items = [
            item
            for item in items
            if search.lower()
            in f"{item.search_name} {item.search_dates} {item.entity_id} {item.task_name}".lower()
        ]
    return AdminOperationsTasksResponse(
        tasks=items[offset : offset + limit], total=len(items)
    )


async def get_task_detail(task_id: str) -> AdminOperationsTaskDetail | None:
    """Return the newest retained attempt for a local job identity."""
    for row in get_runner().recent():
        if row["task_id"] == task_id:
            return AdminOperationsTaskDetail.model_validate(row)
    return None


async def trigger_provider_sync() -> str:
    """Share an active local catalog refresh rather than enqueue duplicates."""
    local = get_runner()
    if not local.healthy:
        raise HTTPException(status_code=503, detail="Local scheduler is not running")
    return local.request_sync()
