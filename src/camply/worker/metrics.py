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
from celery.signals import task_postrun, task_prerun, worker_process_shutdown

# Must configure the multiprocess directory BEFORE prometheus_client is first
# imported — the library checks env key presence at import time.
_multiproc_dir = (
    os.environ.get("CAMPLY_PROMETHEUS_MULTIPROC_DIR")
    or os.environ.get("PROMETHEUS_MULTIPROC_DIR")
    or os.environ.get("prometheus_multiproc_dir")
    or None
)
if _multiproc_dir:
    if not os.environ.get("PROMETHEUS_MULTIPROC_DIR"):
        os.environ["PROMETHEUS_MULTIPROC_DIR"] = _multiproc_dir
    os.makedirs(_multiproc_dir, exist_ok=True)
else:
    for _env_key in ("PROMETHEUS_MULTIPROC_DIR", "prometheus_multiproc_dir"):
        if os.environ.get(_env_key) == "":
            os.environ.pop(_env_key, None)

import prometheus_client  # noqa: E402
from prometheus_client import Counter, Gauge, Histogram, multiprocess  # noqa: E402
from prometheus_client.multiprocess import MultiProcessCollector  # noqa: E402

from camply.providers.transport_config import (  # noqa: E402
    TransportEvent,
    register_transport_observer,
)

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
    multiprocess_mode="livesum",
)

CAMPGROUND_API_ERRORS_TOTAL = Counter(
    f"{METRICS_PREFIX}_campground_api_errors_total",
    "Campground API errors by provider",
    labelnames=["provider"],
)

PROVIDER_CHECKS_TOTAL = Counter(
    f"{METRICS_PREFIX}_provider_checks_total",
    "Total provider availability checks attempted",
    labelnames=["provider", "status"],
)

TARGETS_CHECKED_TOTAL = Counter(
    f"{METRICS_PREFIX}_targets_checked_total",
    "Total target check executions",
)

APPLICATION_OUTCOMES_TOTAL = Counter(
    f"{METRICS_PREFIX}_application_outcomes_total",
    "Normalized application outcomes across worker tasks",
    labelnames=["task_name", "outcome"],
)

PROVIDER_COOLDOWN_WAITS_TOTAL = Counter(
    f"{METRICS_PREFIX}_provider_cooldown_waits_total",
    "Total provider cooldown and proxy exhaustion wait events",
    labelnames=["provider", "reason"],
)

PROVIDER_COOLDOWN_WAIT_SECONDS = Histogram(
    f"{METRICS_PREFIX}_provider_cooldown_wait_seconds",
    "Duration of provider cooldown waits in seconds",
    labelnames=["provider"],
    buckets=(0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0, 120.0),
)

PROVIDER_PROXY_EVENTS_TOTAL = Counter(
    f"{METRICS_PREFIX}_provider_proxy_events_total",
    "Total opt-in proxy rotation, quarantine, and exhaustion events",
    labelnames=["provider", "event", "reason"],
)

_PROXY_EVENT_NAMES: dict[str, str] = {
    "proxy_selected": "selected",
    "proxy_quarantined": "quarantined",
    "proxy_exhausted": "exhausted",
}


def _on_provider_transport_event(event: TransportEvent) -> None:
    """Record low-cardinality Prometheus metrics for provider transport events."""
    if event.kind == "cooldown_wait":
        PROVIDER_COOLDOWN_WAITS_TOTAL.labels(
            provider=event.provider,
            reason=event.reason,
        ).inc()
        if event.delay_seconds > 0.0:
            PROVIDER_COOLDOWN_WAIT_SECONDS.labels(
                provider=event.provider,
            ).observe(event.delay_seconds)
        return

    proxy_event = _PROXY_EVENT_NAMES.get(event.kind)
    if proxy_event is not None:
        PROVIDER_PROXY_EVENTS_TOTAL.labels(
            provider=event.provider,
            event=proxy_event,
            reason=event.reason,
        ).inc()


register_transport_observer(_on_provider_transport_event)


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
    status = state.lower()

    CELERY_TASKS_TOTAL.labels(task_name=task_name, status=status).inc()

    start = _task_start_times.pop(task_id, None)
    if start is not None:
        CELERY_TASK_DURATION_SECONDS.labels(task_name=task_name).observe(
            time.monotonic() - start
        )


@worker_process_shutdown.connect
def _on_worker_process_shutdown(pid: int | None = None, **kwargs: Any) -> None:
    """Clean up live-gauge multiprocess files when a prefork child exits."""
    if _multiproc_dir:
        try:
            multiprocess.mark_process_dead(pid or os.getpid(), path=_multiproc_dir)
        except OSError:
            pass


# ---------------------------------------------------------------------------
# Metrics HTTP server
# ---------------------------------------------------------------------------


def _is_pid_alive(pid: int) -> bool:
    """Return True when a process with the given PID exists."""
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def _cleanup_stale_multiproc_files(multiproc_dir: str) -> None:
    """Remove Prometheus multiprocess .db files left behind by dead processes."""
    current_pid = os.getpid()
    for fname in os.listdir(multiproc_dir):
        if not fname.endswith(".db"):
            continue
        pid_text = fname[:-3].rsplit("_", 1)[-1]
        try:
            pid = int(pid_text)
        except ValueError:
            continue
        if pid <= 0 or pid == current_pid or _is_pid_alive(pid):
            continue
        try:
            os.remove(os.path.join(multiproc_dir, fname))
        except OSError:
            pass


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
            _cleanup_stale_multiproc_files(_multiproc_dir)
            registry = prometheus_client.CollectorRegistry()
            MultiProcessCollector(registry)
            prometheus_client.start_http_server(port, addr="0.0.0.0", registry=registry)
        else:
            prometheus_client.start_http_server(port, addr="0.0.0.0")
        logger.info("Worker metrics server started", port=port)
    except Exception:
        logger.exception("Failed to start worker metrics server", port=port)
