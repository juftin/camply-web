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


@pytest.fixture
def synthetic_equipment_samples() -> dict[str, object]:
    """Return synthetic vehicle lengths, equipment labels, and amenities without external I/O."""
    return {
        "feet_values": [35, 28.9, "24 ft", "up to 30ft", "0", 0, -5, None, "unlimited"],
        "metric_values": ["8m", "9.5 m", "10.2 meters"],
        "equipment_sets": [
            ["Tent"],
            ["RV", "Trailer"],
            ["Small Tent", "RV/Trailer up to 35ft"],
            ["2 Trailers/RVs up to 40ft", "Tent"],
        ],
        "campground_capabilities": {
            "campsite_types": ["RV", "TENT"],
            "has_electric": True,
            "has_water": True,
            "has_sewer": False,
            "pets_allowed": True,
            "ada_accessible": True,
            "max_rv_length": 40,
        },
    }
