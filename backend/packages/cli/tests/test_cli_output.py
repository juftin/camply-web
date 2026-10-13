"""
Tests for output rendering functions.
"""

from datetime import date

from camply.output import (
    print_banner,
    print_campgrounds_table,
    print_campsites_table,
    print_json_output,
    print_rec_areas_table,
)
from camply_core.models import CampsiteDTO, CampsiteType
from camply_core.providers.recreation_gov.models import (
    RecDotGovCampground,
    RecDotGovRecreationArea,
)


def test_print_campsites_table_empty() -> None:
    """Empty campsites prints warning without crashing."""
    print_campsites_table([])


def test_print_campsites_table_with_items() -> None:
    """Non-empty campsites prints table rows."""
    site = CampsiteDTO(
        campsite_id="site_1",
        campsite_name="Pine Site 1",
        campsite_type=CampsiteType.TENT,
        capacity=6,
        available_dates=[date(2026, 9, 1)],
        is_electric=True,
        is_accessible=False,
    )
    print_campsites_table([site])


def test_print_campgrounds_table() -> None:
    """Campgrounds table renders."""
    cg = RecDotGovCampground(
        FacilityID="123",
        FacilityName="Test Campground",
        FacilityTypeDescription="Campground",
        Reservable=True,
    )
    print_campgrounds_table([cg])


def test_print_rec_areas_table() -> None:
    """Recreation areas table renders."""
    ra = RecDotGovRecreationArea(
        RecAreaID="456",
        RecAreaName="Test Rec Area",
    )
    print_rec_areas_table([ra])


def test_print_json_output() -> None:
    """JSON output renders."""
    print_json_output({"status": "ok", "count": 1})


def test_print_banner() -> None:
    """Panel banner renders."""
    print_banner(title="Success", message="All tasks complete")
