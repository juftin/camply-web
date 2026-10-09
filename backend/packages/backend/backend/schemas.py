"""
Pydantic v2 request / response schemas for camply-backend API endpoints.
"""

from __future__ import annotations

import datetime
import uuid
from typing import Optional

from pydantic import BaseModel, Field

# ===========================================================================
# Providers
# ===========================================================================


class ProviderResponse(BaseModel):
    """Public provider representation."""

    id: int
    name: str
    description: Optional[str] = None
    url: str
    enabled: bool


# ===========================================================================
# Me / User profile
# ===========================================================================


class MeResponse(BaseModel):
    """Current user profile returned by ``GET /me``."""

    id: uuid.UUID
    email: str
    is_early_access_user: bool
    is_admin: bool = False
    scanning_enabled: bool = True
    pushover_token: Optional[str] = None


class MeUpdateRequest(BaseModel):
    """Payload for ``PATCH /me``."""

    pushover_token: Optional[str] = None


# ===========================================================================
# Access Requests
# ===========================================================================


class AccessRequestCreate(BaseModel):
    """Payload for ``POST /request-access``."""

    email: str = Field(..., description="Email address requesting early access")
    name: Optional[str] = Field(default=None, description="Optional name")


class AccessRequestResponse(BaseModel):
    """Response for a successful access request submission."""

    message: str


# ===========================================================================
# Scans
# ===========================================================================


class ScanCreateRequest(BaseModel):
    """Payload for creating a new user scan."""

    provider_id: int = Field(..., description="Provider identifier")
    campground_id: str = Field(..., description="Provider-internal campground ID")
    start_date: datetime.date = Field(..., description="Check-in date")
    end_date: datetime.date = Field(..., description="Check-out date")
    min_stay_length: int = Field(
        default=1, ge=1, description="Minimum consecutive nights"
    )
    preferred_types: list[str] = Field(
        default_factory=list,
        description="Preferred campsite types (TENT, RV, CABIN, …)",
    )
    require_electric: bool = Field(
        default=False, description="Only alert on electric hookup sites"
    )


class ScanUpdateRequest(BaseModel):
    """Payload for ``PATCH /scans/{id}`` — all fields optional."""

    is_active: Optional[bool] = None
    min_stay_length: Optional[int] = Field(default=None, ge=1)
    preferred_types: Optional[list[str]] = None
    require_electric: Optional[bool] = None


class ScanResultItem(BaseModel):
    """A single campsite availability entry returned as part of scan detail."""

    campsite_id: str
    campsite_name: str = ""
    available_dates: list[str] = Field(default_factory=list)


class ScanResponse(BaseModel):
    """User scan representation returned by the API."""

    id: uuid.UUID
    provider_id: int
    campground_id: str
    campground_name: str = ""
    recreation_area_name: str = ""
    start_date: datetime.date
    end_date: datetime.date
    is_active: bool
    min_stay_length: int
    preferred_types: list[str] = Field(default_factory=list)
    require_electric: bool
    last_checked_at: Optional[datetime.datetime] = None
    found_count: int = 0
    created_at: datetime.datetime


class ScanListResponse(BaseModel):
    """Wrapper for ``GET /scans`` to include counts."""

    scans: list[ScanResponse]
    total: int


class ScanDetailResponse(ScanResponse):
    """Detailed scan view that includes recent results."""

    results: list[ScanResultItem] = Field(default_factory=list)


# ===========================================================================
# Search
# ===========================================================================


class SearchResultResponse(BaseModel):
    """Single search hit."""

    id: str
    entity_type: str
    provider_id: int
    provider_name: str
    recreation_area_id: Optional[str] = None
    recreation_area_name: Optional[str] = None
    campground_id: Optional[str] = None
    campground_name: Optional[str] = None


# ===========================================================================
# Admin
# ===========================================================================


class AdminOverviewResponse(BaseModel):
    """Aggregate statistics for the administration overview."""

    total_users: int
    scanning_enabled_users: int
    total_scans: int
    saved_active_scans: int
    eligible_scans: int
    total_targets: int
    eligible_targets: int
    overdue_targets: int


class AdminUserItem(BaseModel):
    """User row in admin user list."""

    id: uuid.UUID
    email: str
    is_admin: bool
    is_early_access_user: bool
    scanning_enabled: bool
    has_pushover_token: bool
    total_scans: int
    active_scans: int
    created_at: datetime.datetime


class AdminUserListResponse(BaseModel):
    """Paginated admin user list."""

    users: list[AdminUserItem]
    total: int


class AdminUserDetailResponse(BaseModel):
    """Admin detailed user representation."""

    id: uuid.UUID
    email: str
    auth0_id: Optional[str] = None
    is_admin: bool
    is_early_access_user: bool
    scanning_enabled: bool
    has_pushover_token: bool
    total_scans: int
    active_scans: int
    created_at: datetime.datetime
    updated_at: datetime.datetime


class AdminUserUpdateRequest(BaseModel):
    """Payload to toggle scanning_enabled for a user."""

    scanning_enabled: bool


class AdminScanItem(BaseModel):
    """Scan summary item in admin scan list."""

    id: uuid.UUID
    user_id: uuid.UUID
    user_email: str
    target_id: uuid.UUID
    provider_id: int
    campground_id: str
    campground_name: str
    start_date: datetime.date
    end_date: datetime.date
    is_active: bool
    is_eligible: bool
    user_scanning_enabled: bool
    created_at: datetime.datetime


class AdminScanListResponse(BaseModel):
    """Paginated admin scan list."""

    scans: list[AdminScanItem]
    total: int


class AdminScanDetailResponse(BaseModel):
    """Admin detailed scan view."""

    id: uuid.UUID
    user_id: uuid.UUID
    user_email: str
    target_id: uuid.UUID
    provider_id: int
    campground_id: str
    campground_name: str
    recreation_area_name: str
    start_date: datetime.date
    end_date: datetime.date
    is_active: bool
    is_eligible: bool
    user_scanning_enabled: bool
    min_stay_length: int
    preferred_types: list[str] = Field(default_factory=list)
    require_electric: bool
    last_checked_at: Optional[datetime.datetime] = None
    created_at: datetime.datetime
    results: list[ScanResultItem] = Field(default_factory=list)


class AdminScanUpdateRequest(BaseModel):
    """Payload to toggle is_active for a scan."""

    is_active: bool


class AdminTargetSubscriberItem(BaseModel):
    """A subscriber attached to a unique target."""

    scan_id: uuid.UUID
    user_id: uuid.UUID
    user_email: str
    is_active: bool
    is_eligible: bool
    user_scanning_enabled: bool
    created_at: datetime.datetime


class AdminTargetDetailResponse(BaseModel):
    """Admin detailed view of a shared unique target."""

    id: uuid.UUID
    provider_id: int
    campground_id: str
    campground_name: str
    start_date: datetime.date
    end_date: datetime.date
    hash: str
    last_checked_at: Optional[datetime.datetime] = None
    created_at: datetime.datetime
    total_subscribers: int
    eligible_subscribers: int
    status: str
    subscribers: list[AdminTargetSubscriberItem] = Field(default_factory=list)
    subscribers_total: int


class AdminAuditEventItem(BaseModel):
    """Admin audit event log record."""

    id: uuid.UUID
    actor_id: uuid.UUID
    actor_email: str
    action: str
    subject_type: str
    subject_id: uuid.UUID
    prev_value: Optional[bool] = None
    new_value: Optional[bool] = None
    created_at: datetime.datetime


class AdminAuditListResponse(BaseModel):
    """Paginated list of admin audit records."""

    events: list[AdminAuditEventItem]
    total: int


# ===========================================================================
# Admin Operations
# ===========================================================================


class AdminWorkerItem(BaseModel):
    """Status and queue workload for a single Celery worker node."""

    name: str
    status: str
    active_tasks: int
    reserved_tasks: int
    scheduled_tasks: int


class AdminDiscoveryMetadata(BaseModel):
    """Metadata from the last completed target discovery cycle."""

    timestamp: datetime.datetime
    targets_discovered: int
    targets_enqueued: int
    status: str


class AdminOperationsResponse(BaseModel):
    """Overview of worker execution nodes, queue depth, and discovery status."""

    workers: list[AdminWorkerItem]
    queue_depth: int
    active_tasks_total: int
    reserved_tasks_total: int
    scheduled_tasks_total: int
    last_discovery: Optional[AdminDiscoveryMetadata] = None
    broker_connected: bool
    snapshot_at: datetime.datetime


class AdminTaskTelemetryItem(BaseModel):
    """Allowlisted metadata record of a background task execution."""

    task_id: str
    task_name: str
    worker: str
    finished_at: datetime.datetime
    duration_ms: float
    entity_type: Optional[str] = None
    entity_id: Optional[str] = None
    outcome: str
    reason: Optional[str] = None


class AdminOperationsTasksResponse(BaseModel):
    """List of recent task executions."""

    tasks: list[AdminTaskTelemetryItem]
    total: int


class AdminOperationsTaskDetail(BaseModel):
    """Detailed view of a single task execution."""

    task_id: str
    task_name: str
    worker: str
    finished_at: datetime.datetime
    duration_ms: float
    entity_type: Optional[str] = None
    entity_id: Optional[str] = None
    outcome: str
    reason: Optional[str] = None


# ===========================================================================
# Admin Trends & Prometheus Metrics
# ===========================================================================


class TrendPoint(BaseModel):
    """A single time-value data point."""

    timestamp: datetime.datetime
    value: float


class TrendSeries(BaseModel):
    """A named time series containing data points."""

    name: str
    labels: dict[str, str] = Field(default_factory=dict)
    points: list[TrendPoint] = Field(default_factory=list)


class TrendMetric(BaseModel):
    """A single metric panel containing one or more series."""

    metric_id: str
    title: str
    description: str
    unit: str
    chart_type: str
    series: list[TrendSeries] = Field(default_factory=list)


class AdminTrendsResponse(BaseModel):
    """Aggregated historical trend metrics from Prometheus."""

    group: str
    range: str
    step_seconds: int
    start_time: datetime.datetime
    end_time: datetime.datetime
    timezone: str = "UTC"
    available: bool
    error_message: Optional[str] = None
    metrics: list[TrendMetric] = Field(default_factory=list)
