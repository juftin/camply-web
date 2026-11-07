"""ReserveAmerica integration regressions with synthetic public API responses."""

import asyncio
from collections.abc import AsyncGenerator
from datetime import date, timedelta
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock
from urllib.parse import urlsplit

import httpx2
import pytest
import pytest_asyncio
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from camply.db.models import Base, Campground, Provider, Search
from camply.providers import PROVIDERS
from camply.providers.dto import CampsiteType
from camply.providers.reserve_america.models.api import Site
from camply.providers.reserve_america.provider import ReserveAmericaProvider


def test_registered() -> None:
    """Expose ReserveAmerica to CLI, ingestion, and worker registry consumers."""
    assert PROVIDERS[13] is ReserveAmericaProvider


@pytest_asyncio.fixture
async def provider(
    monkeypatch: pytest.MonkeyPatch,
) -> AsyncGenerator[ReserveAmericaProvider, None]:
    """Disable pacing and close all test clients."""
    monkeypatch.setattr(
        "camply.providers.reserve_america.provider._REQUEST_INTERVAL", 0
    )
    instance = ReserveAmericaProvider()
    await instance.async_client.aclose()
    yield instance
    await instance.async_client.aclose()


def site(**overrides: Any) -> dict[str, Any]:
    """Synthetic version of the verified public product schema."""
    return {
        "id": 42,
        "name": "Site 42",
        "prodGrpName": "Electric",
        "prodInfo": {"lineOfBusiness": "CAMPING", "typeOfUse": "NIGHTLY"},
        "reservableType": "WEB_AVAILABLE",
        "details": {
            "stayType": "NIGHTLY",
            "siteIcon": "type_rv_elec",
            "attributes": [
                {"id": 12, "name": "Maximum Number of People", "value": ["6"]},
                {"id": 104, "name": "ADA Accessible", "value": ["Y"]},
                {"id": 218, "name": "Electricity Hookup", "value": ["30"]},
            ],
        },
        "availabilityGrid": [{"date": "2030-01-01", "status": "AVAILABLE"}],
        **overrides,
    }


def facility(key: int = 1, **overrides: Any) -> dict[str, Any]:
    """Synthetic searchable native overnight facility."""
    return {
        "name": "Example Park",
        "details": {
            "id": key,
            "contrCode": "CO",
            "stateCodes": ["CO"],
            "verifiableAvailability": True,
            "nonClientFacility": False,
            "dayUseOnly": False,
            "facilityTypes": ["camping"],
            **overrides,
        },
    }


def page(
    records: list[Any], current: int = 0, total_pages: int = 1, total: int | None = None
) -> dict[str, Any]:
    """Respect the server's page size, independent of the requested size."""
    return {
        "records": records,
        "control": {"currentPage": current, "pageSize": 1},
        "totalPages": total_pages,
        "totalRecords": len(records) if total is None else total,
    }


def install_http(provider: ReserveAmericaProvider, handler: Any) -> None:
    """Exercise real async request construction and cookie handling."""
    provider.async_client = httpx2.AsyncClient(transport=httpx2.MockTransport(handler))


@pytest.mark.asyncio
async def test_windows_pagination_and_exact_status(
    provider: ReserveAmericaProvider,
) -> None:
    """Merge dates across pages/windows and exclude day use and unknown statuses."""
    requests = []

    def handler(req: httpx2.Request) -> httpx2.Response:
        requests.append(req)
        if req.url.path == "/explore/search-results":
            return httpx2.Response(200)
        assert req.url.path == "/jaxrs-json/products/CO/1"
        assert req.url.params["gal"] == "14"
        start = date.fromisoformat(req.url.params["gad"])
        number = int(req.url.params["rcp"])
        if number:
            raw = site(id=43, details={"stayType": "DAILY"})
        else:
            raw = site(
                availabilityGrid=[
                    {"date": (start + timedelta(days=i)).isoformat(), "status": status}
                    for i, status in [
                        (-1, "AVAILABLE"),
                        (0, "AVAILABLE"),
                        (1, "RESERVED"),
                        (2, "UNKNOWN"),
                        (14, "AVAILABLE"),
                    ]
                ]
            )
        return httpx2.Response(200, json=page([raw], number, 2, 2))

    install_http(provider, handler)
    results = await provider.find_availabilities(
        "CO_1", date(2030, 1, 1), date(2030, 1, 16)
    )
    assert len(results) == 1
    dto = results[0]
    assert dto.campsite_id == "CO_1_42"
    assert dto.available_dates == [date(2030, 1, 1), date(2030, 1, 15)]
    assert dto.capacity == 6 and dto.is_electric and dto.is_accessible
    assert dto.campsite_type == CampsiteType.RV
    assert "contractCode=CO" in dto.metadata["booking_url"]
    assert urlsplit(dto.metadata["booking_url"]).hostname == "www.reserveamerica.com"
    assert all(req.url.host == "a1.reserveamerica.com" for req in requests)
    assert len(requests) == 5


@pytest.mark.asyncio
async def test_auth_refresh(provider: ReserveAmericaProvider) -> None:
    """Expired anonymous tokens refresh once and are URL decoded for A1Data."""
    boots = 0
    calls = 0

    def handler(req: httpx2.Request) -> httpx2.Response:
        nonlocal boots, calls
        if req.url.path == "/explore/search-results":
            boots += 1
            return httpx2.Response(
                200,
                headers=[
                    ("set-cookie", f"idToken=synthetic-{boots}; Path=/"),
                    ("set-cookie", "a1Data=test%20data; Path=/"),
                ],
            )
        calls += 1
        assert req.headers["Authorization"] == f"synthetic-{boots}"
        assert req.headers["A1Data"] == "test data"
        return httpx2.Response(401 if calls == 1 else 200, json=page([]))

    install_http(provider, handler)
    assert (
        await provider.find_availabilities("CO_1", date(2030, 1, 1), date(2030, 1, 2))
        == []
    )
    assert boots == 2 and calls == 2


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "payload",
    [{"code": "ERROR"}, page([], 0, 2, 2), page([site()], 1), page([site()], total=2)],
)
async def test_broken_responses_raise(
    provider: ReserveAmericaProvider, payload: Any
) -> None:
    """Schema/pagination failures must not clear worker cached availability."""
    install_http(provider, lambda req: httpx2.Response(200, json=payload))
    with pytest.raises((ValueError, ValidationError)):
        await provider.find_availabilities("CO_1", date(2030, 1, 1), date(2030, 1, 2))


@pytest.mark.asyncio
@pytest.mark.parametrize("status", [401, 403, 500])
async def test_http_failures_raise(
    provider: ReserveAmericaProvider, status: int
) -> None:
    """Authentication and upstream failures propagate to the shared poller."""
    install_http(
        provider,
        lambda req: httpx2.Response(
            200 if req.url.path == "/explore/search-results" else status
        ),
    )
    with pytest.raises(httpx2.HTTPStatusError):
        await provider.find_availabilities("CO_1", date(2030, 1, 1), date(2030, 1, 2))


@pytest.mark.parametrize(
    "change",
    [
        {"prodInfo": {"lineOfBusiness": "TOURS", "typeOfUse": "NIGHTLY"}},
        {"details": {"stayType": "DAILY"}},
    ],
)
def test_ineligible_products(change: dict[str, Any]) -> None:
    """Day-use inventory and tours are never camping alerts."""
    assert not Site.model_validate(site(**change)).eligible


def test_attributes_and_id_validation() -> None:
    """Non-electric and false accessibility values remain false; IDs are scoped."""
    raw = site()
    raw["details"]["attributes"] = [
        {"id": 218, "name": "Electric", "value": ["0"]},
        {"id": 104, "name": "ADA", "value": ["N"]},
    ]
    dto = Site.model_validate(raw).to_dto("CO_1", set(), "https://example.com")
    assert not dto.is_electric and not dto.is_accessible and dto.capacity == 0
    assert "contractCode=CO&parkId=1" in ReserveAmericaProvider.get_campground_url(
        "CO_1"
    )
    with pytest.raises(ValueError):
        ReserveAmericaProvider.get_campground_url("1/../../evil")


@pytest.mark.asyncio
async def test_catalog_atomic_refresh(
    provider: ReserveAmericaProvider, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Paginate, filter native overnight inventory, retain stale references, isolate providers."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    monkeypatch.setattr(
        "camply.providers.reserve_america.provider.db",
        SimpleNamespace(get_session=sessions),
    )
    records = [
        facility(),
        facility(2, nonClientFacility=True),
        facility(3, dayUseOnly=True),
        facility(4, verifiableAvailability=False),
    ]

    def handler(req: httpx2.Request) -> httpx2.Response:
        if req.url.path == "/explore/search-results":
            return httpx2.Response(200)
        if req.url.path == "/jaxrs-json/config/brand":
            return httpx2.Response(
                200,
                json={
                    "states": [
                        {"stateCode": "CO", "countryCode": "USA"},
                        {"stateCode": "ON", "countryCode": "CAN"},
                    ]
                },
            )
        assert req.url.params["tstc"] == "CO"
        idx = int(req.url.params["rcp"])
        return httpx2.Response(
            200, json=page([records[idx]], idx, len(records), len(records))
        )

    install_http(provider, handler)
    async with sessions.begin() as session:
        session.add_all(
            [
                Provider(id=13, name="ReserveAmerica", url="https://example.com"),
                Provider(id=1, name="Other", url="https://example.com"),
            ]
        )
        await session.flush()
        session.add_all(
            [
                Campground(id="CO_old", provider_id=13, name="Old"),
                Campground(id="CO_1", provider_id=1, name="Other"),
            ]
        )
    await provider.sync_metadata()
    await provider.sync_metadata()
    async with sessions() as session:
        rows = (
            await session.scalars(select(Search).where(Search.provider_id == 13))
        ).all()
        assert len(rows) == 1 and rows[0].campground_id == "CO_1"
        stale = await session.get(Campground, ("CO_old", 13))
        assert stale is not None and not stale.enabled
        other = await session.get(Campground, ("CO_1", 1))
        assert other is not None and other.enabled
    original = provider.populate_search_table
    monkeypatch.setattr(
        provider,
        "populate_search_table",
        AsyncMock(side_effect=RuntimeError("index failed")),
    )
    records[0] = facility(9)
    with pytest.raises(RuntimeError, match="index failed"):
        await provider.populate_database()
    async with sessions() as session:
        assert await session.get(Campground, ("CO_9", 13)) is None
        old = await session.get(Campground, ("CO_1", 13))
        assert old is not None and old.enabled
    monkeypatch.setattr(provider, "populate_search_table", original)
    records[:] = [facility(2, nonClientFacility=True)]
    with pytest.raises(ValueError, match="no native"):
        await provider.populate_database()
    await engine.dispose()


@pytest.mark.parametrize(
    "value,expected",
    [
        ("0", False),
        ("No electric", False),
        ("N/A", False),
        ("30", True),
        ("50 amps", True),
        ("Y", True),
    ],
)
def test_explicit_electricity(value: str, expected: bool) -> None:
    """Unknown or negative hookup values must not match the electric-only filter."""
    raw = site()
    raw["details"]["attributes"] = [
        {"id": 218, "name": "Electricity Hookup", "value": [value]}
    ]
    assert (
        Site.model_validate(raw)
        .to_dto("CO_1", set(), "https://example.com")
        .is_electric
        is expected
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "snapshot", [None, "NOT_AVAILABLE", "CALL_CENTER", "FIELD_AVAILABLE"]
)
@pytest.mark.parametrize("call_center", [False, True])
async def test_daily_grid_independent_of_selected_stay(
    provider: ReserveAmericaProvider, snapshot: str | None, call_center: bool
) -> None:
    """A selected-stay snapshot must not hide later nightly grid openings."""

    def handler(req: httpx2.Request) -> httpx2.Response:
        if req.url.path == "/explore/search-results":
            return httpx2.Response(200)
        return httpx2.Response(
            200,
            json=page(
                [
                    site(
                        reservableType=snapshot,
                        details={
                            "stayType": "NIGHTLY",
                            "callCenterReservable": call_center,
                        },
                        availabilityGrid=[
                            {"date": "2030-01-01", "status": "RESERVED"},
                            {"date": "2030-01-02", "status": "AVAILABLE"},
                            {"date": "2030-01-03", "status": "WALK_UP"},
                            {"date": "2030-01-04", "status": "CALL_CENTER"},
                        ],
                    )
                ]
            ),
        )

    install_http(provider, handler)
    results = await provider.find_availabilities(
        "CO_1", date(2030, 1, 1), date(2030, 1, 5)
    )
    assert len(results) == 1
    assert results[0].available_dates == [date(2030, 1, 2)]


@pytest.mark.asyncio
async def test_auth_headers_follow_cookie_rotation(
    provider: ReserveAmericaProvider,
) -> None:
    """Use rotated cookies, and stop forwarding tokens deleted by API responses."""
    calls = 0

    def handler(req: httpx2.Request) -> httpx2.Response:
        nonlocal calls
        if req.url.path == "/explore/search-results":
            return httpx2.Response(
                200,
                headers=[
                    ("set-cookie", "idToken=initial; Path=/"),
                    ("set-cookie", "a1Data=initial%20data; Path=/"),
                ],
            )
        calls += 1
        if calls == 1:
            assert req.headers["Authorization"] == "initial"
            return httpx2.Response(
                200,
                json=page([]),
                headers=[
                    ("set-cookie", "idToken=rotated; Path=/"),
                    ("set-cookie", "a1Data=rotated%20data; Path=/"),
                ],
            )
        if calls == 2:
            assert req.headers["Authorization"] == "rotated"
            assert req.headers["A1Data"] == "rotated data"
            return httpx2.Response(
                200,
                json=page([]),
                headers=[
                    ("set-cookie", "idToken=; Max-Age=0; Path=/"),
                    ("set-cookie", "a1Data=; Max-Age=0; Path=/"),
                ],
            )
        assert "Authorization" not in req.headers and "A1Data" not in req.headers
        return httpx2.Response(200, json=page([]))

    install_http(provider, handler)
    for _ in range(3):
        await provider.find_availabilities("CO_1", date(2030, 1, 1), date(2030, 1, 2))
    assert calls == 3


@pytest.mark.asyncio
async def test_failed_auth_refresh_invalidates_session(
    provider: ReserveAmericaProvider,
) -> None:
    """After two 401s, the next operation starts by obtaining a fresh session."""
    events: list[str] = []
    boots = 0

    def handler(req: httpx2.Request) -> httpx2.Response:
        nonlocal boots
        if req.url.path == "/explore/search-results":
            events.append("bootstrap")
            boots += 1
            return httpx2.Response(200)
        events.append("api")
        return (
            httpx2.Response(200, json=page([])) if boots == 3 else httpx2.Response(401)
        )

    install_http(provider, handler)
    with pytest.raises(httpx2.HTTPStatusError):
        await provider.find_availabilities("CO_1", date(2030, 1, 1), date(2030, 1, 2))
    assert events == ["bootstrap", "api", "bootstrap", "api"]
    assert (
        await provider.find_availabilities("CO_1", date(2030, 1, 1), date(2030, 1, 2))
        == []
    )
    assert events == ["bootstrap", "api", "bootstrap", "api", "bootstrap", "api"]


@pytest.mark.asyncio
async def test_auth_headers_respect_cookie_path(
    provider: ReserveAmericaProvider,
) -> None:
    """Cookies for unrelated paths must not be mirrored into API auth headers."""

    def handler(req: httpx2.Request) -> httpx2.Response:
        if req.url.path == "/explore/search-results":
            return httpx2.Response(
                200,
                headers=[
                    ("set-cookie", "idToken=private; Path=/private"),
                    ("set-cookie", "a1Data=private; Path=/private"),
                ],
            )
        assert "Authorization" not in req.headers and "A1Data" not in req.headers
        return httpx2.Response(200, json=page([]))

    install_http(provider, handler)
    assert (
        await provider.find_availabilities("CO_1", date(2030, 1, 1), date(2030, 1, 2))
        == []
    )


@pytest.mark.asyncio
async def test_expired_cookies_are_not_mirrored(
    provider: ReserveAmericaProvider,
) -> None:
    """Do not keep forwarding a token header after its cookie expires locally."""
    calls = 0

    def handler(req: httpx2.Request) -> httpx2.Response:
        nonlocal calls
        if req.url.path == "/explore/search-results":
            return httpx2.Response(
                200,
                headers=[
                    ("set-cookie", "idToken=initial; Max-Age=3600; Path=/"),
                    ("set-cookie", "a1Data=initial; Max-Age=3600; Path=/"),
                ],
            )
        calls += 1
        if calls == 1:
            assert req.headers["Authorization"] == "initial"
        else:
            assert "Authorization" not in req.headers and "A1Data" not in req.headers
        return httpx2.Response(200, json=page([]))

    install_http(provider, handler)
    await provider.find_availabilities("CO_1", date(2030, 1, 1), date(2030, 1, 2))
    for cookie in provider.async_client.cookies.jar:
        cookie.expires = 1
    await provider.find_availabilities("CO_1", date(2030, 1, 1), date(2030, 1, 2))
    assert calls == 2


@pytest.mark.asyncio
async def test_concurrent_requests_share_session_refresh(
    provider: ReserveAmericaProvider,
) -> None:
    """Concurrent callers wait for one refresh rather than replacing each other's cookies."""
    boots = 0
    calls = 0

    async def handler(req: httpx2.Request) -> httpx2.Response:
        nonlocal boots, calls
        await asyncio.sleep(0)
        if req.url.path == "/explore/search-results":
            boots += 1
            return httpx2.Response(
                200, headers={"set-cookie": f"idToken=session-{boots}; Path=/"}
            )
        calls += 1
        if req.headers["Authorization"] == "session-1":
            return httpx2.Response(401)
        assert req.headers["Authorization"] == "session-2"
        return httpx2.Response(200, json=page([]))

    install_http(provider, handler)
    results = await asyncio.gather(
        *[
            provider.find_availabilities("CO_1", date(2030, 1, 1), date(2030, 1, 2))
            for _ in range(5)
        ]
    )
    assert results == [[], [], [], [], []]
    assert boots == 2 and calls == 6


@pytest.mark.asyncio
async def test_auth_headers_prefer_more_specific_cookie(
    provider: ReserveAmericaProvider,
) -> None:
    """An API-path token rotation must override an older root cookie of the same name."""
    calls = 0

    def handler(req: httpx2.Request) -> httpx2.Response:
        nonlocal calls
        if req.url.path == "/explore/search-results":
            return httpx2.Response(
                200, headers={"set-cookie": "idToken=root-token; Path=/"}
            )
        calls += 1
        if calls == 1:
            return httpx2.Response(
                200,
                json=page([]),
                headers={"set-cookie": "idToken=api-token; Path=/jaxrs-json"},
            )
        assert req.headers["Authorization"] == "api-token"
        return httpx2.Response(200, json=page([]))

    install_http(provider, handler)
    for _ in range(2):
        await provider.find_availabilities("CO_1", date(2030, 1, 1), date(2030, 1, 2))
    assert calls == 2


def test_public_provider_urls_use_canonical_website() -> None:
    """Public provider links must not send campers to the API/session host."""
    from camply.db.data.providers import ReserveAmerica

    assert ReserveAmerica.url == "https://www.reserveamerica.com"
    assert (
        urlsplit(ReserveAmericaProvider.get_campground_url("CO_1")).hostname
        == "www.reserveamerica.com"
    )
    assert (
        urlsplit(ReserveAmericaProvider.get_rec_area_url("CO_1")).hostname
        == "www.reserveamerica.com"
    )
