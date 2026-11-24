"""Test list-campsites CLI command and provider site-catalog implementations."""

import json
from collections.abc import AsyncIterator
from unittest.mock import AsyncMock

import httpx2
import pytest
from click.testing import CliRunner

from camply.cli.main import cli
from camply.providers import PROVIDERS
from camply.providers.base import BaseProvider, ProviderFilterCapabilities
from camply.providers.dto import CampgroundSearchResult, CampsiteDTO, CampsiteType
from camply.providers.going_to_camp.variations import WashingtonStateParksProvider
from camply.providers.recreation_gov.provider import RecreationGovProvider
from camply.providers.reserve_america.provider import ReserveAmericaProvider
from camply.providers.usedirect.variations import ReserveCaliforniaProvider


def _campground(
    identifier: str = "232450", name: str = "Lower Pines"
) -> CampgroundSearchResult:
    return CampgroundSearchResult(
        provider_id=1,
        provider_name="Recreation.gov",
        campground_id=identifier,
        campground_name=name,
        recreation_area_id="2991",
        recreation_area_name="Yosemite National Park",
        state="CA",
        booking_url=f"https://www.recreation.gov/camping/campgrounds/{identifier}",
    )


def _sample_catalog() -> list[CampsiteDTO]:
    return [
        CampsiteDTO(
            campsite_id="90001",
            campsite_name="001",
            campsite_type=CampsiteType.TENT,
            capacity=6,
            available_dates=[],
            is_electric=False,
            is_accessible=False,
            permitted_equipment=["Tent"],
            max_vehicle_length=None,
            metadata={
                "loop": "Loop A",
                "booking_url": "https://www.recreation.gov/camping/campsites/90001",
            },
        ),
        CampsiteDTO(
            campsite_id="90002",
            campsite_name="002",
            campsite_type=CampsiteType.RV,
            capacity=8,
            available_dates=[],
            is_electric=True,
            is_accessible=True,
            permitted_equipment=["RV", "Trailer"],
            max_vehicle_length=35,
            metadata={
                "loop": "Loop B",
                "booking_url": "https://www.recreation.gov/camping/campsites/90002",
            },
        ),
        CampsiteDTO(
            campsite_id="90003",
            campsite_name="003",
            campsite_type=CampsiteType.RV,
            capacity=6,
            available_dates=[],
            is_electric=True,
            is_accessible=False,
            permitted_equipment=["RV"],
            max_vehicle_length=20,
            metadata={
                "loop": "Loop B",
                "booking_url": "https://www.recreation.gov/camping/campsites/90003",
            },
        ),
    ]


def test_list_campsites_requires_target_and_validates_filters(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Missing targets and unsupported provider filters fail before provider construction."""
    constructed: list[str] = []
    monkeypatch.setattr(
        PROVIDERS[1],
        "__init__",
        lambda self: constructed.append(type(self).__name__),
    )

    no_target = CliRunner().invoke(cli, ["list-campsites"])
    assert no_target.exit_code == 2
    assert "--rec-area or --campground" in no_target.stderr
    assert not constructed

    monkeypatch.setattr(
        PROVIDERS[1],
        "filter_capabilities",
        ProviderFilterCapabilities(min_rv_length=False),
    )
    unsupported = CliRunner().invoke(
        cli, ["list-campsites", "--campground", "232450", "--rv-length", "28"]
    )
    assert unsupported.exit_code == 2
    assert "RV / trailer length" in unsupported.stderr
    assert not constructed


def test_list_campsites_cli_filtering_precedence_limit_and_json(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify campground-over-area precedence, attribute filters, --search, --limit, and --json."""
    client = AsyncMock()
    lookups: list[str] = []
    areas: list[str] = []

    def init(self: BaseProvider) -> None:
        self.async_client = client

    async def lookup(_: BaseProvider, identifier: str) -> CampgroundSearchResult:
        lookups.append(identifier)
        return _campground(identifier)

    async def iterate(
        _: BaseProvider, identifier: str
    ) -> AsyncIterator[CampgroundSearchResult]:
        areas.append(identifier)
        yield _campground("232450")

    async def catalog(_: BaseProvider, park_id: str) -> list[CampsiteDTO]:
        assert park_id == "232450"
        return _sample_catalog()

    provider_cls = PROVIDERS[1]
    monkeypatch.setattr(provider_cls, "__init__", init)
    monkeypatch.setattr(provider_cls, "get_campground", lookup)
    monkeypatch.setattr(provider_cls, "iter_campgrounds", iterate)
    monkeypatch.setattr(provider_cls, "list_campsites", catalog)

    # 1. Terminal output with --campground overriding --rec-area and site filters
    filtered = CliRunner().invoke(
        cli,
        [
            "list-campsites",
            "--rec-area",
            "ignored-area",
            "--campground",
            "232450",
            "--campsite-type",
            "RV",
            "--electric",
            "--accessible",
            "--rv-length",
            "28",
        ],
    )
    assert filtered.exit_code == 0, filtered.output
    assert lookups == ["232450"]
    assert areas == []
    assert "Ignoring --rec-area" in filtered.stderr
    assert "1 Matching Campsites Found" in filtered.stdout
    assert "002 (#90002)" in filtered.stdout
    assert "Electric" in filtered.stdout
    assert "ADA" in filtered.stdout
    assert "Max 35ft" in filtered.stdout
    assert "Loop: Loop B" in filtered.stdout
    assert "90003" not in filtered.stdout

    # 2. --search matches loop/name/id and --limit + --json emits clean JSON on stdout
    json_res = CliRunner().invoke(
        cli,
        [
            "list-campsites",
            "--rec-area",
            "2991",
            "--search",
            "Loop B",
            "--limit",
            "1",
            "--json",
        ],
    )
    assert json_res.exit_code == 0, json_res.output
    assert areas == ["2991"]
    payload = json.loads(json_res.stdout)
    assert len(payload) == 1
    assert payload[0]["campsite_id"] == "90002"
    assert payload[0]["is_electric"] is True
    assert payload[0]["max_vehicle_length"] == 35
    assert payload[0]["loop"] == "Loop B"
    assert "more campsites exist" in json_res.stderr
    assert client.aclose.await_count == 2


@pytest.mark.asyncio
async def test_recreation_gov_list_campsites_is_date_independent() -> None:
    """RecreationGovProvider.list_campsites reads /api/search/campsites without availability calls."""
    seen_paths: list[str] = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        seen_paths.append(request.url.path)
        assert request.url.path == "/api/search/campsites"
        return httpx2.Response(
            200,
            json={
                "campsites": [
                    {
                        "campsite_id": 90010,
                        "name": "010",
                        "type": "STANDARD ELECTRIC",
                        "accessible": True,
                        "loop": "Loop A",
                        "permitted_equipment": [
                            {"equipment_name": "RV", "max_length": 32.0}
                        ],
                        "attributes": [
                            {
                                "attribute_id": 1,
                                "attribute_name": "Max Num of People",
                                "attribute_value": "6",
                            }
                        ],
                    },
                    {
                        "campsite_id": 90011,
                        "name": "011",
                        "type": "STANDARD NONELECTRIC",
                        "accessible": False,
                        "loop": "Loop A",
                        "permitted_equipment": [
                            {"equipment_name": "Tent", "max_length": 0.0}
                        ],
                        "attributes": [],
                    },
                ],
                "size": 1000,
                "start": 0,
                "total": 2,
            },
        )

    provider = RecreationGovProvider()
    provider.async_client = httpx2.AsyncClient(transport=httpx2.MockTransport(handler))
    try:
        sites = await provider.list_campsites("232450")
    finally:
        await provider.async_client.aclose()

    assert seen_paths == ["/api/search/campsites"]
    assert len(sites) == 2
    assert sites[0].campsite_id == "90010"
    assert sites[0].campsite_name == "010"
    assert sites[0].campsite_type == CampsiteType.RV
    assert sites[0].capacity == 6
    assert sites[0].is_electric is True
    assert sites[0].is_accessible is True
    assert sites[0].max_vehicle_length == 32
    assert sites[0].available_dates == []
    assert (
        sites[0].metadata["booking_url"]
        == "https://www.recreation.gov/camping/campsites/90010"
    )
    assert sites[1].campsite_id == "90011"
    assert sites[1].is_electric is False


@pytest.mark.asyncio
async def test_usedirect_list_campsites_returns_unavailable_units() -> None:
    """UseDirectProvider.list_campsites returns eligible units even when no slices are free."""

    def handler(request: httpx2.Request) -> httpx2.Response:
        if request.url.path.endswith("/search/filters"):
            return httpx2.Response(
                200,
                json={
                    "UnitTypesGroups": [
                        {"UnitTypesGroupId": 1, "UnitTypesGroupName": "RV Electric"}
                    ],
                    "NightlySleepingUnits": [
                        {"SleepingUnitId": 2, "SleepingUnitName": "RV"}
                    ],
                },
            )
        assert request.url.path.endswith("/search/grid")
        payload = json.loads(request.content)
        assert payload["InSeasonOnly"] is False
        return httpx2.Response(
            200,
            json={
                "NightsActual": 1,
                "Facility": {
                    "FacilityId": 327,
                    "FacilityAllowWebBooking": True,
                    "Units": {
                        "u1": {
                            "UnitId": 501,
                            "Name": "Site 501",
                            "AllowWebBooking": True,
                            "IsWebViewable": True,
                            "IsAda": True,
                            "UseType": 4,
                            "UnitTypeGroupId": 1,
                            "SleepingUnitIds": [2],
                            "VehicleLength": 40,
                            "MaxPersonOccupancy": 8,
                            "Slices": {"s1": {"Date": "2027-07-01", "IsFree": False}},
                        },
                        "u2": {
                            "UnitId": 502,
                            "Name": "Day Use",
                            "AllowWebBooking": True,
                            "UseType": 1,
                        },
                    },
                },
            },
        )

    provider = ReserveCaliforniaProvider()
    provider.async_client = httpx2.AsyncClient(transport=httpx2.MockTransport(handler))
    try:
        sites = await provider.list_campsites("327")
    finally:
        await provider.async_client.aclose()

    assert len(sites) == 1
    assert sites[0].campsite_id == "501"
    assert sites[0].campsite_name == "Site 501"
    assert sites[0].campsite_type == CampsiteType.RV
    assert sites[0].is_electric is True
    assert sites[0].is_accessible is True
    assert sites[0].max_vehicle_length == 40
    assert sites[0].available_dates == []


@pytest.mark.asyncio
async def test_going_to_camp_list_campsites_is_date_independent() -> None:
    """GoingToCampProvider.list_campsites reads resourcelocation/resources without map availability calls."""
    seen_paths: list[str] = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        seen_paths.append(request.url.path)
        if request.url.path.endswith("/resourceLocation"):
            return httpx2.Response(
                200,
                json=[
                    {
                        "resourceLocationId": 100,
                        "transactionLocationId": 10,
                        "rootMapId": 200,
                        "resourceCategoryIds": [1],
                        "localizedValues": [
                            {"cultureName": "en-US", "fullName": "Loop 1"}
                        ],
                    }
                ],
            )
        if request.url.path.endswith("/bookingcategories"):
            return httpx2.Response(
                200,
                json=[
                    {
                        "bookingCategoryId": 1,
                        "bookingModel": 0,
                        "allowedResourceCategoryIds": [1],
                        "localizedValues": [
                            {"cultureName": "en-US", "name": "Camping"}
                        ],
                    }
                ],
            )
        if request.url.path.endswith("/resourcecategory"):
            return httpx2.Response(
                200,
                json=[
                    {
                        "resourceCategoryId": 1,
                        "resourceType": 0,
                        "localizedValues": [
                            {"cultureName": "en-US", "name": "Tent Site"}
                        ],
                    }
                ],
            )
        if request.url.path.endswith("/equipment"):
            return httpx2.Response(
                200,
                json=[
                    {
                        "equipmentCategoryId": 5,
                        "localizedValues": [{"cultureName": "en-US", "name": "Tent"}],
                        "subEquipmentCategories": [],
                    }
                ],
            )
        if request.url.path.endswith("/attribute/filterable"):
            return httpx2.Response(200, json=[])
        if request.url.path.endswith("/resourcelocation/resources"):
            return httpx2.Response(
                200,
                json={
                    "777": {
                        "resourceId": 777,
                        "resourceLocationId": 100,
                        "resourceCategoryId": 1,
                        "resourceModel": 0,
                        "maxCapacity": 6,
                        "localizedValues": [
                            {"cultureName": "en-US", "name": "Site A1"}
                        ],
                        "allowedEquipment": [{"equipmentCategoryId": 5}],
                        "definedAttributes": [],
                    }
                },
            )
        raise AssertionError(f"Unexpected path {request.url.path}")

    provider = WashingtonStateParksProvider()
    provider.async_client = httpx2.AsyncClient(transport=httpx2.MockTransport(handler))
    try:
        sites = await provider.list_campsites("100")
    finally:
        await provider.async_client.aclose()

    assert not any("availability" in p for p in seen_paths)
    assert len(sites) == 1
    assert sites[0].campsite_id == "777"
    assert sites[0].campsite_name == "Site A1"
    assert sites[0].campsite_type == CampsiteType.TENT
    assert sites[0].available_dates == []


@pytest.mark.asyncio
async def test_reserve_america_list_campsites_returns_all_eligible_sites() -> None:
    """ReserveAmericaProvider.list_campsites includes eligible sites even when booked."""

    def handler(request: httpx2.Request) -> httpx2.Response:
        if request.url.path.endswith("/explore/search-results"):
            return httpx2.Response(200, text="ok")
        assert request.url.path.endswith("/products/NY/123")
        return httpx2.Response(
            200,
            json={
                "totalRecords": 1,
                "totalPages": 1,
                "control": {"currentPage": 0, "pageSize": 50},
                "records": [
                    {
                        "id": 999,
                        "name": "B04",
                        "prodGrpName": "Standard",
                        "prodInfo": {
                            "lineOfBusiness": "CAMPING",
                            "typeOfUse": "NIGHTLY",
                        },
                        "details": {
                            "stayType": "NIGHTLY",
                            "siteIcon": "tent",
                            "loopName": "Birch Loop",
                            "attributes": [
                                {"id": 12, "name": "Max Num of People", "value": ["6"]},
                                {"id": 104, "name": "ADA Access", "value": ["Y"]},
                            ],
                        },
                        "availabilityGrid": [
                            {"date": "2027-07-01", "status": "RESERVED"}
                        ],
                    }
                ],
            },
        )

    provider = ReserveAmericaProvider()
    provider.async_client = httpx2.AsyncClient(transport=httpx2.MockTransport(handler))
    try:
        sites = await provider.list_campsites("NY_123")
    finally:
        await provider.async_client.aclose()

    assert len(sites) == 1
    assert sites[0].campsite_id == "NY_123_999"
    assert sites[0].campsite_name == "B04"
    assert sites[0].campsite_type == CampsiteType.TENT
    assert sites[0].is_accessible is True
    assert sites[0].available_dates == []
    assert sites[0].metadata["loop"] == "Birch Loop"


@pytest.mark.asyncio
async def test_usedirect_list_campsites_rejects_upstream_error() -> None:
    """UseDirectProvider.list_campsites raises ValueError when NightsActual is 0."""

    def handler(request: httpx2.Request) -> httpx2.Response:
        if request.url.path.endswith("/search/filters"):
            return httpx2.Response(
                200, json={"UnitTypesGroups": [], "NightlySleepingUnits": []}
            )
        return httpx2.Response(
            200, json={"NightsActual": 0, "Facility": None, "Message": "Invalid date"}
        )

    provider = ReserveCaliforniaProvider()
    provider.async_client = httpx2.AsyncClient(transport=httpx2.MockTransport(handler))
    try:
        with pytest.raises(ValueError, match="Invalid date"):
            await provider.list_campsites("327")
    finally:
        await provider.async_client.aclose()


@pytest.mark.asyncio
async def test_going_to_camp_list_campsites_uses_booking_category_and_guards_mapless() -> (
    None
):
    """GoingToCampProvider.list_campsites honors booking-category type hints and skips mapless locations."""

    def handler(request: httpx2.Request) -> httpx2.Response:
        if request.url.path.endswith("/resourceLocation"):
            return httpx2.Response(
                200,
                json=[
                    {
                        "resourceLocationId": 100,
                        "transactionLocationId": 10,
                        "rootMapId": 200,
                        "resourceCategoryIds": [1],
                        "localizedValues": [
                            {"cultureName": "en-US", "fullName": "Loop 1"}
                        ],
                    },
                    {
                        "resourceLocationId": 101,
                        "transactionLocationId": 10,
                        "rootMapId": None,
                        "resourceCategoryIds": [1],
                        "localizedValues": [
                            {"cultureName": "en-US", "fullName": "Mapless"}
                        ],
                    },
                ],
            )
        if request.url.path.endswith("/bookingcategories"):
            return httpx2.Response(
                200,
                json=[
                    {
                        "bookingCategoryId": 1,
                        "bookingModel": 0,
                        "allowedResourceCategoryIds": [1],
                        "localizedValues": [
                            {"cultureName": "en-US", "name": "Cabin Lodging"}
                        ],
                    }
                ],
            )
        if request.url.path.endswith("/resourcecategory"):
            return httpx2.Response(
                200,
                json=[
                    {
                        "resourceCategoryId": 1,
                        "resourceType": 0,
                        "localizedValues": [
                            {"cultureName": "en-US", "name": "Standard Site"}
                        ],
                    }
                ],
            )
        if request.url.path.endswith("/equipment"):
            return httpx2.Response(200, json=[])
        if request.url.path.endswith("/attribute/filterable"):
            return httpx2.Response(200, json=[])
        if request.url.path.endswith("/resourcelocation/resources"):
            return httpx2.Response(
                200,
                json={
                    "888": {
                        "resourceId": 888,
                        "resourceLocationId": 100,
                        "resourceCategoryId": 1,
                        "resourceModel": 0,
                        "maxCapacity": 4,
                        "localizedValues": [{"cultureName": "en-US", "name": "C01"}],
                        "allowedEquipment": [],
                        "definedAttributes": [],
                    }
                },
            )
        raise AssertionError(f"Unexpected path {request.url.path}")

    provider = WashingtonStateParksProvider()
    provider.async_client = httpx2.AsyncClient(transport=httpx2.MockTransport(handler))
    try:
        assert await provider.list_campsites("101") == []
        sites = await provider.list_campsites("100")
    finally:
        await provider.async_client.aclose()

    assert len(sites) == 1
    assert sites[0].campsite_type == CampsiteType.CABIN
