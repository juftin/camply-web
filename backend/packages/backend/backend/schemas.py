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
    pushover_token: Optional[str] = None


class MeUpdateRequest(BaseModel):
    """Payload for ``PATCH /me``."""

    pushover_token: Optional[str] = None


# ===========================================================================
# Scans
# ===========================================================================


class ScanCreateRequest(BaseModel):
    """Payload for creating a new user scan."""

    provider_id: int = Field(..., description="Provider identifier")
    campground_id: str = Field(..., description="Provider-internal campground ID")
    start_date: datetime.date = Field(..., description="Check-in date")
    end_date: datetime.date = Field(..., description="Check-out date")
    min_stay_length: int = Field(default=1, ge=1, description="Minimum consecutive nights")
    preferred_types: list[str] = Field(default_factory=list, description="Preferred campsite types (TENT, RV, CABIN, …)")
    require_electric: bool = Field(default=False, description="Only alert on electric hookup sites")


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
