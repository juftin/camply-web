"""
Pydantic v2 request / response schemas for camply-backend API endpoints.
"""

from __future__ import annotations

import datetime
import uuid
from typing import Annotated, Literal, Optional

from pydantic import AfterValidator, BaseModel, Field


def _ensure_utc(v: datetime.datetime) -> datetime.datetime:
    """
    Ensure datetimes (including naive ones from SQLAlchemy) are treated as UTC.

    When serialized to JSON, this ensures timestamps include a 'Z' UTC offset,
    preventing clients from incorrectly parsing them as local time.
    """
    if v.tzinfo is None:
        return v.replace(tzinfo=datetime.timezone.utc)
    return v.astimezone(datetime.timezone.utc)


UtcDateTime = Annotated[datetime.datetime, AfterValidator(_ensure_utc)]


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
    is_invited: bool
    is_admin: bool = False
    scanning_enabled: bool = True
    pushover_token: Optional[str] = None
    must_change_password: bool = False


class MeUpdateRequest(BaseModel):
    """Payload for ``PATCH /me``."""

    pushover_token: Optional[str] = None


class ChangePasswordRequest(BaseModel):
    """Payload for changing the authenticated user's password."""

    current_password: str = Field(min_length=1, max_length=1024, repr=False)
    new_password: str = Field(min_length=1, max_length=1024, repr=False)


class SessionLoginRequest(BaseModel):
    """Credentials submitted through the app's shared-account login form."""

    username: str = Field(min_length=1, max_length=255)
    password: str = Field(min_length=1, max_length=1024, repr=False)


# ===========================================================================
# Access Requests
# ===========================================================================


class AccessRequestCreate(BaseModel):
    """Payload for ``POST /request-access``."""

    email: str = Field(..., description="Email address requesting an invitation")
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
    provider_id: int | None = Field(default=None, ge=1)
    campground_id: str | None = Field(default=None, min_length=1)
    start_date: datetime.date | None = None
    end_date: datetime.date | None = None
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
    last_checked_at: Optional[UtcDateTime] = None
    found_count: int = 0
    created_at: UtcDateTime


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
    """Single search hit with enriched location and amenities."""

    id: str
    entity_type: str
    provider_id: int
    provider_name: str
    recreation_area_id: Optional[str] = None
    recreation_area_name: Optional[str] = None
    campground_id: Optional[str] = None
    campground_name: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    reservable: bool = True
    campsite_types: list[str] = Field(default_factory=list)
    has_electric: bool = False
    has_water: bool = False
    has_sewer: bool = False
    pets_allowed: bool = False
    ada_accessible: bool = False
    max_rv_length: Optional[int] = None


class SearchFacets(BaseModel):
    """Faceted counts for search results."""

    providers: dict[str, int] = Field(default_factory=dict)
    states: dict[str, int] = Field(default_factory=dict)
    entity_types: dict[str, int] = Field(default_factory=dict)


class SearchExploreResponse(BaseModel):
    """Paginated search response with faceted metadata."""

    items: list[SearchResultResponse] = Field(default_factory=list)
    total: int
    page: int
    page_size: int
    total_pages: int
    facets: SearchFacets


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
    suspended_users: int
    dormant_targets: int
    heartbeat_interval_seconds: int
    target_cooldown_seconds: int
    overdue_threshold_seconds: int


class AdminUserItem(BaseModel):
    """User row in admin user list."""

    id: uuid.UUID
    email: str
    is_admin: bool
    is_invited: bool
    scanning_enabled: bool
    has_pushover_token: bool
    must_change_password: bool = False
    total_scans: int
    active_scans: int
    created_at: UtcDateTime


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
    is_invited: bool
    scanning_enabled: bool
    has_pushover_token: bool
    must_change_password: bool = False
    total_scans: int
    active_scans: int
    created_at: UtcDateTime
    updated_at: UtcDateTime


class AdminUserCreateRequest(BaseModel):
    """Payload for creating a user in session authentication mode."""

    email: str = Field(min_length=3, max_length=255, description="User email address")
    password: str = Field(
        min_length=1, max_length=1024, repr=False, description="Initial password"
    )
    is_admin: bool = Field(default=False, description="Grant administrator privileges")
    must_change_password: bool = Field(
        default=False, description="Force password change on first sign in"
    )
    is_invited: bool = Field(default=True, description="Invitation status")
    scanning_enabled: bool = Field(default=True, description="Enable campsite scanning")


class AdminUserUpdateRequest(BaseModel):
    """Payload to update an existing user."""

    is_admin: Optional[bool] = None
    scanning_enabled: Optional[bool] = None
    must_change_password: Optional[bool] = None
    password: Optional[str] = Field(
        default=None, min_length=1, max_length=1024, repr=False
    )


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
    last_checked_at: Optional[UtcDateTime] = None
    found_count: int
    created_at: UtcDateTime


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
    last_checked_at: Optional[UtcDateTime] = None
    created_at: UtcDateTime
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
    created_at: UtcDateTime


class AdminTargetDetailResponse(BaseModel):
    """Admin detailed view of a shared unique target."""

    id: uuid.UUID
    provider_id: int
    campground_id: str
    campground_name: str
    start_date: datetime.date
    end_date: datetime.date
    hash: str
    last_checked_at: Optional[UtcDateTime] = None
    created_at: UtcDateTime
    total_subscribers: int
    eligible_subscribers: int
    overdue_threshold_seconds: int
    status: Literal["active", "overdue", "dormant"]
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
    created_at: UtcDateTime


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
    active_tasks: int | None
    reserved_tasks: int | None
    scheduled_tasks: int | None


class AdminDiscoveryMetadata(BaseModel):
    """Metadata from the last completed target discovery cycle."""

    timestamp: UtcDateTime
    targets_discovered: int
    targets_enqueued: int
    status: str


class AdminOperationsResponse(BaseModel):
    """Overview of worker execution nodes, queue depth, and discovery status."""

    workers: list[AdminWorkerItem]
    queue_depth: int
    active_tasks_total: int | None
    reserved_tasks_total: int | None
    scheduled_tasks_total: int | None
    last_discovery: Optional[AdminDiscoveryMetadata] = None
    broker_connected: bool
    snapshot_at: UtcDateTime
    inspection_available: bool = True
    telemetry_available: bool = True
    stale: bool = False
    last_successful_at: Optional[UtcDateTime] = None
    error_message: Optional[str] = None


class AdminTaskTelemetryItem(BaseModel):
    """Allowlisted metadata record of a background task execution."""

    task_id: str
    event_id: str | None = None
    attempt: int | None = None
    task_name: str
    worker: str
    finished_at: UtcDateTime
    duration_ms: float
    entity_type: Optional[str] = None
    entity_id: Optional[str] = None
    outcome: str
    reason: Optional[str] = None
    provider_id: Optional[int] = None
    provider_name: Optional[str] = None
    search_name: Optional[str] = None
    search_dates: Optional[str] = None


class AdminOperationsTasksResponse(BaseModel):
    """List of recent task executions."""

    tasks: list[AdminTaskTelemetryItem]
    total: int
    available: bool = True
    error_message: Optional[str] = None


class AdminOperationsTaskDetail(AdminTaskTelemetryItem):
    """Detailed view of a single task attempt, using the same safe metadata as history."""


class AdminSyncProvidersResponse(BaseModel):
    """Response returned when triggering provider metadata synchronization."""

    task_id: str
    status: str
    message: str


# ===========================================================================
# Admin Trends & Prometheus Metrics
# ===========================================================================


class TrendPoint(BaseModel):
    """A single time-value data point."""

    timestamp: UtcDateTime
    value: float | None


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
    start_time: UtcDateTime
    end_time: UtcDateTime
    timezone: str = "UTC"
    last_successful_at: Optional[UtcDateTime] = None
    available: bool
    error_message: Optional[str] = None
    metrics: list[TrendMetric] = Field(default_factory=list)


class GeographicBounds(BaseModel):
    """A geographic extent; west greater than east crosses the dateline."""

    west: float = Field(ge=-180, le=180, allow_inf_nan=False)
    south: float = Field(ge=-90, le=90, allow_inf_nan=False)
    east: float = Field(ge=-180, le=180, allow_inf_nan=False)
    north: float = Field(ge=-90, le=90, allow_inf_nan=False)


class SearchMapSummaryResponse(BaseModel):
    """Counts and initial extent for the entire filtered catalog."""

    total: int = Field(ge=0)
    mappable_total: int = Field(ge=0)
    unmappable_total: int = Field(ge=0)
    bounds: GeographicBounds | None


class SearchMapLocation(BaseModel):
    """One independently actionable mapped catalog location."""

    kind: Literal["location"] = "location"
    cell_id: str
    item: SearchResultResponse


class SearchMapGroup(BaseModel):
    """An explorable bounded group, including exactly overlapping places."""

    kind: Literal["group"] = "group"
    cell_id: str
    count: int = Field(ge=2)
    latitude: float
    longitude: float
    bounds: GeographicBounds


class SearchMapResponse(BaseModel):
    """A complete bounded representation of the filtered visible area."""

    viewport: GeographicBounds
    grid_level: int = Field(ge=1, le=20)
    represented_total: int = Field(ge=0)
    features: list[SearchMapLocation | SearchMapGroup] = Field(max_length=512)


class SearchMapMembersResponse(BaseModel):
    """A keyset page for a selected group and its original viewport."""

    items: list[SearchResultResponse] = Field(max_length=100)
    total: int = Field(ge=0)
    next_cursor: str | None
