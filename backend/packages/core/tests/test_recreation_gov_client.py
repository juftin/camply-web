"""
Tests for RecreationGovClient in camply_core.
"""

from datetime import date, datetime
from unittest.mock import AsyncMock, patch

import pytest

from camply_core.models import CampsiteType
from camply_core.providers.recreation_gov import (
    CampsiteAvailabilityCampsite,
    CampsiteAvailabilityResponse,
    RecDotGovAttribute,
    RecDotGovAvailabilityStatus,
    RecDotGovCampsite,
    RecreationGovClient,
    check_is_electric,
    map_campsite_type,
)


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


def test_map_campsite_type() -> None:
    """Test mapping raw Recreation.gov types to CampsiteType."""
    assert map_campsite_type("Standard Tent Only") == CampsiteType.TENT
    assert map_campsite_type("RV Electric") == CampsiteType.RV
    assert map_campsite_type("Cabin") == CampsiteType.CABIN
    assert map_campsite_type("Yurt") == CampsiteType.CABIN
    assert map_campsite_type("Group Picnic Area") == CampsiteType.OTHER
    assert map_campsite_type(None) == CampsiteType.OTHER


def test_check_is_electric() -> None:
    """Test electric attribute checking."""
    electric_site = RecDotGovCampsite(
        campsite_id=1,
        name="1",
        type="Electric RV",
    )
    assert check_is_electric(electric_site) is True

    attr_site = RecDotGovCampsite(
        campsite_id=2,
        name="2",
        attributes=[
            RecDotGovAttribute(
                attribute_id=1,
                attribute_name="Electricity Hookup",
                attribute_value="50 Amp",
            )
        ],
    )
    assert check_is_electric(attr_site) is True

    non_electric = RecDotGovCampsite(
        campsite_id=3,
        name="3",
        attributes=[
            RecDotGovAttribute(
                attribute_id=1,
                attribute_name="Electricity Hookup",
                attribute_value="No",
            )
        ],
    )
    assert check_is_electric(non_electric) is False


def test_urls() -> None:
    """Test URL generation helpers."""
    assert (
        RecreationGovClient.get_campground_url("234708")
        == "https://www.recreation.gov/camping/campgrounds/234708"
    )
    assert (
        RecreationGovClient.get_rec_area_url("123")
        == "https://www.recreation.gov/gateways/123"
    )


@pytest.mark.anyio
async def test_find_availabilities_checkout_exclusion_and_status() -> None:
    """
    Verify provider date contract:
    1. Checkout date morning is excluded from available nights [start, end).
    2. Only explicit 'Available' status is accepted; unknown statuses are rejected.
    """
    client = RecreationGovClient()

    mock_campsite = RecDotGovCampsite(
        campsite_id=101,
        name="Site 101",
        type="Standard Tent Only",
    )

    # API returns:
    # 2026-09-01: Available (should be included)
    # 2026-09-02: Available (should be included)
    # 2026-09-03: Available (checkout day -> MUST BE EXCLUDED!)
    # 2026-09-01 on site 102: UnknownStatus -> MUST BE EXCLUDED!
    mock_avail_response = CampsiteAvailabilityResponse(
        campsites={
            101: CampsiteAvailabilityCampsite(
                site="Site 101",
                campsite_type="Standard Tent Only",
                availabilities={
                    datetime(
                        2026, 9, 1, 0, 0
                    ): RecDotGovAvailabilityStatus.AVAILABLE.value,
                    datetime(
                        2026, 9, 2, 0, 0
                    ): RecDotGovAvailabilityStatus.AVAILABLE.value,
                    datetime(
                        2026, 9, 3, 0, 0
                    ): RecDotGovAvailabilityStatus.AVAILABLE.value,
                },
            ),
            102: CampsiteAvailabilityCampsite(
                site="Site 102",
                campsite_type="Standard Tent Only",
                availabilities={
                    datetime(2026, 9, 1, 0, 0): "UnknownStatusOrReserved",
                },
            ),
        }
    )

    with (
        patch.object(
            client, "paginate_recdotgov_campsites", new_callable=AsyncMock
        ) as mock_meta,
        patch.object(
            client, "make_recdotgov_availability_request", new_callable=AsyncMock
        ) as mock_req,
    ):
        mock_meta.return_value = [mock_campsite]
        mock_req.return_value = mock_avail_response

        # Search window Sept 1 -> Sept 3 (2 nights)
        results = await client.find_availabilities(
            park_id="234708",
            start_date=date(2026, 9, 1),
            end_date=date(2026, 9, 3),
        )

        assert len(results) == 1
        site_101 = results[0]
        assert site_101.campsite_id == "101"
        # Nights MUST only be Sept 1 and Sept 2. Sept 3 is checkout day!
        assert site_101.available_dates == [
            date(2026, 9, 1),
            date(2026, 9, 2),
        ]
        # Site 102 with UnknownStatusOrReserved had zero valid dates, so omitted
        assert all(r.campsite_id != "102" for r in results)


@pytest.mark.anyio
async def test_find_availabilities_invalid_window() -> None:
    """Test start_date >= end_date raises ValueError."""
    client = RecreationGovClient()
    with pytest.raises(ValueError, match="must precede"):
        await client.find_availabilities(
            park_id="234708",
            start_date=date(2026, 9, 3),
            end_date=date(2026, 9, 1),
        )
