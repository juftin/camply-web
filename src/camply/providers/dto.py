"""
Unified Data Transfer Objects for Providers
"""

from datetime import date
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, Field


class CampsiteType(StrEnum):
    """
    Standardized Campsite Type Enum
    """

    TENT = "TENT"
    RV = "RV"
    CABIN = "CABIN"
    OTHER = "OTHER"


class CampsiteDTO(BaseModel):
    """
    Standardized Campsite Data Transfer Object
    """

    campsite_id: str
    campsite_name: str
    campsite_type: CampsiteType
    capacity: int
    available_dates: list[date]
    is_electric: bool
    is_accessible: bool
    metadata: dict[str, Any] = Field(default_factory=dict)


class SearchEntityType(StrEnum):
    """Entity kinds supported by direct provider discovery."""

    CAMPGROUND = "campground"
    RECREATION_AREA = "recreation_area"


class ProviderSearchQuery(BaseModel):
    """Validated provider discovery arguments, independent of persistence."""

    entity_type: SearchEntityType | None = None
    query: str = ""
    state: str | None = Field(default=None, pattern=r"^[A-Z]{2}$")
    recreation_area_id: str | None = None
    limit: int = Field(default=50, ge=1, le=1000, strict=True)


class ProviderSearchResult(BaseModel):
    """Common location and identity fields for upstream discovery."""

    entity_type: SearchEntityType

    provider_id: int
    provider_name: str
    campground_id: str | None = None
    campground_name: str | None = None
    recreation_area_id: str | None = None
    recreation_area_name: str | None = None
    city: str | None = None
    state: str | None = None
    country: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    booking_url: str

    def matches(self, query: ProviderSearchQuery, *, match_text: bool = True) -> bool:
        """Apply common filters to locally searched provider catalogs."""
        text = " ".join(
            value
            for value in (self.campground_name, self.recreation_area_name, self.city)
            if value
        ).casefold()
        return (
            (query.entity_type in (None, self.entity_type))
            and (not match_text or query.query.casefold() in text)
            and (query.state is None or (self.state or "").upper() == query.state)
            and (
                query.recreation_area_id is None
                or self.recreation_area_id == query.recreation_area_id
            )
        )


class CampgroundSearchResult(ProviderSearchResult):
    """A campground whose ID can be used for availability scanning."""

    entity_type: Literal[SearchEntityType.CAMPGROUND] = SearchEntityType.CAMPGROUND
    campground_id: str
    campground_name: str


class RecreationAreaSearchResult(ProviderSearchResult):
    """A park or recreation area containing campground search targets."""

    entity_type: Literal[SearchEntityType.RECREATION_AREA] = (
        SearchEntityType.RECREATION_AREA
    )
    campground_id: None = None
    campground_name: None = None
    recreation_area_id: str
    recreation_area_name: str
