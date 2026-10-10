"""
Worker Task Telemetry: records task lifecycle and application outcomes in Valkey.

Maintains:
- Bounded stream `camply:telemetry:tasks` (capped at 1,000 records).
- Task index `camply:telemetry:task:{task_id}` (TTL 24 hours).
- Last discovery metadata `camply:telemetry:discovery:last` (TTL 7 days).
"""

import datetime as dt
import json
import time
from typing import Any, Optional

import redis
import structlog
from celery.exceptions import Retry
from celery.signals import task_failure, task_postrun, task_prerun, task_retry

from worker.config import worker_config

logger = structlog.getLogger(__name__)

STREAM_KEY = "camply:telemetry:tasks"
TASK_KEY_PREFIX = "camply:telemetry:task:"
DISCOVERY_LAST_KEY = "camply:telemetry:discovery:last"

MAX_STREAM_LEN = 1000
TASK_TTL_SECONDS = 86400  # 24 hours
DISCOVERY_TTL_SECONDS = 604800  # 7 days

_redis_client: Optional[redis.Redis] = None


def get_redis_client() -> redis.Redis:
    """
    Get or initialize a synchronous Redis/Valkey client.
    """
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.Redis.from_url(
            worker_config.valkey_url,
            decode_responses=True,
            socket_timeout=2.0,
            socket_connect_timeout=2.0,
        )
    return _redis_client


# Track task start times in memory
_active_task_starts: dict[str, float] = {}


def _extract_entity_info(
    kwargs: dict[str, Any], args: tuple[Any, ...]
) -> tuple[Optional[str], Optional[str]]:
    """Extract safe entity_type and entity_id from task arguments."""
    if "target_id" in kwargs:
        return "target", str(kwargs["target_id"])
    if "scan_id" in kwargs:
        return "scan", str(kwargs["scan_id"])
    if "user_id" in kwargs:
        return "user", str(kwargs["user_id"])
    return None, None


def _normalize_outcome(
    state: str, retval: Any, exception: Optional[BaseException] = None
) -> tuple[str, Optional[str]]:
    """
    Normalize Celery execution state + return value into safe application outcome.

    Returns (outcome, reason).
    """
    if isinstance(exception, Retry):
        return "retrying", "task_retry"
    if exception is not None:
        return "error", "exception"

    if state == "SUCCESS":
        if isinstance(retval, dict):
            status = retval.get("status")
            if status == "skipped":
                return "skipped", str(retval.get("reason", "skipped"))
            if status in ("error", "failed"):
                return "error", str(retval.get("reason", "task_error"))
        return "success", None

    if state == "FAILURE":
        return "error", "failure"
    if state == "RETRY":
        return "retrying", "task_retry"

    return "unknown", state


def record_task_execution(
    task_id: str,
    task_name: str,
    worker: str,
    start_time: float,
    finish_time: float,
    state: str,
    retval: Any = None,
    exception: Optional[BaseException] = None,
    args: tuple[Any, ...] = (),
    kwargs: Optional[dict[str, Any]] = None,
) -> None:
    """
    Record task execution metadata in Valkey stream and key index.
    Fails safely without raising exceptions to protect business tasks.
    """
    kwargs_dict = kwargs or {}
    entity_type, entity_id = _extract_entity_info(kwargs_dict, args)
    outcome, reason = _normalize_outcome(state, retval, exception)

    now = dt.datetime.now(tz=dt.timezone.utc)
    duration_ms = max(0.0, round((finish_time - start_time) * 1000, 2))

    record = {
        "task_id": task_id,
        "task_name": task_name,
        "worker": worker or "unknown",
        "finished_at": now.isoformat(),
        "duration_ms": duration_ms,
        "entity_type": entity_type or "",
        "entity_id": entity_id or "",
        "outcome": outcome,
        "reason": reason or "",
    }

    try:
        client = get_redis_client()
        # 1. Add to bounded stream with approximate trimming
        client.xadd(
            STREAM_KEY,
            record,  # type: ignore[arg-type]
            maxlen=MAX_STREAM_LEN,
            approximate=True,
        )
        # 2. Add to individual task lookup key with TTL
        client.setex(
            f"{TASK_KEY_PREFIX}{task_id}",
            TASK_TTL_SECONDS,
            json.dumps(record),
        )
    except Exception:
        logger.debug(
            "Failed to record task telemetry to Valkey", task_id=task_id, exc_info=True
        )

    try:
        from worker.metrics import APPLICATION_OUTCOMES_TOTAL

        APPLICATION_OUTCOMES_TOTAL.labels(task_name=task_name, outcome=outcome).inc()
    except Exception:
        pass


def record_discovery_completion(
    targets_discovered: int,
    targets_enqueued: int,
    status: str = "success",
) -> None:
    """
    Record the latest target discovery scheduler completion metadata.
    """
    now = dt.datetime.now(tz=dt.timezone.utc)
    metadata = {
        "timestamp": now.isoformat(),
        "targets_discovered": targets_discovered,
        "targets_enqueued": targets_enqueued,
        "status": status,
    }
    try:
        client = get_redis_client()
        client.setex(
            DISCOVERY_LAST_KEY,
            DISCOVERY_TTL_SECONDS,
            json.dumps(metadata),
        )
    except Exception:
        logger.debug("Failed to record discovery metadata to Valkey", exc_info=True)


# ---------------------------------------------------------------------------
# Celery Signal Handlers
# ---------------------------------------------------------------------------


@task_prerun.connect
def _on_telemetry_prerun(
    sender: Any = None, task_id: str = "", task: Any = None, **kwargs: Any
) -> None:
    """Capture task start time."""
    if task_id:
        _active_task_starts[task_id] = time.monotonic()


@task_postrun.connect
def _on_telemetry_postrun(
    sender: Any = None,
    task_id: str = "",
    task: Any = None,
    args: tuple[Any, ...] = (),
    kwargs: Optional[dict[str, Any]] = None,
    retval: Any = None,
    state: str = "UNKNOWN",
    **extra: Any,
) -> None:
    """Record task completion."""
    if not task_id:
        return
    finish_time = time.monotonic()
    start_time = _active_task_starts.pop(task_id, finish_time)
    task_name = getattr(task, "name", "unknown") if task else "unknown"
    worker_name = (
        getattr(getattr(task, "request", None), "hostname", "unknown") or "unknown"
    )

    record_task_execution(
        task_id=task_id,
        task_name=task_name,
        worker=worker_name,
        start_time=start_time,
        finish_time=finish_time,
        state=state,
        retval=retval,
        args=args,
        kwargs=kwargs,
    )


@task_retry.connect
def _on_telemetry_retry(
    sender: Any = None,
    task_id: str = "",
    reason: Any = None,
    einfo: Any = None,
    **extra: Any,
) -> None:
    """Record task retry outcome."""
    if not task_id:
        return
    finish_time = time.monotonic()
    start_time = _active_task_starts.get(task_id, finish_time)
    task_name = getattr(sender, "name", "unknown") if sender else "unknown"

    record_task_execution(
        task_id=task_id,
        task_name=task_name,
        worker="unknown",
        start_time=start_time,
        finish_time=finish_time,
        state="RETRY",
        exception=reason if isinstance(reason, BaseException) else None,
    )


@task_failure.connect
def _on_telemetry_failure(
    sender: Any = None,
    task_id: str = "",
    exception: Optional[BaseException] = None,
    args: tuple[Any, ...] = (),
    kwargs: Optional[dict[str, Any]] = None,
    einfo: Any = None,
    **extra: Any,
) -> None:
    """Record task failure."""
    if not task_id:
        return
    finish_time = time.monotonic()
    start_time = _active_task_starts.pop(task_id, finish_time)
    task_name = getattr(sender, "name", "unknown") if sender else "unknown"

    record_task_execution(
        task_id=task_id,
        task_name=task_name,
        worker="unknown",
        start_time=start_time,
        finish_time=finish_time,
        state="FAILURE",
        exception=exception,
        args=args,
        kwargs=kwargs,
    )
