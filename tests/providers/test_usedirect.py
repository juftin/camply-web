"""Synthetic regressions for the shared UseDirect provider variations."""

from datetime import date
from types import SimpleNamespace
from typing import Any

import httpx
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from camply.db.models import Base, Campground, Provider, RecreationArea, Search
from camply.providers import PROVIDERS
from camply.providers.dto import CampsiteType
from camply.providers.usedirect.models.api import AvailabilityUnit, SearchFilters
from camply.providers.usedirect.models.metadata import Place
from camply.providers.usedirect.provider import UseDirectProvider


@pytest.fixture
def anyio_backend() -> str:
    """Run the async provider integrations on asyncio."""
    return "asyncio"


def registered_providers() -> list[type[UseDirectProvider]]:
    """Exercise every concrete UseDirect provider, including California."""
    return [cls for cls in PROVIDERS.values() if issubclass(cls, UseDirectProvider)]


def test_usedirect_remains_abstract() -> None:
    """An adapter must declare a persistent provider identity before use."""
    with pytest.raises(TypeError):
        UseDirectProvider()  # type: ignore[abstract]


@pytest.mark.parametrize("state", [None, "", " ", "Florida", "fl", " FL "])
def test_state_normalization(state: str | None) -> None:
    """Full state names and empty strings fall back to the deployment code."""
    from camply.providers.usedirect.variations import FloridaStateParksProvider

    assert (
        FloridaStateParksProvider._metadata_state(
            Place(PlaceId=1, Name="Synthetic park", State=state)
        )
        == "FL"
    )


@pytest.mark.parametrize(
    "provider_id,expected",
    [
        (3, "https://reserve.floridastateparks.org/Web/#!park/1/10"),
        (4, "https://reservevaparks.com/Web/#!park/1/10"),
        (5, "https://reservemn.usedirect.com/MinnesotaWeb/#!park/1/10"),
        (6, "https://reserveohio.com/OhioCampWeb/#!park/1/10"),
        (7, "https://azstateparks.com/reserve/#!park/1/10"),
        (8, "https://icampmo.usedirect.com/MSPWeb/#!park/1/10"),
        (9, "https://fairfax.usedirect.com/FairfaxFCPAWeb"),
        (10, "https://reservemetro.usedirect.com/MetroWeb"),
        (11, "https://parkbookings.nt.gov.au/Web"),
    ],
)
def test_verified_booking_hosts(provider_id: int, expected: str) -> None:
    """Current reservation hosts and search fallbacks stay stable across refactors."""
    assert PROVIDERS[provider_id].get_campground_url("10", rec_area_id="1") == expected


def test_metadata_cli_lists_registered_providers() -> None:
    """Operators can discover all supported metadata provider IDs from help."""
    from click.testing import CliRunner

    from camply.providers.cli import populate_database

    result = CliRunner().invoke(populate_database, ["--help"])
    assert result.exit_code == 0
    assert "3 = FloridaStateParks" in result.output
    assert "11 = NorthernTerritory" in result.output
    assert "--provider-id" in result.output


@pytest.mark.anyio
@pytest.mark.parametrize("provider_cls", registered_providers())
async def test_provider_grid_and_booking_routes(
    provider_cls: type[UseDirectProvider], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Each concrete provider scans its own host and produces its booking route."""
    monkeypatch.setattr("camply.providers.usedirect.provider._REQUEST_INTERVAL", 0)
    provider = provider_cls()
    await provider.async_client.aclose()
    requests: list[httpx.Request] = []

    def respond(request: httpx.Request) -> httpx.Response:
        """Use synthetic API responses; reject requests to another provider."""
        requests.append(request)
        assert str(request.url).startswith(provider.api_url + "/")
        data: dict[str, Any] = {"UnitTypesGroups": [], "NightlySleepingUnits": []}
        if request.method == "POST":
            data = {
                "NightsActual": 2,
                "Facility": {
                    "FacilityId": 10,
                    "Units": {
                        "100.1": {
                            "UnitId": 100,
                            "Name": "Synthetic site",
                            "UseType": 4,
                            "AllowWebBooking": True,
                            "Slices": {
                                "a": {"Date": "2030-01-01", "IsFree": True},
                                "b": {"Date": "2030-01-02", "IsFree": True},
                                "c": {"Date": "2030-01-03", "IsFree": True},
                            },
                        }
                    },
                },
            }
        return httpx.Response(200, json=data)

    provider.async_client = httpx.AsyncClient(transport=httpx.MockTransport(respond))
    try:
        results = await provider.find_availabilities(
            "10", start_date=date(2030, 1, 1), end_date=date(2030, 1, 3)
        )
        assert results[0].available_dates == [date(2030, 1, 1), date(2030, 1, 2)]
        assert results[0].campsite_id == "100"
        assert len(requests) == 2
        url = provider.get_campground_url("10", rec_area_id="1")
        assert url.startswith(provider.booking_url)
        assert provider.get_rec_area_url("1").startswith(provider.booking_url)
        if provider.provider.id == 2:
            assert url.endswith("/park/1/10")
        elif provider.booking_path_params:
            assert url.endswith("#!park/1/10")
        else:
            assert url == provider.booking_url
    finally:
        await provider.async_client.aclose()


@pytest.mark.anyio
@pytest.mark.parametrize("provider_cls", registered_providers())
async def test_provider_error_identity_and_cache_isolation(
    provider_cls: type[UseDirectProvider], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Grid rejections identify their provider and filters stay per instance."""
    monkeypatch.setattr("camply.providers.usedirect.provider._REQUEST_INTERVAL", 0)
    provider = provider_cls()
    other = provider_cls()
    await provider.async_client.aclose()
    provider.async_client = httpx.AsyncClient(
        transport=httpx.MockTransport(
            lambda r: httpx.Response(
                200,
                json={}
                if r.method == "GET"
                else {
                    "NightsActual": 0,
                    "Message": "Invalid facility",
                    "Facility": None,
                },
            )
        )
    )
    try:
        with pytest.raises(ValueError, match=provider.provider.name):
            await provider.find_availabilities(
                "10", start_date=date(2030, 1, 1), end_date=date(2030, 1, 2)
            )
        assert provider._filters is not None
        assert other._filters is None
    finally:
        await provider.async_client.aclose()
        await other.async_client.aclose()


@pytest.mark.anyio
async def test_catalogs_preserve_provider_and_location_defaults(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Identical catalog IDs stay isolated with each deployment's location defaults."""
    monkeypatch.setattr("camply.providers.usedirect.provider._REQUEST_INTERVAL", 0)
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    maker = async_sessionmaker(engine, expire_on_commit=False)
    monkeypatch.setattr(
        "camply.providers.usedirect.provider.db", SimpleNamespace(get_session=maker)
    )
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    try:
        for cls in registered_providers():
            await _sync_synthetic_catalog(cls)
        async with maker() as session:
            parks = (await session.scalars(select(RecreationArea))).all()
            campgrounds = (await session.scalars(select(Campground))).all()
            rows = (await session.scalars(select(Search))).all()
            identities = (await session.scalars(select(Provider))).all()
            assert len(parks) == len(campgrounds) == len(identities) == 10
            assert len(rows) == 20
            assert all(p.enabled and p.reservable for p in parks)
            assert all(c.enabled and c.reservable for c in campgrounds)
            for cls in registered_providers():
                provider = cls()
                try:
                    park = next(
                        p for p in parks if p.provider_id == provider.provider.id
                    )
                    campground = next(
                        c for c in campgrounds if c.provider_id == park.provider_id
                    )
                    assert park.state == campground.state == provider.state_code
                    assert park.country == campground.country == provider.country_code
                    assert park.name == provider.provider.name
                    assert all(
                        r.recreation_area_name == park.name
                        for r in rows
                        if r.provider_id == park.provider_id
                    )
                finally:
                    await provider.async_client.aclose()
    finally:
        await engine.dispose()


async def _sync_synthetic_catalog(cls: type[UseDirectProvider]) -> None:
    """Ingest a complete catalog twice using only metadata GET endpoints."""
    provider = cls()
    await provider.async_client.aclose()
    catalogs = {
        "/fd/places": [
            {
                "PlaceId": 1,
                "Name": provider.provider.name,
                "State": None,
                "AllowWebBooking": True,
            }
        ],
        "/fd/facilities": [
            {
                "FacilityId": 10,
                "PlaceId": 1,
                "Name": "Synthetic campground",
                "AllowWebBooking": True,
            }
        ],
    }

    def respond(request: httpx.Request) -> httpx.Response:
        """Reject availability and classification requests during metadata sync."""
        assert request.method == "GET"
        path = str(request.url).removeprefix(provider.api_url)
        return httpx.Response(200, json=catalogs[path])

    provider.async_client = httpx.AsyncClient(transport=httpx.MockTransport(respond))
    try:
        await provider.sync_metadata()
        await provider.populate_database()
    finally:
        await provider.async_client.aclose()


@pytest.mark.parametrize(
    "group", ["Non-electric", "Non Electric", "No electricity", "Unelectrified"]
)
def test_explicit_non_electric_groups(group: str) -> None:
    """Explicit exclusions override substring matches such as non-electric."""
    unit = AvailabilityUnit.model_validate(
        {
            "UnitId": 100,
            "UseType": 4,
            "AllowWebBooking": True,
            "UnitTypeGroupId": 1,
            "Slices": {"a": {"Date": "2030-01-01", "IsFree": True}},
        }
    )
    filters = SearchFilters.model_validate(
        {"UnitTypesGroups": [{"UnitTypesGroupId": 1, "UnitTypesGroupName": group}]}
    )
    dto = unit.to_dto(
        filters=filters, start_date=date(2030, 1, 1), end_date=date(2030, 1, 2)
    )
    assert dto is not None
    assert dto.is_electric is False
    assert dto.campsite_type == CampsiteType.OTHER
