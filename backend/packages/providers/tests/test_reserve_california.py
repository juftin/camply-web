"""Synthetic HTTP and database regressions for ReserveCalifornia."""

import json
from collections.abc import AsyncGenerator
from datetime import date
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest
from click.testing import CliRunner
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from db.models import Base, Campground, Provider, RecreationArea, Search
from providers import PROVIDERS
from providers.dto import CampsiteType
from providers.reserve_california.provider import ReserveCaliforniaProvider
from providers.usedirect.models.api import AvailabilityUnit, SearchFilters


@pytest.fixture
def anyio_backend() -> str:
    """Run HTTP and database tests on asyncio."""
    return "asyncio"


@pytest.fixture
async def provider(
    monkeypatch: pytest.MonkeyPatch,
) -> AsyncGenerator[ReserveCaliforniaProvider, None]:
    """Create an isolated provider without real rate-limit sleeps."""
    monkeypatch.setattr("providers.usedirect.provider._REQUEST_INTERVAL", 0)
    instance = ReserveCaliforniaProvider()
    await instance.async_client.aclose()
    yield instance
    await instance.async_client.aclose()


def filters() -> dict[str, Any]:
    """Describe synthetic equipment and classification lookups."""
    return {
        "UnitTypesGroups": [
            {"UnitTypesGroupId": 1, "UnitTypesGroupName": "Campsite"},
            {"UnitTypesGroupId": 2, "UnitTypesGroupName": "Tent Site"},
            {"UnitTypesGroupId": 3, "UnitTypesGroupName": "Hook Up (E/W/S)"},
            {"UnitTypesGroupId": 4, "UnitTypesGroupName": "Hook Up (W/S)"},
            {"UnitTypesGroupId": 5, "UnitTypesGroupName": "Cabin"},
        ],
        "NightlySleepingUnits": [
            {"SleepingUnitId": 1, "SleepingUnitName": "Tent"},
            {"SleepingUnitId": 2, "SleepingUnitName": "RV/Motorhome"},
        ],
    }


def unit(**overrides: Any) -> dict[str, Any]:
    """Create one synthetic overnight unit and deliberately unordered slices."""
    return {
        "UnitId": 100,
        "Name": "Test Campsite 100",
        "AllowWebBooking": True,
        "IsWebViewable": True,
        "IsAda": True,
        "UseType": 4,
        "UnitTypeGroupId": 3,
        "SleepingUnitIds": [2],
        "VehicleLength": 30,
        "Slices": {
            "2030-01-03T00:00:00": {"Date": "2030-01-03", "IsFree": True},
            "2030-01-01T00:00:00": {"Date": "2030-01-01", "IsFree": True, "MinStay": 2},
            "2030-01-02T00:00:00": {"Date": "2030-01-02", "IsFree": True},
        },
        **overrides,
    }


def grid(units: dict[str, Any] | None) -> dict[str, Any]:
    """Create a synthetic grid whose keys differ from upstream UnitId."""
    return {"Message": "", "Facility": {"FacilityId": 10, "Units": units}}


@pytest.mark.anyio
async def test_find_availabilities(provider: ReserveCaliforniaProvider) -> None:
    """POST facility IDs, map DTOs, and exclude the check-out night."""
    requests: list[httpx.Request] = []

    def respond(request: httpx.Request) -> httpx.Response:
        """Serve synthetic provider responses and capture the request contract."""
        requests.append(request)
        data = filters() if request.method == "GET" else grid({"99.1": unit()})
        return httpx.Response(200, json=data)

    provider.async_client = httpx.AsyncClient(transport=httpx.MockTransport(respond))
    results = await provider.find_availabilities(
        "10", start_date=date(2030, 1, 1), end_date=date(2030, 1, 3)
    )
    assert len(results) == 1
    site = results[0]
    assert site.campsite_id == "100"
    assert site.campsite_name == "Test Campsite 100"
    assert site.available_dates == [date(2030, 1, 1), date(2030, 1, 2)]
    assert site.campsite_type == CampsiteType.RV
    assert site.capacity == 0
    assert site.is_electric and site.is_accessible
    assert site.metadata["vehicle_length"] == 30
    assert site.metadata["minimum_stays"]["2030-01-01"] == 2
    assert json.loads(requests[-1].content) == {
        "FacilityId": 10,
        "StartDate": "01-01-2030",
        "EndDate": "01-02-2030",
        "WebOnly": True,
        "InSeasonOnly": True,
        "UnitSort": "orderby",
    }
    assert requests[-1].url.path == "/rdr/search/grid"


@pytest.mark.anyio
@pytest.mark.parametrize(
    "override",
    [
        {"AllowWebBooking": False},
        {"IsWebViewable": False},
        {"IsFiltered": True},
        {"UseType": 1},
        {"UnitId": None},
        {"Slices": {"x": {"Date": "2030-01-01", "IsFree": False}}},
        *[
            {"Slices": {"x": {"Date": "2030-01-01", "IsFree": True, flag: True}}}
            for flag in ("IsBlocked", "IsWalkin", "IsReservationDraw")
        ],
        {
            "Slices": {
                "x": {"Date": "2030-01-01", "IsFree": True, "Lock": {"locked": True}}
            }
        },
        {"Slices": None},
    ],
)
async def test_unbookable_inventory(
    provider: ReserveCaliforniaProvider, override: dict[str, Any]
) -> None:
    """A free flag alone must not trigger alerts for unbookable inventory."""
    provider.async_client = httpx.AsyncClient(
        transport=httpx.MockTransport(
            lambda r: httpx.Response(
                200,
                json=filters() if r.method == "GET" else grid({"x": unit(**override)}),
            )
        )
    )
    assert (
        await provider.find_availabilities(
            "10", start_date=date(2030, 1, 1), end_date=date(2030, 1, 2)
        )
        == []
    )


@pytest.mark.anyio
async def test_http_200_rejection_propagates(
    provider: ReserveCaliforniaProvider,
) -> None:
    """An application error must not erase previously cached availability."""
    response = grid(None)
    response.update(
        Message="Invalid FacilityId specified for facility grid search", NightsActual=0
    )
    provider.async_client = httpx.AsyncClient(
        transport=httpx.MockTransport(
            lambda r: httpx.Response(
                200, json=filters() if r.method == "GET" else response
            )
        )
    )
    with pytest.raises(ValueError, match="Invalid FacilityId"):
        await provider.find_availabilities(
            "10", start_date=date(2030, 1, 1), end_date=date(2030, 1, 2)
        )


@pytest.mark.anyio
async def test_chunking_and_deduplication(provider: ReserveCaliforniaProvider) -> None:
    """Long searches request bounded inclusive grids and merge duplicate units."""
    windows: list[dict[str, Any]] = []

    def respond(request: httpx.Request) -> httpx.Response:
        """Return padded overlapping grids like the real provider does."""
        if request.method == "GET":
            return httpx.Response(200, json=filters())
        windows.append(json.loads(request.content))
        slices = {
            str(d): {"Date": str(d), "IsFree": True}
            for d in [
                date(2030, 1, 1),
                date(2030, 1, 30),
                date(2030, 1, 31),
                date(2030, 2, 2),
            ]
        }
        return httpx.Response(200, json=grid({"x": unit(Slices=slices)}))

    provider.async_client = httpx.AsyncClient(transport=httpx.MockTransport(respond))
    results = await provider.find_availabilities(
        "10", start_date=date(2030, 1, 1), end_date=date(2030, 2, 2)
    )
    assert [(w["StartDate"], w["EndDate"]) for w in windows] == [
        ("01-01-2030", "01-30-2030"),
        ("01-31-2030", "02-01-2030"),
    ]
    assert len(results) == 1
    assert results[0].available_dates == [
        date(2030, 1, 1),
        date(2030, 1, 30),
        date(2030, 1, 31),
    ]


@pytest.mark.anyio
@pytest.mark.parametrize("response", [{"Facility": None}, grid(None), grid({})])
async def test_empty_grids(
    provider: ReserveCaliforniaProvider, response: dict[str, Any]
) -> None:
    """Empty successful inventory responses contain no availability."""
    provider.async_client = httpx.AsyncClient(
        transport=httpx.MockTransport(
            lambda r: httpx.Response(
                200, json=filters() if r.method == "GET" else response
            )
        )
    )
    assert (
        await provider.find_availabilities(
            "10", start_date=date(2030, 1, 1), end_date=date(2030, 1, 2)
        )
        == []
    )


@pytest.mark.anyio
async def test_errors_propagate(provider: ReserveCaliforniaProvider) -> None:
    """HTTP failures must reach the worker instead of clearing cached results."""
    provider.async_client = httpx.AsyncClient(
        transport=httpx.MockTransport(lambda r: httpx.Response(503))
    )
    with pytest.raises(httpx.HTTPStatusError):
        await provider.find_availabilities(
            "10", start_date=date(2030, 1, 1), end_date=date(2030, 1, 2)
        )


@pytest.mark.anyio
async def test_metadata_ingestion_and_provider_isolation(
    provider: ReserveCaliforniaProvider, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Refresh complete catalogs without grids or cross-provider park joins."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")

    maker = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    async with maker() as session:
        session.add(Provider(id=1, name="Other provider", url="https://example.com"))
        await session.flush()
        session.add(RecreationArea(id="1", provider_id=1, name="Other park"))
        await session.commit()

    monkeypatch.setattr(
        "providers.usedirect.provider.db", SimpleNamespace(get_session=maker)
    )
    places = [
        {
            "PlaceId": 1,
            "Name": "TEST PARK",
            "City": "Testville",
            "State": "CA",
            "AllowWebBooking": True,
            "IsWebViewable": True,
        }
    ]
    facilities = [
        {
            "FacilityId": 10,
            "PlaceId": 1,
            "Name": "TEST CAMPGROUND",
            "AllowWebBooking": True,
        },
        {"FacilityId": 11, "PlaceId": 999, "Name": "Orphan"},
        {
            "FacilityId": 12,
            "PlaceId": 1,
            "Name": "Offline campground",
            "AllowWebBooking": False,
        },
    ]

    provider.async_client = httpx.AsyncClient(
        transport=httpx.MockTransport(
            lambda r: httpx.Response(
                200,
                json={
                    ("GET", "/rdr/fd/places"): places,
                    ("GET", "/rdr/fd/facilities"): facilities,
                }[(r.method, r.url.path)],
            )
        )
    )
    try:
        await provider.sync_metadata()
        places[0]["Name"] = "Updated Park"
        await provider.sync_metadata()
        async with maker() as session:
            campgrounds = (await session.scalars(select(Campground))).all()
            rows = (
                await session.scalars(select(Search).where(Search.provider_id == 2))
            ).all()
            assert len(campgrounds) == 2
            active_campground = next(c for c in campgrounds if c.id == "10")
            assert (
                active_campground.recreation_area_id,
                active_campground.name,
                active_campground.state,
            ) == ("1", "Test Campground", "CA")
            assert len(rows) == 2
            assert all(row.recreation_area_name == "Updated Park" for row in rows)
            assert (
                await session.scalar(
                    select(RecreationArea.name).where(
                        RecreationArea.id == "1", RecreationArea.provider_id == 1
                    )
                )
                == "Other park"
            )
        places[0]["Name"] = "Uncommitted park name"
        with monkeypatch.context() as patch:
            patch.setattr(
                provider,
                "populate_search_table",
                AsyncMock(side_effect=RuntimeError("synthetic search failure")),
            )
            with pytest.raises(RuntimeError, match="synthetic search failure"):
                await provider.sync_metadata()
        async with maker() as session:
            assert (
                await session.scalar(
                    select(RecreationArea.name).where(
                        RecreationArea.id == "1", RecreationArea.provider_id == 2
                    )
                )
                == "Updated Park"
            )
        places[0]["Name"] = "Updated Park"
        facilities.clear()
        await provider.sync_metadata()
        async with maker() as session:
            retired = await session.get(Campground, ("10", 2))
            assert retired is not None
            assert retired.enabled is False and retired.reservable is False
            assert not (
                await session.scalars(
                    select(Search).where(
                        Search.provider_id == 2, Search.entity_type == "Campground"
                    )
                )
            ).all()
        places[0]["IsWebViewable"] = False
        await provider.sync_metadata()
        async with maker() as session:
            assert not (
                await session.scalars(select(Search).where(Search.provider_id == 2))
            ).all()
    finally:
        await engine.dispose()


def test_registry_and_booking_links() -> None:
    """Search and notifications use the current park/facility booking routes."""
    assert PROVIDERS[2] is ReserveCaliforniaProvider
    assert (
        ReserveCaliforniaProvider.get_rec_area_url("1")
        == "https://www.reservecalifornia.com/park/1"
    )
    assert (
        ReserveCaliforniaProvider.get_campground_url("10", rec_area_id="1")
        == "https://www.reservecalifornia.com/park/1/10"
    )


@pytest.mark.anyio
async def test_invalid_range(provider: ReserveCaliforniaProvider) -> None:
    """Invalid check-out dates fail before making any HTTP requests."""
    provider.async_client = AsyncMock()
    with pytest.raises(ValueError):
        await provider.find_availabilities(
            "10", start_date=date(2030, 1, 2), end_date=date(2030, 1, 1)
        )
    provider.async_client.request.assert_not_called()


@pytest.mark.parametrize(
    "group_id,equipment_ids,expected_type,electric",
    [
        (2, [2], CampsiteType.TENT, False),
        (3, [2], CampsiteType.RV, True),
        (4, [2], CampsiteType.RV, False),
        (5, [], CampsiteType.CABIN, False),
        (999, [1], CampsiteType.TENT, False),
        (999, [], CampsiteType.OTHER, False),
    ],
)
def test_classification(
    group_id: int, equipment_ids: list[int], expected_type: CampsiteType, electric: bool
) -> None:
    """Map equipment conservatively and distinguish electrical from water hookups."""
    parsed = AvailabilityUnit.model_validate(
        unit(UnitTypeGroupId=group_id, SleepingUnitIds=equipment_ids)
    )
    dto = parsed.to_dto(
        filters=SearchFilters.model_validate(filters()),
        start_date=date(2030, 1, 1),
        end_date=date(2030, 1, 2),
    )
    assert dto is not None
    assert dto.campsite_type == expected_type
    assert dto.is_electric is electric


@pytest.mark.anyio
@pytest.mark.parametrize(
    "facility_flags",
    [
        {"IsReservationDraw": True},
        {"FacilityAllowWebBooking": False},
        {"SeasonDates": {"2030-01-01T00:00:00": False}},
    ],
)
async def test_facility_restrictions(
    provider: ReserveCaliforniaProvider, facility_flags: dict[str, Any]
) -> None:
    """Facility lottery, booking, and season restrictions override free slices."""
    data = grid({"x": unit()})
    data["Facility"].update(facility_flags)
    provider.async_client = httpx.AsyncClient(
        transport=httpx.MockTransport(
            lambda r: httpx.Response(200, json=filters() if r.method == "GET" else data)
        )
    )
    assert (
        await provider.find_availabilities(
            "10", start_date=date(2030, 1, 1), end_date=date(2030, 1, 2)
        )
        == []
    )


@pytest.mark.vcr(
    record_mode="none",
    match_on=["method", "scheme", "host", "port", "path", "query", "body"],
)
@pytest.mark.anyio
async def test_reserve_california_http_replay() -> None:
    """Replay synthetic API responses through the real base retry transport."""
    provider = ReserveCaliforniaProvider()
    try:
        results = await provider.find_availabilities(
            "10", start_date=date(2030, 1, 1), end_date=date(2030, 1, 3)
        )
        assert len(results) == 1
        assert results[0].campsite_id == "100"
        assert results[0].available_dates == [date(2030, 1, 1), date(2030, 1, 2)]
        assert results[0].is_electric
    finally:
        await provider.async_client.aclose()


def test_api_booking_url() -> None:
    """Serialized campground responses include the parent park in booking links."""
    from backend.models.campgrounds import Campground as APICampground

    campground = APICampground(
        id="10",
        provider_id=2,
        recreation_area_id="1",
        name="Synthetic campground",
        description=None,
        country="US",
        state="CA",
        longitude=None,
        latitude=None,
    )
    assert (
        campground.model_dump()["url"] == "https://www.reservecalifornia.com/park/1/10"
    )


def test_population_cli(monkeypatch: pytest.MonkeyPatch) -> None:
    """Select California via the metadata CLI and close clients on failure."""
    from providers.cli import populate_database

    instance = MagicMock()
    instance.populate_database = AsyncMock(
        side_effect=RuntimeError("synthetic failure")
    )
    instance.async_client.aclose = AsyncMock()
    factory = MagicMock(return_value=instance)
    monkeypatch.setitem(PROVIDERS, 2, factory)
    result = CliRunner().invoke(populate_database, ["--provider-id", "2"])
    assert isinstance(result.exception, RuntimeError)
    factory.assert_called_once_with()
    instance.populate_database.assert_awaited_once()
    instance.async_client.aclose.assert_awaited_once()
