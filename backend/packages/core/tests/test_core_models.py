"""
Tests for camply_core domain models.
"""

from datetime import date

import pytest
from pydantic import ValidationError

from camply_core.models import (
    CampsiteDTO,
    CampsiteType,
    NotificationDTO,
    SearchFilters,
    SearchWindow,
)


def test_search_window_valid() -> None:
    """Test valid SearchWindow generates expected nights [arrival, departure)."""
    window = SearchWindow(
        arrival=date(2026, 9, 1),
        departure=date(2026, 9, 4),
    )
    assert window.arrival == date(2026, 9, 1)
    assert window.departure == date(2026, 9, 4)
    # 3 nights: Sept 1, Sept 2, Sept 3 (Sept 4 checkout morning is excluded)
    assert window.nights == [
        date(2026, 9, 1),
        date(2026, 9, 2),
        date(2026, 9, 3),
    ]


def test_search_window_invalid() -> None:
    """Test SearchWindow rejects arrival >= departure."""
    with pytest.raises(ValidationError):
        SearchWindow(
            arrival=date(2026, 9, 4),
            departure=date(2026, 9, 1),
        )
    with pytest.raises(ValidationError):
        SearchWindow(
            arrival=date(2026, 9, 1),
            departure=date(2026, 9, 1),
        )


def test_search_filters_validation() -> None:
    """Test SearchFilters validation rules."""
    filters = SearchFilters(
        min_consecutive_nights=2,
        campsite_types=[CampsiteType.TENT],
        electric_requirement=True,
    )
    assert filters.min_consecutive_nights == 2
    assert filters.campsite_types == [CampsiteType.TENT]
    assert filters.electric_requirement is True

    with pytest.raises(ValidationError):
        SearchFilters(min_consecutive_nights=0)


def test_campsite_dto_defaults() -> None:
    """Test CampsiteDTO initialization and defaults."""
    dto = CampsiteDTO(
        campsite_id="101",
        campsite_name="Pine Loop 1",
        campsite_type=CampsiteType.TENT,
    )
    assert dto.campsite_id == "101"
    assert dto.capacity == 1
    assert dto.available_dates == []
    assert dto.is_electric is False
    assert dto.is_accessible is False
    assert dto.booking_url is None
    assert dto.metadata == {}


def test_notification_dto_serialization() -> None:
    """Test NotificationDTO serialization."""
    notif = NotificationDTO(
        title="Opening Found",
        message="Site 1 is open",
        booking_url="https://recreation.gov/1",
        park_name="Yosemite",
        campsite_name="Site 1",
        start_date=date(2026, 9, 1),
        end_date=date(2026, 9, 3),
        metadata={"site_id": "1"},
    )
    dumped = notif.model_dump(mode="json")
    assert dumped["start_date"] == "2026-09-01"
    assert dumped["end_date"] == "2026-09-03"
    assert dumped["booking_url"] == "https://recreation.gov/1"
