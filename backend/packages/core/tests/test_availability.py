"""
Tests for availability snapshot comparison in camply_core.
"""

from datetime import date

from camply_core.availability import (
    AvailabilitySnapshot,
    diff_new_openings,
    identify_new_campsites,
)
from camply_core.models import CampsiteDTO, CampsiteType


def test_availability_snapshot_creation() -> None:
    """Test creating snapshot from campsite DTOs."""
    sites = [
        CampsiteDTO(
            campsite_id="1",
            campsite_name="Site 1",
            campsite_type=CampsiteType.TENT,
            available_dates=[date(2026, 9, 1), date(2026, 9, 2)],
        ),
        CampsiteDTO(
            campsite_id="2",
            campsite_name="Site 2",
            campsite_type=CampsiteType.RV,
            available_dates=[],
        ),
    ]
    snapshot = AvailabilitySnapshot.from_campsites(sites)
    assert snapshot.site_dates["1"] == {date(2026, 9, 1), date(2026, 9, 2)}
    assert snapshot.site_dates["2"] == set()
    assert snapshot.is_empty() is False


def test_diff_new_openings_initial() -> None:
    """Test initial snapshot comparison where previous is None."""
    curr = AvailabilitySnapshot(
        site_dates={"1": {date(2026, 9, 1)}},
    )
    diff = diff_new_openings(previous=None, current=curr)
    assert diff == {"1": {date(2026, 9, 1)}}


def test_diff_new_openings_unchanged() -> None:
    """Test unchanged consecutive snapshots produce no new openings."""
    prev = AvailabilitySnapshot(site_dates={"1": {date(2026, 9, 1)}})
    curr = AvailabilitySnapshot(site_dates={"1": {date(2026, 9, 1)}})
    diff = diff_new_openings(previous=prev, current=curr)
    assert diff == {}


def test_diff_new_openings_additional_dates() -> None:
    """Test additional opened dates are detected."""
    prev = AvailabilitySnapshot(site_dates={"1": {date(2026, 9, 1)}})
    curr = AvailabilitySnapshot(site_dates={"1": {date(2026, 9, 1), date(2026, 9, 2)}})
    diff = diff_new_openings(previous=prev, current=curr)
    assert diff == {"1": {date(2026, 9, 2)}}


def test_diff_reopening_after_departure() -> None:
    """Test a site disappearing and reappearing triggers new opening."""
    prev = AvailabilitySnapshot(site_dates={"1": set()})
    curr = AvailabilitySnapshot(site_dates={"1": {date(2026, 9, 1)}})
    diff = diff_new_openings(previous=prev, current=curr)
    assert diff == {"1": {date(2026, 9, 1)}}


def test_identify_new_campsites() -> None:
    """Test filtering campsite list to newly opened sites."""
    prev = AvailabilitySnapshot(site_dates={"1": {date(2026, 9, 1)}})
    campsites = [
        CampsiteDTO(
            campsite_id="1",
            campsite_name="Site 1",
            campsite_type=CampsiteType.TENT,
            available_dates=[date(2026, 9, 1)],
        ),
        CampsiteDTO(
            campsite_id="2",
            campsite_name="Site 2",
            campsite_type=CampsiteType.RV,
            available_dates=[date(2026, 9, 2)],
        ),
    ]
    new_sites = identify_new_campsites(previous=prev, current_campsites=campsites)
    assert len(new_sites) == 1
    assert new_sites[0].campsite_id == "2"
