"""
Prometheus Trend Metrics Service.

Proxies fixed, allowlisted PromQL queries to an internal Prometheus server.
Strictly disallows arbitrary PromQL strings from clients.
Caches query results in memory to avoid redundant scraper load.
Gracefully degrades with available=False when Prometheus is unreachable.
"""

from __future__ import annotations

import datetime as dt
import math
import time
from typing import Any, Optional

import httpx
import structlog

from backend.config import backend_config
from backend.schemas import (
    AdminTrendsResponse,
    TrendMetric,
    TrendPoint,
    TrendSeries,
)

logger = structlog.getLogger(__name__)

# Bounded in-memory cache: (cache_key) -> (timestamp, AdminTrendsResponse)
_TRENDS_CACHE: dict[str, tuple[float, AdminTrendsResponse]] = {}
CACHE_TTL_SECONDS = 30.0

MAX_SERIES_PER_METRIC = 20


def _parse_step_and_range(range_param: str) -> tuple[int, int, str]:
    """
    Map range parameter to (duration_seconds, step_seconds, step_string).
    """
    if range_param == "7d":
        return 7 * 86400, 3600, "1h"
    elif range_param == "30d":
        return 30 * 86400, 86400, "1d"
    # Default to 24h
    return 86400, 900, "15m"


async def _query_prometheus_range(
    client: httpx.AsyncClient,
    prometheus_url: str,
    query: str,
    start: float,
    end: float,
    step: int,
) -> list[dict[str, Any]]:
    """
    Execute a range query against Prometheus HTTP API.
    """
    url = f"{prometheus_url.rstrip('/')}/api/v1/query_range"
    params = {
        "query": query,
        "start": str(start),
        "end": str(end),
        "step": str(step),
    }
    response = await client.get(url, params=params, timeout=5.0)
    response.raise_for_status()
    data = response.json()
    if data.get("status") != "success":
        raise ValueError(f"Prometheus query failed: {data.get('error')}")
    return data.get("data", {}).get("result", [])


def _matrix_to_series(
    results: list[dict[str, Any]],
    default_name: str,
    label_key: Optional[str] = None,
) -> list[TrendSeries]:
    """
    Convert Prometheus matrix results into TrendSeries models.
    """
    series_list: list[TrendSeries] = []
    # Cap series count
    for item in results[:MAX_SERIES_PER_METRIC]:
        metric_labels = item.get("metric", {})
        raw_values = item.get("values", [])

        if label_key and label_key in metric_labels:
            name = metric_labels[label_key]
        elif metric_labels:
            name = (
                ", ".join(
                    f"{k}={v}" for k, v in metric_labels.items() if k != "__name__"
                )
                or default_name
            )
        else:
            name = default_name

        points: list[TrendPoint] = []
        for ts_raw, val_raw in raw_values:
            try:
                val = float(val_raw)
                if math.isnan(val) or math.isinf(val):
                    val = 0.0
            except (ValueError, TypeError):
                val = 0.0

            ts = dt.datetime.fromtimestamp(float(ts_raw), tz=dt.timezone.utc)
            points.append(TrendPoint(timestamp=ts, value=round(val, 4)))

        series_list.append(
            TrendSeries(
                name=name,
                labels=metric_labels,
                points=points,
            )
        )
    return series_list


async def get_admin_trends(
    group: str = "usage",
    range_param: str = "24h",
    endpoint_filter: Optional[str] = None,
    task_name_filter: Optional[str] = None,
    provider_filter: Optional[str] = None,
) -> AdminTrendsResponse:
    """
    Fetch historical trend series for an administrative metrics group.
    """
    # 1. Check cache
    cache_key = (
        f"{group}:{range_param}:{endpoint_filter}:{task_name_filter}:{provider_filter}"
    )
    now = time.monotonic()
    if cache_key in _TRENDS_CACHE:
        cached_time, cached_resp = _TRENDS_CACHE[cache_key]
        if now - cached_time < CACHE_TTL_SECONDS:
            return cached_resp

    duration_sec, step_sec, step_str = _parse_step_and_range(range_param)
    end_dt = dt.datetime.now(tz=dt.timezone.utc)
    start_dt = end_dt - dt.timedelta(seconds=duration_sec)
    start_ts = start_dt.timestamp()
    end_ts = end_dt.timestamp()

    norm_group = (
        group.lower() if group in ("usage", "api", "worker", "provider") else "usage"
    )

    metrics: list[TrendMetric] = []

    try:
        async with httpx.AsyncClient() as client:
            if norm_group == "usage":
                # Metric 1: Total Registered Users
                try:
                    res = await _query_prometheus_range(
                        client,
                        backend_config.prometheus_url,
                        "camply_registered_users_total or camply_active_users",
                        start_ts,
                        end_ts,
                        step_sec,
                    )
                    metrics.append(
                        TrendMetric(
                            metric_id="registered_users",
                            title="Total Registered Users",
                            description="Cumulative registered users in the database.",
                            unit="users",
                            chart_type="line",
                            series=_matrix_to_series(res, "Registered Users"),
                        )
                    )
                except (ValueError, KeyError) as e:
                    logger.debug("Failed query for registered_users", error=str(e))

                # Metric 2: New Users Created
                try:
                    res = await _query_prometheus_range(
                        client,
                        backend_config.prometheus_url,
                        f"sum(increase(camply_users_created_total[{step_str}]))",
                        start_ts,
                        end_ts,
                        step_sec,
                    )
                    metrics.append(
                        TrendMetric(
                            metric_id="new_users",
                            title="New Users Created",
                            description=f"New user registrations per {step_str} bucket.",
                            unit="users",
                            chart_type="bar",
                            series=_matrix_to_series(res, "New Users"),
                        )
                    )
                except (ValueError, KeyError) as e:
                    logger.debug("Failed query for new_users", error=str(e))

                # Metric 3: Scan Creation
                try:
                    res = await _query_prometheus_range(
                        client,
                        backend_config.prometheus_url,
                        f"sum(increase(camply_scans_created_total[{step_str}]))",
                        start_ts,
                        end_ts,
                        step_sec,
                    )
                    metrics.append(
                        TrendMetric(
                            metric_id="scans_created",
                            title="Scans Created",
                            description=f"Successfully committed user scans per {step_str} bucket.",
                            unit="scans",
                            chart_type="bar",
                            series=_matrix_to_series(res, "New Scans"),
                        )
                    )
                except (ValueError, KeyError) as e:
                    logger.debug("Failed query for scans_created", error=str(e))

                # Metric 4: Scan Activity (Saved Active vs Eligible)
                try:
                    res_active = await _query_prometheus_range(
                        client,
                        backend_config.prometheus_url,
                        "camply_active_scans",
                        start_ts,
                        end_ts,
                        step_sec,
                    )
                    res_eligible = await _query_prometheus_range(
                        client,
                        backend_config.prometheus_url,
                        "camply_eligible_scans",
                        start_ts,
                        end_ts,
                        step_sec,
                    )
                    series = _matrix_to_series(
                        res_active, "Saved Active Scans"
                    ) + _matrix_to_series(res_eligible, "Eligible Scans")
                    metrics.append(
                        TrendMetric(
                            metric_id="scan_activity",
                            title="Scan Fleet Activity",
                            description="Saved active scans compared with effective eligible scans.",
                            unit="scans",
                            chart_type="line",
                            series=series,
                        )
                    )
                except (ValueError, KeyError) as e:
                    logger.debug("Failed query for scan_activity", error=str(e))

                # Metric 5: Polling Demand (Targets & Sharing)
                try:
                    res_targets = await _query_prometheus_range(
                        client,
                        backend_config.prometheus_url,
                        "camply_total_unique_targets",
                        start_ts,
                        end_ts,
                        step_sec,
                    )
                    res_elig_targets = await _query_prometheus_range(
                        client,
                        backend_config.prometheus_url,
                        "camply_eligible_targets",
                        start_ts,
                        end_ts,
                        step_sec,
                    )
                    series = _matrix_to_series(
                        res_targets, "Total Targets"
                    ) + _matrix_to_series(res_elig_targets, "Eligible Targets")
                    metrics.append(
                        TrendMetric(
                            metric_id="polling_demand",
                            title="Polling Demand & Sharing",
                            description="Unique targets vs targets with eligible subscribers.",
                            unit="targets",
                            chart_type="line",
                            series=series,
                        )
                    )
                except (ValueError, KeyError) as e:
                    logger.debug("Failed query for polling_demand", error=str(e))

                # Metric 6: Campground Search Volume
                try:
                    res = await _query_prometheus_range(
                        client,
                        backend_config.prometheus_url,
                        "sum(rate(camply_total_search_requests[1m]))",
                        start_ts,
                        end_ts,
                        step_sec,
                    )
                    metrics.append(
                        TrendMetric(
                            metric_id="search_throughput",
                            title="Campground Search Throughput",
                            description="Campground and recreation area search requests per second.",
                            unit="req/s",
                            chart_type="line",
                            series=_matrix_to_series(res, "Search Throughput"),
                        )
                    )
                except (ValueError, KeyError) as e:
                    logger.debug("Failed query for search_throughput", error=str(e))

            elif norm_group == "api":
                # Metric 1: API Requests per sec by Endpoint
                ep_filter = (
                    f'{{endpoint="{endpoint_filter}"}}' if endpoint_filter else ""
                )
                try:
                    res = await _query_prometheus_range(
                        client,
                        backend_config.prometheus_url,
                        f"sum(rate(camply_http_requests_total{ep_filter}[1m])) by (endpoint)",
                        start_ts,
                        end_ts,
                        step_sec,
                    )
                    metrics.append(
                        TrendMetric(
                            metric_id="api_requests_by_endpoint",
                            title="API Requests / sec by Endpoint",
                            description="Traffic volume broken down by normalized API route.",
                            unit="req/s",
                            chart_type="line",
                            series=_matrix_to_series(
                                res, "Endpoint", label_key="endpoint"
                            ),
                        )
                    )
                except (ValueError, KeyError) as e:
                    logger.debug(
                        "Failed query for api_requests_by_endpoint", error=str(e)
                    )

                # Metric 2: HTTP Status Breakdown (2xx, 4xx, 5xx)
                try:
                    res_2xx = await _query_prometheus_range(
                        client,
                        backend_config.prometheus_url,
                        'sum(rate(camply_http_requests_total{status=~"2.."}[5m])) / sum(rate(camply_http_requests_total[5m])) * 100',
                        start_ts,
                        end_ts,
                        step_sec,
                    )
                    res_5xx = await _query_prometheus_range(
                        client,
                        backend_config.prometheus_url,
                        'sum(rate(camply_http_requests_total{status=~"5.."}[5m])) / sum(rate(camply_http_requests_total[5m])) * 100',
                        start_ts,
                        end_ts,
                        step_sec,
                    )
                    res_4xx = await _query_prometheus_range(
                        client,
                        backend_config.prometheus_url,
                        'sum(rate(camply_http_requests_total{status=~"4.."}[5m])) / sum(rate(camply_http_requests_total[5m])) * 100',
                        start_ts,
                        end_ts,
                        step_sec,
                    )
                    series = (
                        _matrix_to_series(res_2xx, "2xx Success Rate (%)")
                        + _matrix_to_series(res_4xx, "4xx Client Error Rate (%)")
                        + _matrix_to_series(res_5xx, "5xx Server Error Rate (%)")
                    )
                    metrics.append(
                        TrendMetric(
                            metric_id="http_status_rates",
                            title="HTTP Response Status Rates",
                            description="Proportion of successful, client error, and server error responses.",
                            unit="%",
                            chart_type="line",
                            series=series,
                        )
                    )
                except (ValueError, KeyError) as e:
                    logger.debug("Failed query for http_status_rates", error=str(e))

                # Metric 3: Request Latency Quantiles
                try:
                    res_p50 = await _query_prometheus_range(
                        client,
                        backend_config.prometheus_url,
                        "histogram_quantile(0.50, sum(rate(camply_http_request_duration_seconds_bucket[5m])) by (le)) * 1000",
                        start_ts,
                        end_ts,
                        step_sec,
                    )
                    res_p95 = await _query_prometheus_range(
                        client,
                        backend_config.prometheus_url,
                        "histogram_quantile(0.95, sum(rate(camply_http_request_duration_seconds_bucket[5m])) by (le)) * 1000",
                        start_ts,
                        end_ts,
                        step_sec,
                    )
                    res_p99 = await _query_prometheus_range(
                        client,
                        backend_config.prometheus_url,
                        "histogram_quantile(0.99, sum(rate(camply_http_request_duration_seconds_bucket[5m])) by (le)) * 1000",
                        start_ts,
                        end_ts,
                        step_sec,
                    )
                    series = (
                        _matrix_to_series(res_p50, "p50 Latency (ms)")
                        + _matrix_to_series(res_p95, "p95 Latency (ms)")
                        + _matrix_to_series(res_p99, "p99 Latency (ms)")
                    )
                    metrics.append(
                        TrendMetric(
                            metric_id="request_latency",
                            title="Request Latency (p50 / p95 / p99)",
                            description="Estimated HTTP response duration quantiles in milliseconds.",
                            unit="ms",
                            chart_type="line",
                            series=series,
                        )
                    )
                except (ValueError, KeyError) as e:
                    logger.debug("Failed query for request_latency", error=str(e))

                # Metric 4: HTTP 5xx Errors by Endpoint
                try:
                    res = await _query_prometheus_range(
                        client,
                        backend_config.prometheus_url,
                        'sum(rate(camply_http_requests_total{status=~"5.."}[5m])) by (endpoint)',
                        start_ts,
                        end_ts,
                        step_sec,
                    )
                    metrics.append(
                        TrendMetric(
                            metric_id="server_errors_by_endpoint",
                            title="Server Errors (5xx) by Endpoint",
                            description="HTTP 5xx error rate per second broken down by route.",
                            unit="errors/s",
                            chart_type="line",
                            series=_matrix_to_series(
                                res, "Endpoint", label_key="endpoint"
                            ),
                        )
                    )
                except (ValueError, KeyError) as e:
                    logger.debug(
                        "Failed query for server_errors_by_endpoint", error=str(e)
                    )

            elif norm_group == "worker":
                # Metric 1: Tasks Executed / min
                task_filter = (
                    f'{{task_name="{task_name_filter}"}}' if task_name_filter else ""
                )
                try:
                    res = await _query_prometheus_range(
                        client,
                        backend_config.prometheus_url,
                        f"sum(rate(camply_celery_tasks_total{task_filter}[1m])) by (task_name) * 60",
                        start_ts,
                        end_ts,
                        step_sec,
                    )
                    metrics.append(
                        TrendMetric(
                            metric_id="tasks_executed_per_min",
                            title="Tasks Executed / min",
                            description="Celery task execution throughput by task name.",
                            unit="tasks/min",
                            chart_type="line",
                            series=_matrix_to_series(
                                res, "Task", label_key="task_name"
                            ),
                        )
                    )
                except (ValueError, KeyError) as e:
                    logger.debug(
                        "Failed query for tasks_executed_per_min", error=str(e)
                    )

                # Metric 2: Task Success & Failure Rates
                try:
                    res_success = await _query_prometheus_range(
                        client,
                        backend_config.prometheus_url,
                        'sum(rate(camply_celery_tasks_total{status="success"}[5m])) / sum(rate(camply_celery_tasks_total[5m])) * 100',
                        start_ts,
                        end_ts,
                        step_sec,
                    )
                    res_fail = await _query_prometheus_range(
                        client,
                        backend_config.prometheus_url,
                        'sum(rate(camply_celery_tasks_total{status="failure"}[5m])) / sum(rate(camply_celery_tasks_total[5m])) * 100',
                        start_ts,
                        end_ts,
                        step_sec,
                    )
                    series = _matrix_to_series(
                        res_success, "Success Rate (%)"
                    ) + _matrix_to_series(res_fail, "Failure Rate (%)")
                    metrics.append(
                        TrendMetric(
                            metric_id="task_success_failure_rate",
                            title="Task Success & Failure Rates",
                            description="Percentage of celery executions succeeding or failing.",
                            unit="%",
                            chart_type="line",
                            series=series,
                        )
                    )
                except (ValueError, KeyError) as e:
                    logger.debug(
                        "Failed query for task_success_failure_rate", error=str(e)
                    )

                # Metric 3: Application Outcomes (success, error, skipped, retrying)
                try:
                    res = await _query_prometheus_range(
                        client,
                        backend_config.prometheus_url,
                        "sum(rate(camply_application_outcomes_total[5m])) by (outcome) * 60",
                        start_ts,
                        end_ts,
                        step_sec,
                    )
                    metrics.append(
                        TrendMetric(
                            metric_id="application_outcomes",
                            title="Application Outcomes / min",
                            description="Normalized business outcomes (success, error, skipped, retrying).",
                            unit="outcomes/min",
                            chart_type="line",
                            series=_matrix_to_series(
                                res, "Outcome", label_key="outcome"
                            ),
                        )
                    )
                except (ValueError, KeyError) as e:
                    logger.debug("Failed query for application_outcomes", error=str(e))

                # Metric 4: Task Duration Quantiles
                try:
                    res_p50 = await _query_prometheus_range(
                        client,
                        backend_config.prometheus_url,
                        "histogram_quantile(0.50, sum(rate(camply_celery_task_duration_seconds_bucket[5m])) by (le)) * 1000",
                        start_ts,
                        end_ts,
                        step_sec,
                    )
                    res_p95 = await _query_prometheus_range(
                        client,
                        backend_config.prometheus_url,
                        "histogram_quantile(0.95, sum(rate(camply_celery_task_duration_seconds_bucket[5m])) by (le)) * 1000",
                        start_ts,
                        end_ts,
                        step_sec,
                    )
                    res_p99 = await _query_prometheus_range(
                        client,
                        backend_config.prometheus_url,
                        "histogram_quantile(0.99, sum(rate(camply_celery_task_duration_seconds_bucket[5m])) by (le)) * 1000",
                        start_ts,
                        end_ts,
                        step_sec,
                    )
                    series = (
                        _matrix_to_series(res_p50, "p50 Duration (ms)")
                        + _matrix_to_series(res_p95, "p95 Duration (ms)")
                        + _matrix_to_series(res_p99, "p99 Duration (ms)")
                    )
                    metrics.append(
                        TrendMetric(
                            metric_id="task_duration",
                            title="Task Duration (p50 / p95 / p99)",
                            description="Celery task execution duration quantiles in milliseconds.",
                            unit="ms",
                            chart_type="line",
                            series=series,
                        )
                    )
                except (ValueError, KeyError) as e:
                    logger.debug("Failed query for task_duration", error=str(e))

                # Metric 5: Discovery vs Enqueue
                try:
                    res_disc = await _query_prometheus_range(
                        client,
                        backend_config.prometheus_url,
                        "rate(camply_targets_discovered_total[1m]) * 60",
                        start_ts,
                        end_ts,
                        step_sec,
                    )
                    res_enq = await _query_prometheus_range(
                        client,
                        backend_config.prometheus_url,
                        "rate(camply_targets_enqueued_total[1m]) * 60",
                        start_ts,
                        end_ts,
                        step_sec,
                    )
                    series = _matrix_to_series(
                        res_disc, "Targets Discovered / min"
                    ) + _matrix_to_series(res_enq, "Targets Enqueued / min")
                    metrics.append(
                        TrendMetric(
                            metric_id="discovery_vs_enqueued",
                            title="Targets Discovered vs Enqueued / min",
                            description="Discovery heartbeat throughput and scheduling rate.",
                            unit="targets/min",
                            chart_type="line",
                            series=series,
                        )
                    )
                except (ValueError, KeyError) as e:
                    logger.debug("Failed query for discovery_vs_enqueued", error=str(e))

                # Metric 6: Scan Results Stored & Notifications Sent
                try:
                    res_stored = await _query_prometheus_range(
                        client,
                        backend_config.prometheus_url,
                        "rate(camply_scan_results_stored_total[1m]) * 60",
                        start_ts,
                        end_ts,
                        step_sec,
                    )
                    res_notif = await _query_prometheus_range(
                        client,
                        backend_config.prometheus_url,
                        "rate(camply_notifications_sent_total[1m]) * 60",
                        start_ts,
                        end_ts,
                        step_sec,
                    )
                    series = _matrix_to_series(
                        res_stored, "Results Stored / min"
                    ) + _matrix_to_series(res_notif, "Notifications Sent / min")
                    metrics.append(
                        TrendMetric(
                            metric_id="results_and_notifications",
                            title="Scan Results Stored & Notifications Sent / min",
                            description="Campsite openings stored and notification dispatch rate.",
                            unit="events/min",
                            chart_type="line",
                            series=series,
                        )
                    )
                except (ValueError, KeyError) as e:
                    logger.debug(
                        "Failed query for results_and_notifications", error=str(e)
                    )

                # Metric 7: Lock Contention Rate
                try:
                    res_acq = await _query_prometheus_range(
                        client,
                        backend_config.prometheus_url,
                        'sum(rate(camply_lock_contention_total{outcome="acquired"}[5m])) / sum(rate(camply_lock_contention_total[5m])) * 100',
                        start_ts,
                        end_ts,
                        step_sec,
                    )
                    res_skip = await _query_prometheus_range(
                        client,
                        backend_config.prometheus_url,
                        'sum(rate(camply_lock_contention_total{outcome="skipped"}[5m])) / sum(rate(camply_lock_contention_total[5m])) * 100',
                        start_ts,
                        end_ts,
                        step_sec,
                    )
                    series = _matrix_to_series(
                        res_acq, "Locks Acquired (%)"
                    ) + _matrix_to_series(res_skip, "Locks Skipped (%)")
                    metrics.append(
                        TrendMetric(
                            metric_id="lock_contention",
                            title="Lock Contention Rate",
                            description="Proportion of distributed target locks acquired vs skipped.",
                            unit="%",
                            chart_type="line",
                            series=series,
                        )
                    )
                except (ValueError, KeyError) as e:
                    logger.debug("Failed query for lock_contention", error=str(e))

                # Metric 8: Targets Checked (Executions)
                try:
                    res = await _query_prometheus_range(
                        client,
                        backend_config.prometheus_url,
                        "rate(camply_targets_checked_total[1m]) * 60",
                        start_ts,
                        end_ts,
                        step_sec,
                    )
                    metrics.append(
                        TrendMetric(
                            metric_id="targets_checked",
                            title="Targets Checked (Executions / min)",
                            description="Actual target availability scan executions performed.",
                            unit="checks/min",
                            chart_type="line",
                            series=_matrix_to_series(res, "Checks / min"),
                        )
                    )
                except (ValueError, KeyError) as e:
                    logger.debug("Failed query for targets_checked", error=str(e))

            elif norm_group == "provider":
                # Metric 1: Campground API Errors by Provider
                p_filter = (
                    f'{{provider="{provider_filter}"}}' if provider_filter else ""
                )
                try:
                    res = await _query_prometheus_range(
                        client,
                        backend_config.prometheus_url,
                        f"sum(rate(camply_campground_api_errors_total{p_filter}[5m])) by (provider)",
                        start_ts,
                        end_ts,
                        step_sec,
                    )
                    metrics.append(
                        TrendMetric(
                            metric_id="provider_errors",
                            title="Campground API Errors by Provider",
                            description="Upstream booking provider API error rate per second.",
                            unit="errors/s",
                            chart_type="line",
                            series=_matrix_to_series(
                                res, "Provider", label_key="provider"
                            ),
                        )
                    )
                except (ValueError, KeyError) as e:
                    logger.debug("Failed query for provider_errors", error=str(e))

                # Metric 2: Provider Error Rate (%) using actual provider checks as denominator
                try:
                    res = await _query_prometheus_range(
                        client,
                        backend_config.prometheus_url,
                        f"sum(rate(camply_campground_api_errors_total{p_filter}[5m])) / sum(rate(camply_provider_checks_total{p_filter}[5m])) * 100",
                        start_ts,
                        end_ts,
                        step_sec,
                    )
                    metrics.append(
                        TrendMetric(
                            metric_id="provider_error_rate",
                            title="Provider Error Rate (%)",
                            description="Error percentage using actual provider-call attempts as denominator.",
                            unit="%",
                            chart_type="line",
                            series=_matrix_to_series(res, "Error Rate (%)"),
                        )
                    )
                except (ValueError, KeyError) as e:
                    logger.debug("Failed query for provider_error_rate", error=str(e))

                # Metric 3: Provider Check Volume by Provider and Status
                try:
                    res = await _query_prometheus_range(
                        client,
                        backend_config.prometheus_url,
                        f"sum(rate(camply_provider_checks_total{p_filter}[5m])) by (provider, status) * 60",
                        start_ts,
                        end_ts,
                        step_sec,
                    )
                    metrics.append(
                        TrendMetric(
                            metric_id="provider_checks_volume",
                            title="Provider Checks Volume / min",
                            description="Availability checks performed per provider and status.",
                            unit="checks/min",
                            chart_type="line",
                            series=_matrix_to_series(res, "Provider Checks"),
                        )
                    )
                except (ValueError, KeyError) as e:
                    logger.debug(
                        "Failed query for provider_checks_volume", error=str(e)
                    )

        response = AdminTrendsResponse(
            group=norm_group,
            range=range_param,
            step_seconds=step_sec,
            start_time=start_dt,
            end_time=end_dt,
            timezone="UTC",
            available=True,
            error_message=None,
            metrics=metrics,
        )
        _TRENDS_CACHE[cache_key] = (now, response)
        return response

    except (httpx.RequestError, httpx.HTTPStatusError, ValueError) as exc:
        logger.warning(
            "Prometheus trends service unavailable",
            url=backend_config.prometheus_url,
            error=str(exc),
        )
        return AdminTrendsResponse(
            group=norm_group,
            range=range_param,
            step_seconds=step_sec,
            start_time=start_dt,
            end_time=end_dt,
            timezone="UTC",
            available=False,
            error_message=f"Prometheus service unreachable at {backend_config.prometheus_url}: {exc}",
            metrics=[],
        )
