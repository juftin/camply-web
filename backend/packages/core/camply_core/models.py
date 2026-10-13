"""
Domain models and DTOs for camply core.
"""

from datetime import date, timedelta
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator


class CampsiteType(StrEnum):
    """
    Standardized campsite type classification.
    """

    TENT = "TENT"
    RV = "RV"
    CABIN = "CABIN"
    OTHER = "OTHER"


class SearchWindow(BaseModel):
    """
    Arrival and departure search window for campsite availability.
    """

    arrival: date
    departure: date

    @model_validator(mode="after")
    def validate_window(self) -> "SearchWindow":
        """
        Ensure arrival date strictly precedes departure date.
        """
        if self.arrival >= self.departure:
            raise ValueError(
                f"Arrival date ({self.arrival}) must precede departure date ({self.departure})."
            )
        return self

    @property
    def nights(self) -> list[date]:
        """
        The list of overnight stay dates [arrival, departure).
        """
        night_list: list[date] = []
        curr = self.arrival
        while curr < self.departure:
            night_list.append(curr)
            curr += timedelta(days=1)
        return night_list


class SearchFilters(BaseModel):
    """
    Search filters for qualifying stays.
    """

    min_consecutive_nights: int = Field(default=1, ge=1)
    campsite_types: list[CampsiteType] | None = None
    electric_requirement: bool = False

    @field_validator("min_consecutive_nights")
    @classmethod
    def validate_min_nights(cls, v: int) -> int:
        """
        Ensure minimum consecutive nights is positive.
        """
        if v < 1:
            raise ValueError("Minimum consecutive nights must be at least 1.")
        return v


class StayWindow(BaseModel):
    """
    A qualifying consecutive available stay run.
    """

    arrival: date
    departure: date
    nights: int


class CampsiteDTO(BaseModel):
    """
    Standardized Campsite Data Transfer Object.
    """

    campsite_id: str
    campsite_name: str
    campsite_type: CampsiteType
    capacity: int = 1
    available_dates: list[date] = Field(default_factory=list)
    is_electric: bool = False
    is_accessible: bool = False
    booking_url: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class NotificationDTO(BaseModel):
    """
    Unified notification payload passed to alert providers and worker tasks.
    """

    title: str
    message: str
    booking_url: str
    park_name: str
    campsite_name: str
    start_date: date
    end_date: date
    metadata: dict[str, Any] = Field(default_factory=dict)


class ProviderDescriptor(BaseModel):
    """
    Metadata descriptor for a campsite booking provider.
    """

    slug: str
    name: str
    base_url: str
    booking_url_template: str | None = None
