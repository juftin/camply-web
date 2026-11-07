"""Database-free upstream campground discovery."""

from contextlib import asynccontextmanager
from unittest.mock import patch

import httpx2
import pytest

from camply.db.config import db
from camply.providers import PROVIDERS
from camply.providers.dto import SearchEntityType
from camply.providers.going_to_camp.provider import GoingToCampProvider
from camply.providers.reserve_america.provider import ReserveAmericaProvider
from camply.providers.usedirect.provider import UseDirectProvider


@pytest.mark.asyncio
@pytest.mark.parametrize("provider_cls", PROVIDERS.values())
async def test_invalid_search_does_not_request(provider_cls):
    """All registered providers reject invalid limits before network IO."""
    provider = provider_cls()
    try:
        with pytest.raises(ValueError):
            await provider.search(limit=0)
    finally:
        await provider.async_client.aclose()


def catalog(provider):
    """Supply only upstream metadata, including unbookable/hidden distractions."""
    if isinstance(provider, UseDirectProvider):
        return {
            "fd/places": [
                {"PlaceId": 1, "Name": "Forest Park", "AllowWebBooking": True},
                {
                    "PlaceId": 2,
                    "Name": "Hidden",
                    "AllowWebBooking": True,
                    "IsWebViewable": False,
                },
            ],
            "fd/facilities": [
                {
                    "FacilityId": 10,
                    "PlaceId": 1,
                    "Name": "Pine Camp",
                    "AllowWebBooking": True,
                },
                {
                    "FacilityId": 11,
                    "PlaceId": 2,
                    "Name": "Pine Hidden",
                    "AllowWebBooking": True,
                },
                {
                    "FacilityId": 12,
                    "PlaceId": 1,
                    "Name": "Pine Offline",
                    "AllowWebBooking": False,
                },
                {
                    "FacilityId": 13,
                    "PlaceId": 99,
                    "Name": "Pine Orphan",
                    "AllowWebBooking": True,
                },
            ],
        }
    if isinstance(provider, GoingToCampProvider):
        return {
            "transactionlocation": [
                {
                    "transactionLocationId": -1,
                    "localizedValues": [{"name": "Forest Park"}],
                }
            ],
            "resourceLocation": [
                {
                    "resourceLocationId": 10,
                    "transactionLocationId": -1,
                    "rootMapId": 5,
                    "resourceCategoryIds": [1],
                    "localizedValues": [{"name": "Pine Camp"}],
                },
                {
                    "resourceLocationId": 11,
                    "transactionLocationId": -1,
                    "rootMapId": 5,
                    "resourceCategoryIds": [2],
                    "localizedValues": [{"name": "Day Use"}],
                },
            ],
            "bookingcategories": [
                {
                    "bookingCategoryId": 0,
                    "bookingModel": 0,
                    "allowedResourceCategoryIds": [1],
                }
            ],
            "resourcecategory": [{"resourceCategoryId": 1, "resourceType": 0}],
        }
    if isinstance(provider, ReserveAmericaProvider):
        return {
            "config/brand": {"states": [{"stateCode": "CO", "countryCode": "USA"}]},
            "search": {
                "control": {"currentPage": 0, "pageSize": 50},
                "totalRecords": 2,
                "totalPages": 1,
                "records": [
                    {
                        "name": "Pine Camp",
                        "details": {
                            "id": 10,
                            "contrCode": "CO",
                            "stateCodes": ["CO"],
                            "verifiableAvailability": True,
                            "nonClientFacility": False,
                            "dayUseOnly": False,
                            "facilityTypes": ["camping"],
                        },
                    },
                    {
                        "name": "Pine Day Use",
                        "details": {
                            "id": 11,
                            "contrCode": "CO",
                            "stateCodes": ["CO"],
                            "verifiableAvailability": True,
                            "nonClientFacility": False,
                            "dayUseOnly": True,
                            "facilityTypes": ["camping"],
                        },
                    },
                ],
            },
        }
    return {
        "api/search": {
            "start": "0",
            "total": 2,
            "results": [
                {
                    "entity_id": "10",
                    "entity_type": "campground",
                    "name": "Pine Camp",
                    "reservable": True,
                    "parent_id": "1",
                    "state_code": "California",
                    "addresses": [{"state_code": "CA"}],
                },
                {
                    "entity_id": "11",
                    "entity_type": "campground",
                    "name": "Pine Offline",
                    "reservable": False,
                },
            ],
        }
    }


@asynccontextmanager
async def upstream(provider_cls, monkeypatch, handler=None):
    """Real HTTP clients with synthetic responses; any DB access fails the test."""
    for family in ("usedirect", "going_to_camp", "reserve_america"):
        monkeypatch.setattr(f"camply.providers.{family}.provider._REQUEST_INTERVAL", 0)
    provider = provider_cls()
    await provider.async_client.aclose()
    requests = []
    data = catalog(provider)

    def respond(request):
        requests.append(request)
        if handler:
            return handler(request)
        if (
            isinstance(provider, ReserveAmericaProvider)
            and "jaxrs-json" not in request.url.path
        ):
            return httpx2.Response(200)
        key = next(key for key in data if request.url.path.endswith("/" + key))
        return httpx2.Response(200, json=data[key])

    provider.async_client = httpx2.AsyncClient(transport=httpx2.MockTransport(respond))
    try:
        with patch.object(
            type(db), "get_session", side_effect=AssertionError("Search accessed DB")
        ):
            yield provider, requests
    finally:
        await provider.async_client.aclose()


@pytest.mark.asyncio
@pytest.mark.parametrize("provider_cls", PROVIDERS.values())
async def test_each_provider_searches_upstream(provider_cls, monkeypatch):
    """Regional variants inherit search, eligibility, identity and booking URLs."""
    async with upstream(provider_cls, monkeypatch) as (provider, requests):
        results = await provider.search("  pInE  ")
        assert len(results) == 1
        result = results[0]
        assert result.campground_name == "Pine Camp"
        assert result.provider_id == provider.provider.id
        assert result.campground_id == (
            "CO_10" if isinstance(provider, ReserveAmericaProvider) else "10"
        )
        assert result.booking_url.startswith("https://")
        assert requests
        # A second search fetches again rather than relying on ingested metadata.
        count = len(requests)
        assert await provider.search("", state=" zz ") == []
        assert len(requests) > count


@pytest.mark.asyncio
@pytest.mark.parametrize("provider_cls", PROVIDERS.values())
@pytest.mark.parametrize(
    "kwargs", [{"state": "California"}, {"limit": -1}, {"limit": 1001}, {"limit": True}]
)
async def test_invalid_arguments(provider_cls, kwargs, monkeypatch):
    """Invalid arguments fail without contacting the upstream API."""
    async with upstream(provider_cls, monkeypatch) as (provider, requests):
        with pytest.raises(ValueError):
            await provider.search(**kwargs)
        assert not requests


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "provider_cls", [PROVIDERS[1], PROVIDERS[2], PROVIDERS[12], PROVIDERS[13]]
)
@pytest.mark.parametrize("status,body", [(503, {}), (200, {"error": "unavailable"})])
async def test_upstream_failures_propagate(provider_cls, status, body, monkeypatch):
    """HTTP and malformed responses cannot masquerade as an empty search."""
    async with upstream(
        provider_cls, monkeypatch, lambda _: httpx2.Response(status, json=body)
    ) as (provider, _):
        with pytest.raises((httpx2.HTTPStatusError, ValueError)):
            await provider.search()


@pytest.mark.asyncio
async def test_recreation_gov_pagination_and_state(monkeypatch):
    """Skip ineligible pages and use address codes instead of full state names."""

    def respond(request):
        start = int(request.url.params["start"])
        return httpx2.Response(
            200,
            json={
                "start": start,
                "total": 2,
                "results": [
                    {
                        "entity_id": str(start),
                        "entity_type": "campground",
                        "name": "Camp",
                        "reservable": bool(start),
                        "state_code": "California",
                        "addresses": [{"state_code": "CA"}],
                        "parent_id": "1",
                    }
                ],
            },
        )

    async with upstream(PROVIDERS[1], monkeypatch, respond) as (provider, requests):
        result = await provider.search(state=" ca ", recreation_area_id="1", limit=1)
        assert [r.campground_id for r in result] == ["1"]
        assert [r.url.params["start"] for r in requests] == ["0", "1"]
        assert result[0].state == "CA"


@pytest.mark.asyncio
async def test_recreation_gov_no_progress(monkeypatch):
    """Reject truncated pagination rather than publishing partial search results."""
    async with upstream(
        PROVIDERS[1],
        monkeypatch,
        lambda _: httpx2.Response(200, json={"start": 0, "total": 2, "results": []}),
    ) as (provider, _):
        with pytest.raises(ValueError, match="no progress"):
            await provider.search()


@pytest.mark.asyncio
@pytest.mark.parametrize("provider_cls", PROVIDERS.values())
async def test_exact_parent_filter(provider_cls, monkeypatch):
    """Parent IDs scope results without matching IDs embedded in other strings."""
    async with upstream(provider_cls, monkeypatch) as (provider, _):
        assert await provider.search(recreation_area_id="999") == []
        if not isinstance(provider, ReserveAmericaProvider):
            parent = "-1" if isinstance(provider, GoingToCampProvider) else "1"
            result = await provider.search(
                recreation_area_id=parent, entity_type="campground"
            )
            assert len(result) == 1
            assert result[0].recreation_area_id == parent


@pytest.mark.asyncio
async def test_reserve_america_pagination(monkeypatch):
    """Search follows every state page and deduplicates native facility IDs."""

    def respond(request):
        if "jaxrs-json" not in request.url.path:
            return httpx2.Response(200)
        page = int(request.url.params["rcp"])
        return httpx2.Response(
            200,
            json={
                "totalRecords": 2,
                "totalPages": 2,
                "control": {"currentPage": page, "pageSize": 1},
                "records": [
                    {
                        "name": "Pine Camp",
                        "details": {
                            "id": 10 + page,
                            "contrCode": "CO",
                            "stateCodes": ["CO"],
                            "verifiableAvailability": True,
                            "nonClientFacility": False,
                            "dayUseOnly": False,
                            "facilityTypes": ["camping"],
                        },
                    }
                ],
            },
        )

    async with upstream(PROVIDERS[13], monkeypatch, respond) as (provider, requests):
        result = await provider.search(state=" co ", limit=1)
        assert len(result) == 1
        assert result[0].campground_id == "CO_10"
        assert [r.url.params["rcp"] for r in requests if "rcp" in r.url.params] == [
            "0",
            "1",
        ]


@pytest.mark.asyncio
@pytest.mark.parametrize("provider_cls", PROVIDERS.values())
@pytest.mark.parametrize(
    "entity_type", [None, "campground", "recreation_area", *SearchEntityType]
)
async def test_entity_type_selection(provider_cls, entity_type, monkeypatch):
    """Callers can request either native entity type or both."""
    from camply.providers.dto import CampgroundSearchResult, RecreationAreaSearchResult

    async with upstream(provider_cls, monkeypatch) as (provider, requests):
        if isinstance(
            provider, (UseDirectProvider, GoingToCampProvider, ReserveAmericaProvider)
        ):
            results = await provider.search(entity_type=entity_type)
        else:
            # Add a real recreation area with the same native ID as a campground.
            # Identity must include entity type to avoid losing either result.
            original = catalog(provider)["api/search"]
            original["results"].append(
                {
                    "entity_id": "10",
                    "entity_type": "recarea",
                    "name": "Forest Park",
                    "reservable": True,
                    "addresses": [{"state_code": "CA"}],
                }
            )
            original["total"] = 3
            provider.async_client = await replace_client(provider, original)
            results = await provider.search(entity_type=entity_type)
        if entity_type == "recreation_area" and isinstance(
            provider, (UseDirectProvider, GoingToCampProvider)
        ):
            assert len(requests) == 1
        expected = (
            {"campground", "recreation_area"} if entity_type is None else {entity_type}
        )
        if isinstance(provider, ReserveAmericaProvider):
            expected.discard("recreation_area")
        assert {r.entity_type for r in results} == expected
        for result in results:
            if result.entity_type == "recreation_area":
                assert isinstance(result, RecreationAreaSearchResult)
                assert result.recreation_area_id is not None
                assert result.campground_id is None
                assert result.booking_url == provider.get_rec_area_url(
                    result.recreation_area_id
                )
            else:
                assert isinstance(result, CampgroundSearchResult)
                assert result.campground_id is not None
        if (
            isinstance(provider, ReserveAmericaProvider)
            and entity_type == "recreation_area"
        ):
            assert not requests


async def replace_client(provider, payload):
    """Replace the mock transport for mixed-entity endpoint coverage."""
    await provider.async_client.aclose()
    return httpx2.AsyncClient(
        transport=httpx2.MockTransport(lambda _: httpx2.Response(200, json=payload))
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "state_name,state_code", [("California", "CA"), ("District of Columbia", "DC")]
)
async def test_recreation_area_state_name_and_upstream_filter(
    monkeypatch, state_name, state_code
):
    """Area records lack addresses; full state names must still match codes."""

    def respond(request):
        assert request.url.params["fq"] == "entity_type:recarea"
        return httpx2.Response(
            200,
            json={
                "start": 0,
                "total": 2,
                "results": [
                    {
                        "entity_id": "1",
                        "entity_type": "recarea",
                        "name": "Forest Park",
                        "state_code": state_name,
                    },
                    {"entity_id": "2", "entity_type": "tour", "name": "Forest Tour"},
                ],
            },
        )

    async with upstream(PROVIDERS[1], monkeypatch, respond) as (provider, _):
        results = await provider.search(entity_type="recreation_area", state=state_code)
        assert len(results) == 1
        assert results[0].recreation_area_id == "1"
        assert results[0].state == state_code


@pytest.mark.asyncio
@pytest.mark.parametrize("provider_cls", [PROVIDERS[2], PROVIDERS[12]])
async def test_recreation_areas_are_searchable_without_bookable_campgrounds(
    provider_cls, monkeypatch
):
    """Visible park discovery does not require a campground availability target."""
    provider = provider_cls()
    data = catalog(provider)
    await provider.async_client.aclose()
    if isinstance(provider, UseDirectProvider):
        data["fd/places"][0]["AllowWebBooking"] = False
        data["fd/facilities"] = []
    else:
        data["resourceLocation"] = []
        data["transactionlocation"].append(
            {
                "transactionLocationId": -2,
                "isDisabled": True,
                "localizedValues": [{"name": "Hidden Park"}],
            }
        )

    def respond(request):
        key = next(key for key in data if request.url.path.endswith("/" + key))
        return httpx2.Response(200, json=data[key])

    async with upstream(provider_cls, monkeypatch, respond) as (provider, _):
        results = await provider.search(entity_type="recreation_area")
        assert [r.recreation_area_name for r in results] == ["Forest Park"]
        assert await provider.search(entity_type="campground") == []


@pytest.mark.asyncio
@pytest.mark.parametrize("entity_type", ["parks", "both"])
async def test_invalid_entity_type_does_not_request(monkeypatch, entity_type):
    """Misspelled entity selectors fail validation before making a request."""
    async with upstream(PROVIDERS[2], monkeypatch) as (provider, requests):
        with pytest.raises(ValueError):
            await provider.search(entity_type=entity_type)
        assert not requests


@pytest.mark.asyncio
async def test_entity_type_defaults_to_none(monkeypatch):
    """Omitted and explicit None selectors discover both entity types."""
    from camply.providers.dto import ProviderSearchQuery

    assert ProviderSearchQuery().entity_type is None
    async with upstream(PROVIDERS[2], monkeypatch) as (provider, _):
        default = await provider.search()
        explicit = await provider.search(entity_type=None)
        assert default == explicit
        assert {r.entity_type for r in default} == set(SearchEntityType)
        assert all(isinstance(r.entity_type, SearchEntityType) for r in default)
        assert default[0].model_dump(mode="json")["entity_type"] in {
            "campground",
            "recreation_area",
        }


@pytest.mark.asyncio
async def test_recreation_gov_parent_filter_is_sent_upstream(monkeypatch):
    """Scoped campground discovery must not walk the entire national catalog."""

    def respond(request):
        assert request.url.params.get_list("fq") == [
            "entity_type:campground",
            "parent_asset_id:2991",
        ]
        return httpx2.Response(
            200,
            json={
                "start": 0,
                "total": 2,
                "results": [
                    {
                        "entity_id": "10",
                        "entity_type": "campground",
                        "name": "Pine Camp",
                        "reservable": True,
                        "parent_id": "2991",
                    },
                    {
                        "entity_id": "11",
                        "entity_type": "campground",
                        "name": "Other Camp",
                        "reservable": True,
                        "parent_id": "1000",
                    },
                ],
            },
        )

    async with upstream(PROVIDERS[1], monkeypatch, respond) as (provider, requests):
        results = await provider.search(
            recreation_area_id="2991", entity_type="campground"
        )
        assert [result.campground_id for result in results] == ["10"]
        assert len(requests) == 1
