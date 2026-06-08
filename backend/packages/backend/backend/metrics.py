"""
Prometheus metrics instrumentation for the FastAPI backend.

Uses prometheus_client multiprocess mode for gunicorn multi-worker
compatibility. Each worker writes metrics to a file in
PROMETHEUS_MULTIPROC_DIR; the /metrics endpoint aggregates them.
"""

import os
import time
from collections.abc import Awaitable, Callable
from typing import Any

# Must create the multiprocess directory BEFORE prometheus_client is first
# imported — the library checks the env var at import time.
_multiproc_dir = os.environ.get(
    "CAMPLY_PROMETHEUS_MULTIPROC_DIR",
    os.environ.get("PROMETHEUS_MULTIPROC_DIR"),
)
if _multiproc_dir:
    os.makedirs(_multiproc_dir, exist_ok=True)

import prometheus_client  # noqa: E402
import structlog  # noqa: E402
from fastapi import Response  # noqa: E402
from prometheus_client import Counter, Gauge, Histogram  # noqa: E402
from prometheus_client.multiprocess import MultiProcessCollector  # noqa: E402

logger = structlog.getLogger(__name__)

# ---------------------------------------------------------------------------
# Metric definitions
# ---------------------------------------------------------------------------

METRICS_PREFIX = "camply"

HTTP_REQUESTS_TOTAL = Counter(
    f"{METRICS_PREFIX}_http_requests_total",
    "Total HTTP requests",
    labelnames=["method", "endpoint", "status"],
)

HTTP_REQUEST_DURATION_SECONDS = Histogram(
    f"{METRICS_PREFIX}_http_request_duration_seconds",
    "HTTP request duration in seconds",
    labelnames=["method", "endpoint"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)

ACTIVE_USERS = Gauge(
    f"{METRICS_PREFIX}_active_users",
    "Number of active users in the database",
)

TOTAL_SCANS = Gauge(
    f"{METRICS_PREFIX}_total_scans",
    "Total number of user scans",
)

ACTIVE_SCANS = Gauge(
    f"{METRICS_PREFIX}_active_scans",
    "Number of currently active scans",
)

TOTAL_UNIQUE_TARGETS = Gauge(
    f"{METRICS_PREFIX}_total_unique_targets",
    "Total number of unique targets",
)

TOTAL_SEARCH_REQUESTS = Counter(
    f"{METRICS_PREFIX}_total_search_requests",
    "Total number of search requests",
)

SEARCH_DURATION_SECONDS = Histogram(
    f"{METRICS_PREFIX}_search_duration_seconds",
    "Search request duration in seconds",
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)

ACCESS_REQUESTS_TOTAL = Counter(
    f"{METRICS_PREFIX}_access_requests_total",
    "Total number of early access requests",
)


# ---------------------------------------------------------------------------
# DB-backed gauge refresh
# ---------------------------------------------------------------------------


async def refresh_db_gauges() -> None:
    """
    Query the database for current gauge values and update Prometheus gauges.

    This is called on each /metrics scrape so gauge values reflect the
    current DB state. Runs in a best-effort manner — failures are logged
    but do not block the metrics endpoint.
    """
    try:
        from sqlalchemy import func, select

        from db.config import db
        from db.models import UniqueTarget, User, UserScan

        async with db.get_session() as session:
            # Active users
            user_count_result = await session.execute(
                select(func.count()).select_from(User)
            )
            user_count = user_count_result.scalar() or 0
            ACTIVE_USERS.set(user_count)

            # Total scans
            scan_count_result = await session.execute(
                select(func.count()).select_from(UserScan)
            )
            scan_count = scan_count_result.scalar() or 0
            TOTAL_SCANS.set(scan_count)

            # Active scans
            active_scan_result = await session.execute(
                select(func.count())
                .select_from(UserScan)
                .where(
                    UserScan.is_active == True  # noqa: E712
                )
            )
            active_scan_count = active_scan_result.scalar() or 0
            ACTIVE_SCANS.set(active_scan_count)

            # Total unique targets
            target_count_result = await session.execute(
                select(func.count()).select_from(UniqueTarget)
            )
            target_count = target_count_result.scalar() or 0
            TOTAL_UNIQUE_TARGETS.set(target_count)

    except Exception:
        logger.exception("Failed to refresh DB-backed Prometheus gauges")


# ---------------------------------------------------------------------------
# Metrics middleware
# ---------------------------------------------------------------------------


class PrometheusMiddleware:
    """
    FastAPI middleware that instruments every HTTP request.

    Records request count (by method, endpoint, status) and duration
    (by method, endpoint). Skips the /metrics endpoint itself to avoid
    self-instrumentation noise.
    """

    def __init__(self, app: Any) -> None:
        self.app = app

    async def __call__(
        self,
        scope: dict[str, Any],
        receive: Callable[[], Awaitable[dict[str, Any]]],
        send: Callable[[dict[str, Any]], Awaitable[None]],
    ) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")
        method = scope.get("method", "")

        if path == "/metrics":
            await self.app(scope, receive, send)
            return

        start = time.monotonic()

        status_code = 500

        async def _send(message: dict[str, Any]) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
            await send(message)

        try:
            await self.app(scope, receive, _send)
        finally:
            duration = time.monotonic() - start
            endpoint = _normalize_path(path)

            HTTP_REQUESTS_TOTAL.labels(
                method=method,
                endpoint=endpoint,
                status=str(status_code),
            ).inc()
            HTTP_REQUEST_DURATION_SECONDS.labels(
                method=method,
                endpoint=endpoint,
            ).observe(duration)


def _normalize_path(path: str) -> str:
    """
    Normalize path for metric labels by replacing UUIDs and numeric IDs
    with placeholders to avoid cardinality explosion.
    """
    import re

    path = re.sub(
        r"/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
        "/:uuid",
        path,
    )
    path = re.sub(r"/\d+", "/:id", path)
    return path


# ---------------------------------------------------------------------------
# /metrics endpoint handler
# ---------------------------------------------------------------------------


def get_metrics_response() -> Response:
    """
    Produce the Prometheus metrics response.

    Uses MultiProcessCollector to aggregate metrics from all gunicorn
    workers when PROMETHEUS_MULTIPROC_DIR is configured; falls back to
    the default collector otherwise.
    """
    registry = prometheus_client.CollectorRegistry()

    if os.environ.get("PROMETHEUS_MULTIPROC_DIR"):
        MultiProcessCollector(registry)

    data = prometheus_client.generate_latest(registry)
    return Response(
        content=data,
        media_type="text/plain; charset=utf-8",
    )
