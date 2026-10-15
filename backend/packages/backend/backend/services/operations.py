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
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Optional

import structlog

from backend.config import RuntimeMode, backend_config

if backend_config.runtime_mode == RuntimeMode.DISTRIBUTED:
    import redis
    from celery import Celery

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


def _inspect_celery_sync() -> tuple[
    bool, list[AdminWorkerItem], int | None, int | None, int | None
]:
    """
    Synchronously query Celery broker & workers using control inspection.
    Returns inspection completeness, responding workers, and workload totals.
    A missing worker response yields an unknown count rather than zero.
    """
    try:
        app = Celery("camply_inspect", broker=backend_config.valkey_url)
        app.conf.broker_connection_timeout = 2.0
        inspect = app.control.inspect(timeout=2.0)

        # Independent inspections share the deadline, retaining successful replies.
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = [
                executor.submit(getattr(inspect, method))
                for method in ("ping", "active", "reserved", "scheduled")
            ]
            replies = []
            complete = True
            for future in futures:
                try:
                    reply = future.result()
                    if not isinstance(reply, dict):
                        complete = False
                        reply = {}
                    replies.append(reply)
                except Exception:
                    complete = False
                    replies.append({})
        ping, active, reserved, scheduled = replies

        all_workers = (
            set(ping.keys())
            | set(active.keys())
            | set(reserved.keys())
            | set(scheduled.keys())
        )

        worker_items: list[AdminWorkerItem] = []

        for w_name in sorted(all_workers):
            act_count = (
                len(active[w_name]) if isinstance(active.get(w_name), list) else None
            )
            res_count = (
                len(reserved[w_name])
                if isinstance(reserved.get(w_name), list)
                else None
            )
            sch_count = (
                len(scheduled[w_name])
                if isinstance(scheduled.get(w_name), list)
                else None
            )
            if w_name not in ping or any(
                count is None for count in (act_count, res_count, sch_count)
            ):
                complete = False

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

        totals = [
            sum(len(reply[name]) for name in all_workers)
            if all_workers
            and all(isinstance(reply.get(name), list) for name in all_workers)
            else None
            for reply in (active, reserved, scheduled)
        ]
        return (
            complete and bool(all_workers),
            worker_items,
            totals[0],
            totals[1],
            totals[2],
        )
    except Exception:
        logger.warning("Failed to inspect Celery workers", exc_info=True)
        return False, [], None, None, None


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
        raise


async def get_operations_overview() -> AdminOperationsResponse:
    """
    Return the current operations overview snapshot, cached for 10 seconds.
    """
    if backend_config.runtime_mode == RuntimeMode.STANDALONE:
        from backend.services import local_operations

        return await local_operations.get_operations_overview()
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

        results = await asyncio.gather(
            asyncio.wait_for(asyncio.to_thread(_inspect_celery_sync), timeout=4.0),
            asyncio.wait_for(
                asyncio.to_thread(_query_valkey_overview_sync), timeout=4.0
            ),
            return_exceptions=True,
        )
        previous = _cached_overview
        inspection = results[0]
        telemetry = results[1]
        inspection_available = (
            not isinstance(inspection, BaseException) and inspection[0]
        )
        telemetry_available = not isinstance(telemetry, BaseException)
        workers: list[AdminWorkerItem]
        if isinstance(inspection, BaseException):
            workers, act_tot, res_tot, sch_tot = [], None, None, None
        else:
            _, workers, act_tot, res_tot, sch_tot = inspection
        if not inspection_available and not workers and previous:
            workers = previous.workers
            act_tot, res_tot, sch_tot = (
                previous.active_tasks_total,
                previous.reserved_tasks_total,
                previous.scheduled_tasks_total,
            )
        if isinstance(telemetry, BaseException):
            depth = previous.queue_depth if previous else 0
            disc_meta = previous.last_discovery if previous else None
        else:
            depth, disc_meta = telemetry
        timestamp = dt.datetime.now(tz=dt.timezone.utc)
        stale = not (inspection_available and telemetry_available)
        errors = []
        if not inspection_available:
            errors.append("Worker inspection unavailable or incomplete")
        if not telemetry_available:
            errors.append("Queue and discovery telemetry unavailable")
        snapshot = AdminOperationsResponse(
            workers=workers,
            queue_depth=depth,
            active_tasks_total=act_tot,
            reserved_tasks_total=res_tot,
            scheduled_tasks_total=sch_tot,
            last_discovery=disc_meta,
            broker_connected=telemetry_available,
            inspection_available=inspection_available,
            telemetry_available=telemetry_available,
            stale=stale,
            last_successful_at=(previous.last_successful_at if previous else None)
            if stale
            else timestamp,
            error_message="; ".join(errors) or None,
            snapshot_at=timestamp,
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
        provider_id_raw = d.get("provider_id")
        provider_id = (
            int(provider_id_raw)
            if provider_id_raw is not None and str(provider_id_raw).isdigit()
            else None
        )
        return AdminTaskTelemetryItem(
            task_id=str(d.get("task_id", "")),
            event_id=d.get("event_id") or None,
            attempt=int(d["attempt"]) if d.get("attempt") else None,
            task_name=str(d.get("task_name", "unknown")),
            worker=str(d.get("worker", "unknown")),
            finished_at=fin_dt,
            duration_ms=float(d.get("duration_ms", 0.0)),
            entity_type=d.get("entity_type") or None,
            entity_id=d.get("entity_id") or None,
            outcome=str(d.get("outcome", "unknown")),
            reason=d.get("reason") or None,
            provider_id=provider_id,
            provider_name=d.get("provider_name") or None,
            search_name=d.get("search_name") or None,
            search_dates=d.get("search_dates") or None,
        )
    except Exception:
        return None


def _matches_provider(item: AdminTaskTelemetryItem, provider: str) -> bool:
    """
    Check if a task item matches the specified provider filter.

    Parameters
    ----------
    item : AdminTaskTelemetryItem
        The parsed task telemetry record.
    provider : str
        The requested provider query string.

    Returns
    -------
    bool
        True if the item matches the provider query, False otherwise.
    """
    prov_query = provider.strip().lower().replace("_", "")
    if item.provider_id is not None and str(item.provider_id) == provider.strip():
        return True
    if item.provider_name:
        normalized_name = (
            item.provider_name.lower()
            .replace(" ", "")
            .replace(".", "")
            .replace("_", "")
        )
        if prov_query in normalized_name or prov_query in item.provider_name.lower():
            return True
    return False


def _matches_task_filters(
    item: AdminTaskTelemetryItem,
    oldest_timestamp: dt.datetime,
    task_name: Optional[str] = None,
    outcome: Optional[str] = None,
    provider: Optional[str] = None,
    search: Optional[str] = None,
) -> bool:
    """
    Check if a task telemetry record matches all applied query filters.

    Parameters
    ----------
    item : AdminTaskTelemetryItem
        The parsed task telemetry record.
    oldest_timestamp : dt.datetime
        Oldest allowable timestamp.
    task_name : Optional[str]
        Substring filter for task name.
    outcome : Optional[str]
        Filter for execution outcome.
    provider : Optional[str]
        Filter for provider name or id.
    search : Optional[str]
        Fuzzy search query.

    Returns
    -------
    bool
        True if item passes all active filters.
    """
    if item.finished_at < oldest_timestamp:
        return False
    if task_name and task_name not in item.task_name:
        return False
    if outcome and item.outcome != outcome:
        return False
    if provider and not _matches_provider(item, provider):
        return False
    if search:
        s_query = search.strip().lower()
        searchable_text = f"{item.search_name or ''} {item.search_dates or ''} {item.entity_id or ''} {item.task_name}".lower()
        if s_query not in searchable_text:
            return False
    return True


def _get_recent_tasks_sync(
    limit: int = 50,
    offset: int = 0,
    task_name: Optional[str] = None,
    outcome: Optional[str] = None,
    provider: Optional[str] = None,
    search: Optional[str] = None,
) -> AdminOperationsTasksResponse:
    """
    Synchronously read recent task records from Valkey stream.

    Parameters
    ----------
    limit : int
        Maximum number of tasks to return.
    offset : int
        Offset for pagination.
    task_name : Optional[str]
        Optional filter for task name.
    outcome : Optional[str]
        Optional filter for task outcome.
    provider : Optional[str]
        Optional filter for provider.
    search : Optional[str]
        Optional search keyword.

    Returns
    -------
    AdminOperationsTasksResponse
        Paginated recent task executions.
    """
    try:
        r = _get_redis_client()
        # Fetch up to 1000 recent items from stream
        raw_items_res = r.xrevrange(STREAM_KEY, max="+", min="-", count=1000)
        raw_items: list[Any] = raw_items_res if isinstance(raw_items_res, list) else []

        oldest_timestamp = dt.datetime.now(tz=dt.timezone.utc) - dt.timedelta(hours=24)
        parsed: list[AdminTaskTelemetryItem] = []
        for _msg_id, fields in raw_items:
            item = _parse_telemetry_dict(fields)
            if item is None:
                continue
            if item.event_id is None:
                item.event_id = str(_msg_id)
            if item.finished_at.tzinfo is None:
                item.finished_at = item.finished_at.replace(tzinfo=dt.timezone.utc)
            if not _matches_task_filters(
                item=item,
                oldest_timestamp=oldest_timestamp,
                task_name=task_name,
                outcome=outcome,
                provider=provider,
                search=search,
            ):
                continue
            parsed.append(item)

        total = len(parsed)
        sliced = parsed[offset : offset + limit]
        return AdminOperationsTasksResponse(tasks=sliced, total=total)
    except Exception:
        logger.warning("Failed to read task telemetry from Valkey", exc_info=True)
        return AdminOperationsTasksResponse(
            tasks=[],
            total=0,
            available=False,
            error_message="Task telemetry unavailable; retry when Valkey is reachable.",
        )


async def get_recent_tasks(
    limit: int = 50,
    offset: int = 0,
    task_name: Optional[str] = None,
    outcome: Optional[str] = None,
    provider: Optional[str] = None,
    search: Optional[str] = None,
) -> AdminOperationsTasksResponse:
    """
    Fetch bounded recent task executions with optional filters.
    """
    if backend_config.runtime_mode == RuntimeMode.STANDALONE:
        from backend.services import local_operations

        return await local_operations.get_recent_tasks(
            limit=limit,
            offset=offset,
            task_name=task_name,
            outcome=outcome,
            provider=provider,
            search=search,
        )
    return await asyncio.to_thread(
        _get_recent_tasks_sync,
        limit=limit,
        offset=offset,
        task_name=task_name,
        outcome=outcome,
        provider=provider,
        search=search,
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
                    event_id=item.event_id,
                    attempt=item.attempt,
                    task_name=item.task_name,
                    worker=item.worker,
                    finished_at=item.finished_at,
                    duration_ms=item.duration_ms,
                    entity_type=item.entity_type,
                    entity_id=item.entity_id,
                    outcome=item.outcome,
                    reason=item.reason,
                    provider_id=item.provider_id,
                    provider_name=item.provider_name,
                    search_name=item.search_name,
                    search_dates=item.search_dates,
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
    if backend_config.runtime_mode == RuntimeMode.STANDALONE:
        from backend.services import local_operations

        return await local_operations.get_task_detail(task_id)
    return await asyncio.to_thread(_get_task_detail_sync, task_id=task_id)


def dispatch_sync_all_providers() -> str:
    """
    Dispatch the camply.catalog.sync_all_providers Celery task.

    Returns
    -------
    str
        The Celery task ID of the dispatched task.
    """
    app = Celery("camply_backend", broker=backend_config.valkey_url)
    app.conf.broker_connection_timeout = 2.0
    task = app.send_task("camply.catalog.sync_all_providers", queue="celery")
    return str(task.id)


async def trigger_provider_sync() -> str:
    """
    Asynchronously trigger the sync_all_providers background task.

    Returns
    -------
    str
        The dispatched task ID.
    """
    if backend_config.runtime_mode == RuntimeMode.STANDALONE:
        from backend.services import local_operations

        return await local_operations.trigger_provider_sync()
    return await asyncio.to_thread(dispatch_sync_all_providers)
