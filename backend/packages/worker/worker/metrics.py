"""
Prometheus metrics instrumentation for the Celery worker.

Exposes a /metrics endpoint on a separate HTTP port (default 8001)
via prometheus_client's built-in HTTP server running in a daemon thread.
Celery signals (task_prerun, task_postrun) automatically capture task
execution counts and durations across all tasks.

When PROMETHEUS_MULTIPROC_DIR is set, uses prometheus_client's multiprocess
mode so metrics from all prefork worker children are aggregated via shared
.db files, matching the FastAPI backend's approach.
"""

import os
import time
from typing import Any

import structlog
from celery.signals import task_postrun, task_prerun

# Must create the multiprocess directory BEFORE prometheus_client is first
# imported — the library checks the env var at import time.
_multiproc_dir = os.environ.get(
    "CAMPLY_PROMETHEUS_MULTIPROC_DIR",
    os.environ.get("PROMETHEUS_MULTIPROC_DIR"),
)
if _multiproc_dir:
    os.makedirs(_multiproc_dir, exist_ok=True)
    # Clean stale .db files from previous runs to prevent metric accumulation
    for fname in os.listdir(_multiproc_dir):
        if fname.endswith(".db"):
            try:
                os.remove(os.path.join(_multiproc_dir, fname))
            except OSError:
                pass

import prometheus_client  # noqa: E402
from prometheus_client import Counter, Gauge, Histogram  # noqa: E402
from prometheus_client.multiprocess import MultiProcessCollector  # noqa: E402

logger = structlog.getLogger(__name__)

# ---------------------------------------------------------------------------
# Metric definitions
# ---------------------------------------------------------------------------

METRICS_PREFIX = "camply"

CELERY_TASKS_TOTAL = Counter(
    f"{METRICS_PREFIX}_celery_tasks_total",
    "Total celery task executions",
    labelnames=["task_name", "status"],
)

CELERY_TASK_DURATION_SECONDS = Histogram(
    f"{METRICS_PREFIX}_celery_task_duration_seconds",
    "Celery task duration in seconds",
    labelnames=["task_name"],
    buckets=(0.01, 0.05, 0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0, 120.0),
)

TARGETS_DISCOVERED_TOTAL = Counter(
    f"{METRICS_PREFIX}_targets_discovered_total",
    "Total targets discovered by heartbeat",
)

TARGETS_ENQUEUED_TOTAL = Counter(
    f"{METRICS_PREFIX}_targets_enqueued_total",
    "Total targets enqueued for scanning",
)

NOTIFICATIONS_SENT_TOTAL = Counter(
    f"{METRICS_PREFIX}_notifications_sent_total",
    "Total notifications sent",
)

LOCK_CONTENTION_TOTAL = Counter(
    f"{METRICS_PREFIX}_lock_contention_total",
    "Lock acquisition attempts",
    labelnames=["outcome"],
)

SCAN_RESULTS_STORED_TOTAL = Counter(
    f"{METRICS_PREFIX}_scan_results_stored_total",
    "Total scan results stored",
)

UNIQUE_TARGETS_CHECKED = Gauge(
    f"{METRICS_PREFIX}_unique_targets_checked",
    "Number of unique targets checked",
)

CAMPGROUND_API_ERRORS_TOTAL = Counter(
    f"{METRICS_PREFIX}_campground_api_errors_total",
    "Campground API errors by provider",
    labelnames=["provider"],
)


# ---------------------------------------------------------------------------
# Task timing storage (thread-local for asyncio.run safety)
# ---------------------------------------------------------------------------

_task_start_times: dict[str, float] = {}


@task_prerun.connect
def _on_task_prerun(
    sender: Any = None, task_id: str = "", task: Any = None, **kwargs: Any
) -> None:
    """Record task start time on prerun."""
    _task_start_times[task_id] = time.monotonic()


@task_postrun.connect
def _on_task_postrun(
    sender: Any = None,
    task_id: str = "",
    task: Any = None,
    state: str = "UNKNOWN",
    **kwargs: Any,
) -> None:
    """Record task execution count and duration on postrun."""
    task_name = task.name if task else "unknown"
    status = "success" if state == "SUCCESS" else "failure"

    CELERY_TASKS_TOTAL.labels(task_name=task_name, status=status).inc()

    start = _task_start_times.pop(task_id, None)
    if start is not None:
        CELERY_TASK_DURATION_SECONDS.labels(task_name=task_name).observe(
            time.monotonic() - start
        )


# ---------------------------------------------------------------------------
# Metrics HTTP server
# ---------------------------------------------------------------------------


def start_metrics_server(port: int = 8001) -> None:
    """
    Start a prometheus_client HTTP server in a daemon thread.

    When PROMETHEUS_MULTIPROC_DIR is configured, uses MultiProcessCollector
    to aggregate metrics from all prefork worker children via shared .db files.
    Otherwise falls back to the default in-process collector for single-worker
    setups (e.g. local development with --pool=solo).
    """
    try:
        if _multiproc_dir:
            registry = prometheus_client.CollectorRegistry()
            MultiProcessCollector(registry)
            prometheus_client.start_http_server(port, registry=registry)
        else:
            prometheus_client.start_http_server(port)
        logger.info("Worker metrics server started", port=port)
    except Exception:
        logger.exception("Failed to start worker metrics server", port=port)
