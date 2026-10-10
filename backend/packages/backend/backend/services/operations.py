"""
Read-only background operations inspection service.

Inspects Celery workers and reads task telemetry from Valkey without
importing worker task definitions or registering worker signals.
"""

from __future__ import annotations

import asyncio
import datetime as dt
import json
import time
from typing import Any, Optional

import redis
import structlog
from celery import Celery

from backend.config import backend_config
from backend.schemas import (
    AdminDiscoveryMetadata,
    AdminOperationsResponse,
    AdminOperationsTaskDetail,
    AdminOperationsTasksResponse,
    AdminTaskTelemetryItem,
    AdminWorkerItem,
)

logger = structlog.getLogger(__name__)

STREAM_KEY = "camply:telemetry:tasks"
TASK_KEY_PREFIX = "camply:telemetry:task:"
DISCOVERY_LAST_KEY = "camply:telemetry:discovery:last"

# 10-second in-memory snapshot cache
_cached_overview: Optional[AdminOperationsResponse] = None
_cached_overview_time: float = 0.0
_cache_lock = asyncio.Lock()


def _get_redis_client() -> redis.Redis:
    """Create a short-lived sync Redis client with a 2-second timeout."""
    return redis.Redis.from_url(
        backend_config.valkey_url,
        decode_responses=True,
        socket_timeout=2.0,
        socket_connect_timeout=2.0,
    )


def _inspect_celery_sync() -> tuple[bool, list[AdminWorkerItem], int, int, int]:
    """
    Synchronously query Celery broker & workers using control inspection.
    Returns (broker_connected, workers, active_total, reserved_total, scheduled_total).
    """
    try:
        app = Celery("camply_inspect", broker=backend_config.valkey_url)
        app.conf.broker_connection_timeout = 2.0
        inspect = app.control.inspect(timeout=2.0)

        ping = inspect.ping() or {}
        active = inspect.active() or {}
        reserved = inspect.reserved() or {}
        scheduled = inspect.scheduled() or {}

        all_workers = (
            set(ping.keys())
            | set(active.keys())
            | set(reserved.keys())
            | set(scheduled.keys())
        )

        worker_items: list[AdminWorkerItem] = []
        active_total = 0
        reserved_total = 0
        scheduled_total = 0

        for w_name in sorted(all_workers):
            act_count = len(active.get(w_name, []))
            res_count = len(reserved.get(w_name, []))
            sch_count = len(scheduled.get(w_name, []))

            active_total += act_count
            reserved_total += res_count
            scheduled_total += sch_count

            is_online = w_name in ping
            worker_items.append(
                AdminWorkerItem(
                    name=w_name,
                    status="online" if is_online else "unresponsive",
                    active_tasks=act_count,
                    reserved_tasks=res_count,
                    scheduled_tasks=sch_count,
                )
            )

        return True, worker_items, active_total, reserved_total, scheduled_total
    except Exception:
        logger.warning("Failed to inspect Celery workers", exc_info=True)
        return False, [], 0, 0, 0


def _query_valkey_overview_sync() -> tuple[int, Optional[AdminDiscoveryMetadata]]:
    """
    Synchronously query Valkey for queue depth and discovery metadata.
    """
    try:
        r = _get_redis_client()
        raw_depth = r.llen("celery")
        depth = int(raw_depth) if isinstance(raw_depth, int) else 0
        raw_disc = r.get(DISCOVERY_LAST_KEY)

        disc_meta: Optional[AdminDiscoveryMetadata] = None
        if raw_disc and isinstance(raw_disc, str):
            try:
                data = json.loads(raw_disc)
                disc_meta = AdminDiscoveryMetadata(
                    timestamp=dt.datetime.fromisoformat(data["timestamp"]),
                    targets_discovered=data.get("targets_discovered", 0),
                    targets_enqueued=data.get("targets_enqueued", 0),
                    status=data.get("status", "unknown"),
                )
            except Exception:
                pass

        return depth, disc_meta
    except Exception:
        logger.warning("Failed to query Valkey for operations overview", exc_info=True)
        return 0, None


async def get_operations_overview() -> AdminOperationsResponse:
    """
    Return the current operations overview snapshot, cached for 10 seconds.
    """
    global _cached_overview, _cached_overview_time

    now_mono = time.monotonic()
    if _cached_overview is not None and (now_mono - _cached_overview_time) < 10.0:
        return _cached_overview

    async with _cache_lock:
        if (
            _cached_overview is not None
            and (time.monotonic() - _cached_overview_time) < 10.0
        ):
            return _cached_overview

        # Run blocking inspect in thread executor with a 4-second deadline
        try:
            connected, workers, act_tot, res_tot, sch_tot = await asyncio.wait_for(
                asyncio.to_thread(_inspect_celery_sync),
                timeout=4.0,
            )
        except asyncio.TimeoutError:
            connected, workers, act_tot, res_tot, sch_tot = False, [], 0, 0, 0

        try:
            depth, disc_meta = await asyncio.wait_for(
                asyncio.to_thread(_query_valkey_overview_sync),
                timeout=2.0,
            )
        except asyncio.TimeoutError:
            depth, disc_meta = 0, None

        snapshot = AdminOperationsResponse(
            workers=workers,
            queue_depth=depth,
            active_tasks_total=act_tot,
            reserved_tasks_total=res_tot,
            scheduled_tasks_total=sch_tot,
            last_discovery=disc_meta,
            broker_connected=connected,
            snapshot_at=dt.datetime.now(tz=dt.timezone.utc),
        )

        _cached_overview = snapshot
        _cached_overview_time = time.monotonic()
        return snapshot


def _parse_telemetry_dict(d: dict[str, Any]) -> Optional[AdminTaskTelemetryItem]:
    """Parse raw stream/json mapping to AdminTaskTelemetryItem."""
    try:
        finished_str = d.get("finished_at")
        if not finished_str:
            return None
        fin_dt = dt.datetime.fromisoformat(finished_str)
        return AdminTaskTelemetryItem(
            task_id=str(d.get("task_id", "")),
            task_name=str(d.get("task_name", "unknown")),
            worker=str(d.get("worker", "unknown")),
            finished_at=fin_dt,
            duration_ms=float(d.get("duration_ms", 0.0)),
            entity_type=d.get("entity_type") or None,
            entity_id=d.get("entity_id") or None,
            outcome=str(d.get("outcome", "unknown")),
            reason=d.get("reason") or None,
        )
    except Exception:
        return None


def _get_recent_tasks_sync(
    limit: int = 50,
    offset: int = 0,
    task_name: Optional[str] = None,
    outcome: Optional[str] = None,
) -> AdminOperationsTasksResponse:
    """
    Synchronously read recent task records from Valkey stream.
    """
    try:
        r = _get_redis_client()
        # Fetch up to 500 recent items from stream
        raw_items_res = r.xrevrange(STREAM_KEY, max="+", min="-", count=500)
        raw_items: list[Any] = raw_items_res if isinstance(raw_items_res, list) else []

        parsed: list[AdminTaskTelemetryItem] = []
        for _msg_id, fields in raw_items:
            item = _parse_telemetry_dict(fields)
            if item is None:
                continue
            if task_name and task_name not in item.task_name:
                continue
            if outcome and item.outcome != outcome:
                continue
            parsed.append(item)

        total = len(parsed)
        sliced = parsed[offset : offset + limit]
        return AdminOperationsTasksResponse(tasks=sliced, total=total)
    except Exception:
        logger.warning("Failed to read task telemetry from Valkey", exc_info=True)
        return AdminOperationsTasksResponse(tasks=[], total=0)


async def get_recent_tasks(
    limit: int = 50,
    offset: int = 0,
    task_name: Optional[str] = None,
    outcome: Optional[str] = None,
) -> AdminOperationsTasksResponse:
    """
    Fetch bounded recent task executions with optional filters.
    """
    return await asyncio.to_thread(
        _get_recent_tasks_sync,
        limit=limit,
        offset=offset,
        task_name=task_name,
        outcome=outcome,
    )


def _get_task_detail_sync(task_id: str) -> Optional[AdminOperationsTaskDetail]:
    """
    Look up a single task by ID from Valkey index key.
    """
    try:
        r = _get_redis_client()
        raw = r.get(f"{TASK_KEY_PREFIX}{task_id}")
        if raw and isinstance(raw, str):
            data = json.loads(raw)
            item = _parse_telemetry_dict(data)
            if item:
                return AdminOperationsTaskDetail(
                    task_id=item.task_id,
                    task_name=item.task_name,
                    worker=item.worker,
                    finished_at=item.finished_at,
                    duration_ms=item.duration_ms,
                    entity_type=item.entity_type,
                    entity_id=item.entity_id,
                    outcome=item.outcome,
                    reason=item.reason,
                )
    except Exception:
        logger.warning(
            "Failed to lookup task detail in Valkey", task_id=task_id, exc_info=True
        )
    return None


async def get_task_detail(task_id: str) -> Optional[AdminOperationsTaskDetail]:
    """
    Fetch single task execution detail by ID.
    """
    return await asyncio.to_thread(_get_task_detail_sync, task_id=task_id)
