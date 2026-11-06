"""Synthetic HTTP, model, CLI, and database regressions for GoingToCamp."""

from collections.abc import AsyncGenerator
from datetime import date
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import httpx2
import pytest
from click.testing import CliRunner
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from camply.db.models import Base, Campground, Provider, RecreationArea, Search
from camply.providers import PROVIDERS
from camply.providers.dto import CampsiteType
from camply.providers.going_to_camp.models.api import (
    AttributeDefinition,
    CatalogFilters,
    EquipmentCategory,
    Resource,
)
from camply.providers.going_to_camp.models.metadata import (
    BookingCategory,
    ResourceCategory,
    ResourceLocation,
    normalize_country_code,
    normalize_state_code,
    parse_gps_coordinates,
    resolve_overnight_categories,
)
from camply.providers.going_to_camp.provider import GoingToCampProvider
from camply.providers.going_to_camp.variations import WashingtonStateParksProvider


@pytest.fixture
def anyio_backend() -> str:
    """Run HTTP and database tests on asyncio."""
    return "asyncio"


@pytest.fixture
async def provider(
    monkeypatch: pytest.MonkeyPatch,
) -> AsyncGenerator[WashingtonStateParksProvider, None]:
    """Create an isolated Washington State Parks provider without pacing sleeps."""
    monkeypatch.setattr("camply.providers.going_to_camp.provider._REQUEST_INTERVAL", 0)
    instance = WashingtonStateParksProvider()
    await instance.async_client.aclose()
    yield instance
    await instance.async_client.aclose()


def synthetic_booking_categories() -> list[dict[str, Any]]:
    """Provide overnight, shelter/day-use, marina, and disabled booking categories."""
    return [
        {
            "bookingCategoryId": 0,
            "bookingModel": 0,
            "isDisabled": False,
            "allowedResourceCategoryIds": [-2147483648, -2147483645],
            "localizedValues": [{"cultureName": "en-US", "name": "Campsite"}],
        },
        {
            "bookingCategoryId": 1,
            "bookingModel": 0,
            "isDisabled": False,
            "allowedResourceCategoryIds": [-2147483640],
            "localizedValues": [
                {"cultureName": "en-US", "name": "Roofed Accommodation"}
            ],
        },
        {
            "bookingCategoryId": 2,
            "bookingModel": 1,
            "isDisabled": False,
            "allowedResourceCategoryIds": [-2147483630],
            "localizedValues": [{"cultureName": "en-US", "name": "Day Use Shelter"}],
        },
        {
            "bookingCategoryId": 3,
            "bookingModel": 0,
            "isDisabled": False,
            "allowedResourceCategoryIds": [-2147483620],
            "localizedValues": [{"cultureName": "en-US", "name": "Marina Moorage"}],
        },
        {
            "bookingCategoryId": 4,
            "bookingModel": 0,
            "isDisabled": True,
            "allowedResourceCategoryIds": [-2147483610],
            "localizedValues": [{"cultureName": "en-US", "name": "Retired Overnight"}],
        },
    ]


def synthetic_resource_categories() -> list[dict[str, Any]]:
    """Provide frontcountry, backcountry, cabin, day-use, and slip resource categories."""
    return [
        {
            "resourceCategoryId": -2147483648,
            "resourceType": 0,
            "localizedValues": [{"cultureName": "en-US", "name": "Standard Campsite"}],
        },
        {
            "resourceCategoryId": -2147483645,
            "resourceType": 3,
            "localizedValues": [{"cultureName": "en-US", "name": "Marine Trail Site"}],
        },
        {
            "resourceCategoryId": -2147483640,
            "resourceType": 0,
            "localizedValues": [{"cultureName": "en-US", "name": "Cabin"}],
        },
        {
            "resourceCategoryId": -2147483630,
            "resourceType": 2,
            "localizedValues": [{"cultureName": "en-US", "name": "Picnic Shelter"}],
        },
        {
            "resourceCategoryId": -2147483620,
            "resourceType": 1,
            "localizedValues": [{"cultureName": "en-US", "name": "Moorage Slip"}],
        },
    ]


def synthetic_equipment() -> list[dict[str, Any]]:
    """Put Group at index 0 to ensure lookup spans all equipment categories."""
    return [
        {
            "equipmentCategoryId": -32767,
            "localizedValues": [{"cultureName": "en-US", "name": "Group"}],
            "subEquipmentCategories": [
                {
                    "subEquipmentCategoryId": -32768,
                    "localizedValues": [{"cultureName": "en-US", "name": "Group Tent"}],
                }
            ],
        },
        {
            "equipmentCategoryId": -32768,
            "localizedValues": [{"cultureName": "en-US", "name": "Single"}],
            "subEquipmentCategories": [
                {
                    "subEquipmentCategoryId": -32768,
                    "localizedValues": [{"cultureName": "en-US", "name": "Small Tent"}],
                },
                {
                    "subEquipmentCategoryId": -32766,
                    "localizedValues": [
                        {"cultureName": "en-US", "name": "RV/Trailer up to 35ft"}
                    ],
                },
            ],
        },
    ]


def synthetic_attributes() -> dict[str, dict[str, Any]]:
    """Provide service, amperage, accessibility, proximity, and RV count attributes."""
    return {
        "1": {
            "attributeDefinitionId": 1,
            "localizedValues": [
                {"cultureName": "en-US", "displayName": "Service Type"}
            ],
            "values": [
                {
                    "enumValue": 1,
                    "localizedValues": [
                        {
                            "cultureName": "en-US",
                            "displayName": "Standard - No Hook-ups",
                        }
                    ],
                },
                {
                    "enumValue": 2,
                    "localizedValues": [
                        {"cultureName": "en-US", "displayName": "Full Hook-up (E/W/S)"}
                    ],
                },
                {
                    "enumValue": 3,
                    "localizedValues": [
                        {"cultureName": "en-US", "displayName": "Water Only"}
                    ],
                },
            ],
        },
        "2": {
            "attributeDefinitionId": 2,
            "localizedValues": [
                {"cultureName": "en-US", "displayName": "Electrical Service"}
            ],
            "values": [
                {
                    "enumValue": 1,
                    "localizedValues": [
                        {"cultureName": "en-US", "displayName": "20 Amps"}
                    ],
                },
                {
                    "enumValue": 2,
                    "localizedValues": [
                        {"cultureName": "en-US", "displayName": "30 Amps"}
                    ],
                },
                {
                    "enumValue": 3,
                    "localizedValues": [
                        {"cultureName": "en-US", "displayName": "50 Amps"}
                    ],
                },
                {
                    "enumValue": 4,
                    "localizedValues": [
                        {"cultureName": "en-US", "displayName": "Not Available"}
                    ],
                },
            ],
        },
        "3": {
            "attributeDefinitionId": 3,
            "localizedValues": [
                {"cultureName": "en-US", "displayName": "ADA Accessible"}
            ],
            "values": [
                {
                    "enumValue": 1,
                    "localizedValues": [{"cultureName": "en-US", "displayName": "Yes"}],
                },
                {
                    "enumValue": 2,
                    "localizedValues": [{"cultureName": "en-US", "displayName": "No"}],
                },
            ],
        },
        "4": {
            "attributeDefinitionId": 4,
            "localizedValues": [{"cultureName": "en-US", "displayName": "Adjacent To"}],
            "values": [
                {
                    "enumValue": 1,
                    "localizedValues": [
                        {"cultureName": "en-US", "displayName": "ADA Restroom"}
                    ],
                }
            ],
        },
        "5": {
            "attributeDefinitionId": 5,
            "localizedValues": [{"cultureName": "en-US", "displayName": "Max RVs"}],
            "values": [],
        },
        "6": {
            "attributeDefinitionId": 6,
            "localizedValues": [
                {"cultureName": "en-US", "displayName": "Electrical Outlets"}
            ],
            "values": [],
        },
    }


def build_filters() -> CatalogFilters:
    """Build parsed CatalogFilters from synthetic GoingToCamp dictionaries."""
    return CatalogFilters.build(
        resource_locations=[
            ResourceLocation.model_validate(
                {
                    "resourceLocationId": -2147483631,
                    "transactionLocationId": -2147483640,
                    "rootMapId": 100,
                    "region": "Washington",
                    "country": "USA",
                    "resourceCategoryIds": [-2147483648, -2147483640],
                    "localizedValues": [
                        {"cultureName": "en-US", "fullName": "Synthetic Bay Campground"}
                    ],
                }
            ),
            ResourceLocation.model_validate(
                {
                    "resourceLocationId": -2147483632,
                    "transactionLocationId": -2147483640,
                    "rootMapId": None,
                    "region": "Washington",
                    "country": "USA",
                    "resourceCategoryIds": [],
                    "localizedValues": [
                        {"cultureName": "en-US", "fullName": "Unmapped Campground"}
                    ],
                }
            ),
        ],
        booking_categories=[
            BookingCategory.model_validate(bc) for bc in synthetic_booking_categories()
        ],
        resource_categories=[
            ResourceCategory.model_validate(rc)
            for rc in synthetic_resource_categories()
        ],
        equipment_categories=[
            EquipmentCategory.model_validate(eq) for eq in synthetic_equipment()
        ],
        attributes=[
            AttributeDefinition.model_validate(attr)
            for attr in synthetic_attributes().values()
        ],
    )


def test_going_to_camp_remains_abstract() -> None:
    """GoingToCampProvider cannot be instantiated without a concrete deployment."""
    with pytest.raises(TypeError):
        GoingToCampProvider()  # type: ignore[abstract]


def test_registry_and_booking_links() -> None:
    """Provider ID 12 is registered and builds GoingToCamp deep links."""
    assert PROVIDERS[12] is WashingtonStateParksProvider
    assert (
        WashingtonStateParksProvider.get_rec_area_url("-2147483640")
        == "https://washington.goingtocamp.com/create-booking/results?transactionLocationId=-2147483640"
    )
    assert (
        WashingtonStateParksProvider.get_campground_url("-2147483631")
        == "https://washington.goingtocamp.com/create-booking/results?resourceLocationId=-2147483631"
    )
    assert (
        WashingtonStateParksProvider.get_campground_url(
            "-2147483631", rec_area_id="-2147483640"
        )
        == "https://washington.goingtocamp.com/create-booking/results?resourceLocationId=-2147483631&transactionLocationId=-2147483640"
    )


def test_api_campground_serialization_url() -> None:
    """Serialized API campgrounds include Washington State Parks booking links."""
    from camply.server.models.campgrounds import Campground as APICampground

    campground = APICampground(
        id="-2147483631",
        provider_id=12,
        recreation_area_id="-2147483640",
        name="Synthetic Bay Campground",
        description=None,
        country="US",
        state="WA",
        longitude=-122.65,
        latitude=48.40,
    )
    assert (
        campground.model_dump()["url"]
        == "https://washington.goingtocamp.com/create-booking/results?resourceLocationId=-2147483631&transactionLocationId=-2147483640"
    )


def test_metadata_cli_lists_and_invokes_washington(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """CLI help exposes ID 12 and closes the async client when population fails."""
    from camply.cli.db import metadata_cmd

    help_result = CliRunner().invoke(metadata_cmd, ["--help"])
    assert help_result.exit_code == 0
    assert "12 = WashingtonStateParks" in help_result.output

    instance = MagicMock()
    instance.populate_database = AsyncMock(
        side_effect=RuntimeError("synthetic failure")
    )
    instance.async_client.aclose = AsyncMock()
    factory = MagicMock(return_value=instance)
    monkeypatch.setitem(PROVIDERS, 12, factory)
    result = CliRunner().invoke(metadata_cmd, ["--provider-id", "12"])
    assert isinstance(result.exception, RuntimeError)
    factory.assert_called_once_with()
    instance.populate_database.assert_awaited_once()
    instance.async_client.aclose.assert_awaited_once()


def test_dynamic_overnight_category_resolution() -> None:
    """Resolve nightly frontcountry/backcountry categories while excluding day use and moorage."""
    booking_cats, resource_cats = resolve_overnight_categories(
        [BookingCategory.model_validate(bc) for bc in synthetic_booking_categories()],
        [ResourceCategory.model_validate(rc) for rc in synthetic_resource_categories()],
    )
    assert sorted(booking_cats) == [0, 1]
    assert sorted(resource_cats) == [-2147483648, -2147483645, -2147483640]


@pytest.mark.parametrize(
    "raw_coords,expected",
    [
        ("48.4055, -122.6461", (48.4055, -122.6461)),
        (" 47.1 , -123.5 ", (47.1, -123.5)),
        ("0, 0", (None, None)),
        ("99.9, -122.0", (None, None)),
        ("invalid", (None, None)),
        (None, (None, None)),
    ],
)
def test_gps_coordinate_parsing(
    raw_coords: str | None, expected: tuple[float | None, float | None]
) -> None:
    """Parse valid lat/lng pairs and reject zeroed or out-of-range coordinates."""
    assert parse_gps_coordinates(raw_coords) == expected


def test_state_and_country_normalization() -> None:
    """Normalize full state/province/country names and fall back when blank."""
    assert normalize_state_code("Washington", "WA") == "WA"
    assert normalize_state_code("British Columbia", "WA") == "BC"
    assert normalize_state_code(" wi ", "WA") == "WI"
    assert normalize_state_code("", "WA") == "WA"
    assert normalize_state_code(None, "WA") == "WA"
    assert normalize_country_code("USA", "US") == "US"
    assert normalize_country_code("Canada", "US") == "CA"
    assert normalize_country_code(None, "US") == "US"


def test_resource_classification_and_attribute_decoding() -> None:
    """Classify cabins, RVs, tents, hookups, multi-enum amps, capacities, and ADA flags."""
    filters = build_filters()

    scalar = Resource.model_validate(
        {
            "definedAttributes": [
                {"attributeDefinitionId": 2, "value": 1},
                {"attributeDefinitionId": 3, "value": 1},
                {"attributeDefinitionId": 5, "value": 2},
            ]
        }
    )
    decoded = scalar._decode_attributes(filters)
    assert decoded["Electrical Service"] == "20 Amps"
    assert decoded["ADA Accessible"] == "Yes"
    assert decoded["Max RVs"] == 2

    # 1. RV site with multi-enum Electrical Service + Adjacent To: ADA Restroom (NOT accessible!)
    rv_site = Resource.model_validate(
        {
            "resourceId": 101,
            "resourceCategoryId": -2147483648,
            "resourceModel": 0,
            "minCapacity": 1,
            "maxCapacity": 8,
            "maxStay": 10,
            "localizedValues": [{"cultureName": "en-US", "name": "RV-01"}],
            "allowedEquipment": [
                {"equipmentCategoryId": -32768, "subEquipmentCategoryId": -32766}
            ],
            "definedAttributes": [
                {"attributeDefinitionId": 2, "values": [1, 2, 3]},
                {"attributeDefinitionId": 4, "values": [1]},
            ],
        }
    )
    rv_dto = rv_site.to_dto(
        filters=filters,
        available_dates={date(2030, 7, 10)},
        booking_category_names=["Campsite"],
    )
    assert rv_dto is not None
    assert rv_dto.campsite_type == CampsiteType.RV
    assert rv_dto.is_electric is True
    assert rv_dto.is_accessible is False
    assert rv_dto.capacity == 8
    assert rv_dto.metadata["attributes"]["Electrical Service"] == [
        "20 Amps",
        "30 Amps",
        "50 Amps",
    ]
    assert rv_dto.metadata["permitted_equipment"] == ["RV/Trailer up to 35ft"]

    # 2. Tent site with explicit non-electric ("Standard - No Hook-ups" + "Not Available") and ADA Yes
    tent_site = Resource.model_validate(
        {
            "resourceId": 102,
            "resourceCategoryId": -2147483648,
            "resourceModel": 0,
            "minCapacity": None,
            "maxCapacity": 50,
            "localizedValues": [{"cultureName": "en-US", "name": "G1"}],
            "allowedEquipment": [
                {"equipmentCategoryId": -32767, "subEquipmentCategoryId": -32768}
            ],
            "definedAttributes": [
                {"attributeDefinitionId": 1, "values": [1]},
                {"attributeDefinitionId": 2, "values": [4]},
                {"attributeDefinitionId": 3, "values": [1]},
            ],
        }
    )
    tent_dto = tent_site.to_dto(
        filters=filters,
        available_dates={date(2030, 7, 10)},
        booking_category_names=["Campsite"],
    )
    assert tent_dto is not None
    assert tent_dto.campsite_type == CampsiteType.TENT
    assert tent_dto.is_electric is False
    assert tent_dto.is_accessible is True
    assert tent_dto.capacity == 50
    assert tent_dto.metadata["permitted_equipment"] == ["Group Tent"]

    # 3. Cabin with Electrical Outlets > 0 and unknown capacity (maxCapacity=None -> 0)
    cabin_site = Resource.model_validate(
        {
            "resourceId": 103,
            "resourceCategoryId": -2147483640,
            "resourceModel": 0,
            "maxCapacity": None,
            "localizedValues": [{"cultureName": "en-US", "name": "Cabin C1"}],
            "definedAttributes": [{"attributeDefinitionId": 6, "value": 2}],
        }
    )
    cabin_dto = cabin_site.to_dto(
        filters=filters,
        available_dates={date(2030, 7, 10)},
        booking_category_names=["Roofed Accommodation"],
    )
    assert cabin_dto is not None
    assert cabin_dto.campsite_type == CampsiteType.CABIN
    assert cabin_dto.is_electric is True
    assert cabin_dto.capacity == 0

    # 4. Water-only site with Max RVs = 0 and no tent equipment -> OTHER, non-electric
    other_site = Resource.model_validate(
        {
            "resourceId": 104,
            "resourceCategoryId": -2147483645,
            "resourceModel": 0,
            "maxCapacity": None,
            "localizedValues": [{"cultureName": "en-US", "name": "Mooring Trail"}],
            "definedAttributes": [
                {"attributeDefinitionId": 1, "values": [3]},
                {"attributeDefinitionId": 5, "value": 0},
            ],
        }
    )
    other_dto = other_site.to_dto(
        filters=filters,
        available_dates={date(2030, 7, 10)},
        booking_category_names=["Campsite"],
    )
    assert other_dto is not None
    assert other_dto.campsite_type == CampsiteType.OTHER
    assert other_dto.is_electric is False


@pytest.mark.parametrize(
    "ineligible_payload",
    [
        {"resourceId": None, "resourceCategoryId": -2147483648, "resourceModel": 0},
        {"resourceId": 200, "resourceCategoryId": -2147483648, "resourceModel": 1},
        {"resourceId": 201, "resourceCategoryId": -2147483630, "resourceModel": 0},
        {
            "resourceId": 202,
            "resourceCategoryId": -2147483648,
            "resourceModel": 0,
            "maxCapacity": 0,
        },
    ],
)
def test_ineligible_resources_excluded(ineligible_payload: dict[str, Any]) -> None:
    """Exclude non-specific zones, day-use categories, and zero-capacity placeholders."""
    filters = build_filters()
    resource = Resource.model_validate(ineligible_payload)
    assert resource.is_eligible(filters) is False
    assert resource.to_dto(filters=filters, available_dates={date(2030, 7, 10)}) is None


@pytest.mark.anyio
async def test_find_availabilities_map_traversal_statuses_and_clipping(
    provider: WashingtonStateParksProvider,
) -> None:
    """Traverse open child loop maps, prune closed maps, filter statuses 1..8, and clip check-out."""
    provider._filters = build_filters()
    map_requests: list[tuple[int, int, str, str]] = []

    resources_payload = {
        "101": {
            "resourceId": 101,
            "resourceCategoryId": -2147483648,
            "resourceModel": 0,
            "maxCapacity": 6,
            "localizedValues": [{"cultureName": "en-US", "name": "Loop A-01"}],
            "allowedEquipment": [
                {"equipmentCategoryId": -32768, "subEquipmentCategoryId": -32768}
            ],
        },
        "102": {
            "resourceId": 102,
            "resourceCategoryId": -2147483640,
            "resourceModel": 0,
            "maxCapacity": 4,
            "localizedValues": [{"cultureName": "en-US", "name": "Cabin B-01"}],
        },
        "103": {
            "resourceId": 103,
            "resourceCategoryId": -2147483648,
            "resourceModel": 0,
            "maxCapacity": 6,
            "localizedValues": [{"cultureName": "en-US", "name": "Unbookable Site"}],
        },
    }

    def respond(request: httpx2.Request) -> httpx2.Response:
        if request.url.path.endswith("/resourcelocation/resources"):
            return httpx2.Response(200, json=resources_payload)
        assert request.url.path.endswith("/availability/map")
        params = request.url.params
        map_id = int(params["mapId"])
        bc_id = int(params["bookingCategoryId"])
        map_requests.append((map_id, bc_id, params["startDate"], params["endDate"]))
        if bc_id == 0 and map_id == 100:
            # Root map links to 101 (partially available), 102 (closed/non-reservable -> pruned!), and 100 (cycle guard)
            return httpx2.Response(
                200,
                json={
                    "mapId": 100,
                    "resourceAvailabilities": {},
                    "mapLinkAvailabilities": {
                        "101": [7, 1, 0],
                        "102": [
                            2,
                            3,
                            0,
                        ],  # index 2 is check-out date, so nights [0,1] are [2,3] -> pruned!
                        "100": [0, 0, 0],
                    },
                },
            )
        if bc_id == 0 and map_id == 101:
            # Site 101 is available on night 0, unavailable (1) on night 1, available (0) on check-out night 2 (must be clipped!)
            # Site 103 has non-zero statuses (3=walk-in, 8=held) -> excluded!
            return httpx2.Response(
                200,
                json={
                    "mapId": 101,
                    "resourceAvailabilities": {
                        "101": [
                            {"availability": 0},
                            {"availability": 1},
                            {"availability": 0},
                        ],
                        "103": [
                            {"availability": 3},
                            {"availability": 8},
                            {"availability": 0},
                        ],
                    },
                    "mapLinkAvailabilities": {},
                },
            )
        if bc_id == 1 and map_id == 100:
            return httpx2.Response(
                200,
                json={
                    "mapId": 100,
                    "resourceAvailabilities": {
                        "102": [
                            {"availability": 6},
                            {"availability": 0},
                            {"availability": 0},
                        ]
                    },
                    "mapLinkAvailabilities": {},
                },
            )
        raise AssertionError(f"Unexpected map call: {(map_id, bc_id)}")

    provider.async_client = httpx2.AsyncClient(transport=httpx2.MockTransport(respond))
    results = await provider.find_availabilities(
        "-2147483631", start_date=date(2030, 7, 10), end_date=date(2030, 7, 12)
    )
    by_id = {dto.campsite_id: dto for dto in results}
    assert sorted(by_id) == ["101", "102"]
    assert by_id["101"].available_dates == [date(2030, 7, 10)]
    assert by_id["101"].campsite_type == CampsiteType.TENT
    assert by_id["102"].available_dates == [date(2030, 7, 11)]
    assert by_id["102"].campsite_type == CampsiteType.CABIN
    assert map_requests == [
        (100, 0, "2030-07-10", "2030-07-12"),
        (101, 0, "2030-07-10", "2030-07-12"),
        (100, 1, "2030-07-10", "2030-07-12"),
    ]


@pytest.mark.anyio
async def test_chunking_and_deduplication(
    provider: WashingtonStateParksProvider,
) -> None:
    """Long searches split into 60-night windows and merge per-site dates."""
    provider._filters = build_filters()
    windows: list[tuple[str, str]] = []

    def respond(request: httpx2.Request) -> httpx2.Response:
        if request.url.path.endswith("/resourcelocation/resources"):
            return httpx2.Response(
                200,
                json={
                    "101": {
                        "resourceId": 101,
                        "resourceCategoryId": -2147483648,
                        "resourceModel": 0,
                        "maxCapacity": 6,
                        "localizedValues": [{"cultureName": "en-US", "name": "A1"}],
                    }
                },
            )
        params = request.url.params
        windows.append((params["startDate"], params["endDate"]))
        start = date.fromisoformat(params["startDate"])
        end = date.fromisoformat(params["endDate"])
        nights = (end - start).days
        # Mark only first night of each chunk and padded check-out entry as available (0)
        entries = [
            {"availability": 0 if idx in (0, nights) else 1}
            for idx in range(nights + 2)
        ]
        return httpx2.Response(
            200,
            json={
                "mapId": 100,
                "resourceAvailabilities": {"101": entries},
                "mapLinkAvailabilities": {},
            },
        )

    provider.async_client = httpx2.AsyncClient(transport=httpx2.MockTransport(respond))
    results = await provider.find_availabilities(
        "-2147483631", start_date=date(2030, 6, 1), end_date=date(2030, 8, 5)
    )
    assert windows == [
        ("2030-06-01", "2030-07-31"),
        ("2030-07-31", "2030-08-05"),
    ]
    assert len(results) == 1
    assert results[0].available_dates == [date(2030, 6, 1), date(2030, 7, 31)]


@pytest.mark.anyio
async def test_unknown_unmapped_and_invalid_inputs(
    provider: WashingtonStateParksProvider,
) -> None:
    """Reject invalid ranges, unknown campgrounds, HTTP 5xx, and return [] when rootMapId is None."""
    other = WashingtonStateParksProvider()
    try:
        provider.async_client = AsyncMock()
        with pytest.raises(ValueError, match="Check-out"):
            await provider.find_availabilities(
                "-2147483631",
                start_date=date(2030, 7, 10),
                end_date=date(2030, 7, 10),
            )
        provider.async_client.request.assert_not_called()

        provider._filters = build_filters()
        assert other._filters is None

        # Unmapped facility (rootMapId=None) returns [] without HTTP availability calls
        assert (
            await provider.find_availabilities(
                "-2147483632",
                start_date=date(2030, 7, 10),
                end_date=date(2030, 7, 12),
            )
            == []
        )

        # Unknown facility raises ValueError naming the provider
        with pytest.raises(ValueError, match="Washington State Parks"):
            await provider.find_availabilities(
                "999999",
                start_date=date(2030, 7, 10),
                end_date=date(2030, 7, 12),
            )

        # Non-numeric campground ID raises ValueError naming the provider
        with pytest.raises(ValueError, match="Washington State Parks"):
            await provider.find_availabilities(
                "not-an-int",
                start_date=date(2030, 7, 10),
                end_date=date(2030, 7, 12),
            )

        # HTTP 503 propagates HTTPStatusError
        provider._filters = None
        provider.async_client = httpx2.AsyncClient(
            transport=httpx2.MockTransport(lambda _r: httpx2.Response(503))
        )
        with pytest.raises(httpx2.HTTPStatusError):
            await provider.find_availabilities(
                "-2147483631",
                start_date=date(2030, 7, 10),
                end_date=date(2030, 7, 12),
            )
    finally:
        await other.async_client.aclose()


def _synthetic_metadata_catalogs() -> tuple[
    list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]
]:
    """Build synthetic GoingToCamp park/facility/category payloads for ingestion tests."""
    parks = [
        {
            "transactionLocationId": -2147483640,
            "isDisabled": False,
            "gpsCoordinates": "48.4055, -122.6461",
            "regionCode": "WA",
            "rootMapId": 10,
            "localizedValues": [
                {
                    "cultureName": "en-US",
                    "fullName": "DECEPTION PASS STATE PARK",
                    "city": "Oak Harbor",
                    "description": "Coastal park",
                }
            ],
        },
        {
            "transactionLocationId": -2147483639,
            "isDisabled": False,
            "gpsCoordinates": "47.5000, -122.1000",
            "regionCode": "WA",
            "rootMapId": 20,
            "localizedValues": [
                {"cultureName": "en-US", "fullName": "Day Use Only Park"}
            ],
        },
    ]
    facilities = [
        {
            "resourceLocationId": -2147483631,
            "transactionLocationId": -2147483640,
            "rootMapId": 100,
            "gpsCoordinates": "48.4100, -122.6500",
            "region": "Washington",
            "country": "USA",
            "resourceCategoryIds": [-2147483648],
            "localizedValues": [
                {"cultureName": "en-US", "fullName": "CRANBERRY LAKE CAMPGROUND"}
            ],
        },
        {
            "resourceLocationId": -2147483630,
            "transactionLocationId": -2147483639,
            "rootMapId": 200,
            "region": "Washington",
            "country": "USA",
            "resourceCategoryIds": [-2147483630, -2147483620],
            "localizedValues": [
                {"cultureName": "en-US", "fullName": "Picnic & Marina Area"}
            ],
        },
        {
            "resourceLocationId": -2147483629,
            "transactionLocationId": 999999,
            "rootMapId": 300,
            "resourceCategoryIds": [-2147483648],
            "localizedValues": [{"cultureName": "en-US", "fullName": "Orphan"}],
        },
    ]
    catalogs = {
        "/api/transactionlocation": parks,
        "/api/resourceLocation": facilities,
        "/api/bookingcategories": synthetic_booking_categories(),
        "/api/resourcecategory": synthetic_resource_categories(),
    }
    return parks, facilities, catalogs


async def _assert_ingested_catalog(maker: async_sessionmaker[Any]) -> None:
    """Verify park/campground rows, searchable campgrounds, and provider isolation."""
    async with maker() as session:
        wa_parks = (
            await session.scalars(
                select(RecreationArea).where(RecreationArea.provider_id == 12)
            )
        ).all()
        wa_campgrounds = (
            await session.scalars(
                select(Campground).where(Campground.provider_id == 12)
            )
        ).all()
        wa_search = (
            await session.scalars(select(Search).where(Search.provider_id == 12))
        ).all()
        assert len(wa_parks) == 2
        assert len(wa_campgrounds) == 2
        overnight_cg = next(c for c in wa_campgrounds if c.id == "-2147483631")
        day_use_cg = next(c for c in wa_campgrounds if c.id == "-2147483630")
        assert overnight_cg.name == "Cranberry Lake Campground"
        assert overnight_cg.city == "Oak Harbor"
        assert overnight_cg.state == "WA"
        assert overnight_cg.country == "US"
        assert overnight_cg.reservable is True and overnight_cg.enabled is True
        assert day_use_cg.reservable is False and day_use_cg.enabled is True
        cg_search = [s for s in wa_search if s.entity_type == "Campground"]
        assert len(cg_search) == 1
        assert cg_search[0].campground_id == "-2147483631"
        assert cg_search[0].recreation_area_name == "Deception Pass State Park"
        other_park = await session.get(RecreationArea, ("-2147483640", 1))
        assert other_park is not None
        assert other_park.name == "Colliding Other Park"


@pytest.mark.anyio
async def test_metadata_ingestion_atomicity_and_provider_isolation(
    provider: WashingtonStateParksProvider, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Ingest parks/campgrounds atomically, exclude day-use/moorage from search, and isolate colliding IDs."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    maker = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    async with maker() as session:
        session.add(Provider(id=1, name="Other Provider", url="https://example.com"))
        await session.flush()
        session.add(
            RecreationArea(id="-2147483640", provider_id=1, name="Colliding Other Park")
        )
        session.add(
            Campground(
                id="-2147483631",
                provider_id=1,
                recreation_area_id="-2147483640",
                name="Colliding Other Campground",
            )
        )
        await session.commit()

    monkeypatch.setattr(
        "camply.providers.going_to_camp.provider.db",
        SimpleNamespace(get_session=maker),
    )
    parks, facilities, catalogs = _synthetic_metadata_catalogs()

    def respond(request: httpx2.Request) -> httpx2.Response:
        assert request.method == "GET"
        return httpx2.Response(200, json=catalogs[request.url.path])

    provider.async_client = httpx2.AsyncClient(transport=httpx2.MockTransport(respond))
    try:
        await provider.sync_metadata()
        await _assert_ingested_catalog(maker)

        parks[0]["localizedValues"][0]["fullName"] = "Uncommitted Rename"
        with monkeypatch.context() as patch:
            patch.setattr(
                provider,
                "populate_search_table",
                AsyncMock(side_effect=RuntimeError("synthetic search failure")),
            )
            with pytest.raises(RuntimeError, match="synthetic search failure"):
                await provider.sync_metadata()
        async with maker() as session:
            park = await session.get(RecreationArea, ("-2147483640", 12))
            assert park is not None
            assert park.name == "Deception Pass State Park"

        # Retiring disappeared facilities disables them and removes from Search without deleting rows
        facilities.clear()
        await provider.sync_metadata()
        async with maker() as session:
            retired = await session.get(Campground, ("-2147483631", 12))
            assert retired is not None
            assert retired.enabled is False and retired.reservable is False
            assert not (
                await session.scalars(
                    select(Search).where(
                        Search.provider_id == 12, Search.entity_type == "Campground"
                    )
                )
            ).all()
    finally:
        await engine.dispose()


@pytest.mark.vcr(
    record_mode="none",
    match_on=["method", "scheme", "host", "port", "path", "query", "body"],
)
@pytest.mark.anyio
async def test_washington_going_to_camp_http_replay() -> None:
    """Replay synthetic GoingToCamp HTTP responses through the real base retry transport."""
    provider = WashingtonStateParksProvider()
    try:
        results = await provider.find_availabilities(
            "-2147483631", start_date=date(2030, 7, 10), end_date=date(2030, 7, 12)
        )
        assert len(results) == 1
        site = results[0]
        assert site.campsite_id == "-2147483001"
        assert site.campsite_name == "Site A01"
        assert site.campsite_type == CampsiteType.RV
        assert site.capacity == 8
        assert site.available_dates == [date(2030, 7, 10), date(2030, 7, 11)]
        assert site.is_electric is True
        assert site.is_accessible is True
        assert site.metadata["attributes"]["Electrical Service"] == [
            "30 Amps",
            "50 Amps",
        ]
    finally:
        await provider.async_client.aclose()
