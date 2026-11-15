"""Synthetic catalog builders shared by area-monitoring regression suites."""

import datetime

import pytest

from camply.db.models import Campground, RecreationArea


@pytest.fixture
def area_catalog() -> tuple[RecreationArea, list[Campground]]:
    """Return a complete area larger than any discovery page, without external I/O."""
    area = RecreationArea(id="area-029", provider_id=1, name="Synthetic Area")
    children = [
        Campground(
            id=f"029-{index:03}",
            provider_id=1,
            recreation_area_id=area.id,
            name=f"Synthetic Campground {index:03}",
            enabled=True,
            reservable=True,
        )
        for index in range(125)
    ]
    return area, children


@pytest.fixture
def monitoring_now() -> datetime.datetime:
    """Provide one stable UTC instant for explicitly clocked coverage operations."""
    return datetime.datetime(2027, 7, 1, tzinfo=datetime.timezone.utc)
