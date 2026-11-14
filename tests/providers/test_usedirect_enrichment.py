"""Synthetic destination enrichment checks across UseDirect deployments."""

from collections.abc import AsyncGenerator, AsyncIterator
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock

import httpx2
import pytest
import pytest_asyncio
from sqlalchemy import update
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from camply.db.models import Base, Provider, RecreationArea
from camply.providers import PROVIDERS
from camply.providers.details import DestinationDetails, DestinationPhoto
from camply.providers.enrichment import Destination
from camply.providers.usedirect.enrichment import fetch_details
from camply.providers.usedirect.provider import UseDirectProvider


def park_information(**changes: Any) -> dict[str, Any]:
    """Return a complete synthetic response from the park-information route."""
    return {
        "PlaceId": 1,
        "Website": "https://parks.example.org/synthetic",
        "ParkHeadquartersHours": "Weekdays 9-5",
        "DayUseParkHours": "Sunrise to sunset",
        "BackCountyTrailCampOfficeHours": None,
        "NatureMuseum": "Not Available",
        "TrailerMaxLength": "0",
        "CamperMotorHomeMaxLength": "35",
        "DisplayMaxTrailerLengthOnWeb": True,
        **changes,
    }


@pytest_asyncio.fixture
async def provider() -> AsyncGenerator[UseDirectProvider, None]:
    """Supply a closed-on-exit concrete provider with synthetic API calls."""
    instance = PROVIDERS[3]()
    assert isinstance(instance, UseDirectProvider)
    await instance.async_client.aclose()
    yield instance
    await instance.async_client.aclose()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "provider_id,enterprise",
    [
        (2, "California"),
        (3, "Florida"),
        (4, "Virginia"),
        (5, "Minnesota"),
        (6, "Ohio"),
        (7, "Arizona"),
        (8, "Missouri"),
        (9, "FairfaxFCPA"),
        (10, "OregonMetro"),
        (11, "NorthernTerritory"),
    ],
)
async def test_each_deployment_uses_verified_image_origin(
    provider_id: int, enterprise: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Build each deployment's image path without trusting upstream URL fields."""
    instance = PROVIDERS[provider_id]()
    assert isinstance(instance, UseDirectProvider)
    await instance.async_client.aclose()
    information = AsyncMock(return_value=httpx2.Response(200, json=park_information()))
    monkeypatch.setattr(instance, "_request", information)
    urls: list[str] = []

    def respond(request: httpx2.Request) -> httpx2.Response:
        """Return a JPEG only for the configured public destination image."""
        urls.append(str(request.url))
        return httpx2.Response(
            200,
            headers={"Content-Type": "image/jpeg"},
            content=b"\xff\xd8\xff\xe0synthetic",
        )

    instance.async_client = httpx2.AsyncClient(transport=httpx2.MockTransport(respond))
    try:
        details = await fetch_details(
            instance,
            Destination(
                entity_type="recreation_area",
                id="1",
                name="Synthetic park",
                recreation_area_id=None,
            ),
        )
        assert details is not None
        expected = f"{instance.booking_url}/images/{enterprise}/ParkImages/Place/1.jpg"
        assert urls == [expected]
        assert details.photos[0].url == expected
        assert details.links[0].url == "https://parks.example.org/synthetic"
        assert [fact.value for fact in details.hours] == [
            "Weekdays 9-5",
            "Sunrise to sunset",
        ]
        assert [fact.value for fact in details.vehicle_limits] == ["35"]
        information.assert_awaited_once_with(
            "GET", "fd/placeinfo/additional-place-info/1"
        )
    finally:
        await instance.async_client.aclose()


@pytest.mark.asyncio
@pytest.mark.parametrize("status", [404, 410])
async def test_missing_photo_keeps_practical_information(
    provider: UseDirectProvider, monkeypatch: pytest.MonkeyPatch, status: int
) -> None:
    """A confirmed missing image is a valid empty gallery, not lost park data."""
    monkeypatch.setattr(
        provider,
        "_request",
        AsyncMock(
            return_value=httpx2.Response(
                200, json=park_information(DisplayMaxTrailerLengthOnWeb=False)
            )
        ),
    )
    provider.async_client = httpx2.AsyncClient(
        transport=httpx2.MockTransport(lambda request: httpx2.Response(status))
    )
    details = await fetch_details(
        provider,
        Destination(
            entity_type="recreation_area", id="1", name="Park", recreation_area_id=None
        ),
    )
    assert details is not None and details.photos == []
    assert details.hours and details.vehicle_limits == []


@pytest.mark.asyncio
@pytest.mark.parametrize("status", [403, 429, 500])
async def test_image_access_failures_do_not_become_empty_snapshots(
    provider: UseDirectProvider, status: int
) -> None:
    """Refresh machinery can preserve earlier data when photo access fails."""
    provider.async_client = httpx2.AsyncClient(
        transport=httpx2.MockTransport(lambda request: httpx2.Response(status))
    )
    with pytest.raises(httpx2.HTTPStatusError):
        await fetch_details(
            provider,
            Destination(
                entity_type="campground", id="10", name="Camp", recreation_area_id="1"
            ),
        )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "response",
    [
        httpx2.Response(
            302, headers={"Location": "https://other.example.org/image.jpg"}
        ),
        httpx2.Response(
            200,
            headers={"Content-Type": "text/html"},
            content=b"<html>Not an image</html>",
        ),
        httpx2.Response(
            200,
            headers={"Content-Type": "image/jpeg"},
            content=b"<html>Not an image</html>",
        ),
    ],
)
async def test_static_images_reject_redirects_and_nonimages(
    provider: UseDirectProvider, response: httpx2.Response
) -> None:
    """Do not follow arbitrary destinations or accept HTML with an image suffix."""
    requests: list[str] = []

    def respond(request: httpx2.Request) -> httpx2.Response:
        """Record that validation never fetches the redirect target."""
        requests.append(str(request.url))
        return response

    provider.async_client = httpx2.AsyncClient(
        transport=httpx2.MockTransport(respond), follow_redirects=True
    )
    with pytest.raises((ValueError, httpx2.HTTPStatusError)):
        await fetch_details(
            provider,
            Destination(
                entity_type="campground", id="10", name="Camp", recreation_area_id="1"
            ),
        )
    assert len(requests) == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("information", [{"PlaceId": 1}, park_information(PlaceId=2)])
async def test_partial_or_mismatched_park_response_fails(
    provider: UseDirectProvider,
    monkeypatch: pytest.MonkeyPatch,
    information: dict[str, Any],
) -> None:
    """Never replace cached details using partial data or another park's response."""
    monkeypatch.setattr(
        provider,
        "_request",
        AsyncMock(return_value=httpx2.Response(200, json=information)),
    )
    with pytest.raises(ValueError):
        await fetch_details(
            provider,
            Destination(
                entity_type="recreation_area",
                id="1",
                name="Park",
                recreation_area_id=None,
            ),
        )


@pytest.mark.asyncio
async def test_campground_image_does_not_fetch_or_inherit_park_information(
    provider: UseDirectProvider, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Campground media keeps its facility scope and makes no parent API request."""
    information = AsyncMock()
    monkeypatch.setattr(provider, "_request", information)
    provider.async_client = httpx2.AsyncClient(
        transport=httpx2.MockTransport(lambda request: httpx2.Response(404))
    )
    details = await fetch_details(
        provider,
        Destination(
            entity_type="campground", id="10", name="Camp", recreation_area_id="1"
        ),
    )
    assert details is not None and details.photos == [] and details.hours == []
    information.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("entity_id", ["../1", "1?other=2", "-1"])
async def test_native_id_is_validated_before_network(
    provider: UseDirectProvider, entity_id: str
) -> None:
    """Only existing numeric provider identities may enter static asset paths."""
    with pytest.raises(ValueError):
        await fetch_details(
            provider,
            Destination(
                entity_type="campground",
                id=entity_id,
                name="Camp",
                recreation_area_id=None,
            ),
        )


@pytest.mark.asyncio
async def test_image_validation_reads_only_a_bounded_prefix(
    provider: UseDirectProvider,
) -> None:
    """A large upstream image is closed after validation instead of downloaded."""

    class PrefixOnlyStream(httpx2.AsyncByteStream):
        """Fail if validation attempts to consume the remainder of the image."""

        closed = False
        """Whether the response context released the image stream."""

        async def __aiter__(self) -> AsyncIterator[bytes]:
            """Expose one JPEG prefix and reject every later byte request."""
            yield b"\xff\xd8\xff\xe0" + b"x" * 28
            raise AssertionError("Image validation consumed more than its prefix")

        async def aclose(self) -> None:
            """Record that prefix validation still closes the network response."""
            self.closed = True

    stream = PrefixOnlyStream()
    provider.async_client = httpx2.AsyncClient(
        transport=httpx2.MockTransport(
            lambda request: httpx2.Response(
                200, headers={"Content-Type": "image/jpeg"}, stream=stream
            )
        )
    )
    details = await fetch_details(
        provider,
        Destination(
            entity_type="campground", id="10", name="Camp", recreation_area_id="1"
        ),
    )
    assert details is not None and len(details.photos) == 1 and stream.closed


@pytest.mark.asyncio
async def test_cached_refresh_preserves_failure_then_replaces_confirmed_empty(
    provider: UseDirectProvider, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Per-entity source errors preserve old details; an absent photo clears them."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    monkeypatch.setattr(
        "camply.providers.enrichment.db", SimpleNamespace(get_session=sessions)
    )
    old = DestinationDetails(
        source_url="https://parks.example.org/old",
        fetched_at=datetime.now(tz=timezone.utc) - timedelta(days=8),
        photos=[DestinationPhoto(url="https://images.example.org/old.jpg")],
    ).model_dump(mode="json")
    async with sessions.begin() as session:
        session.add(Provider(id=3, name="Synthetic", url="https://parks.example.org"))
        await session.flush()
        session.add(RecreationArea(id="1", provider_id=3, name="Park", details=old))
    monkeypatch.setattr(
        provider,
        "_request",
        AsyncMock(return_value=httpx2.Response(200, json=park_information())),
    )
    status = 403
    provider.async_client = httpx2.AsyncClient(
        transport=httpx2.MockTransport(lambda request: httpx2.Response(status))
    )
    try:
        await provider.enrich_metadata()
        async with sessions() as session:
            row = await session.get(RecreationArea, ("1", 3))
            assert row is not None and row.details == old
        status = 404
        async with sessions.begin() as session:
            await session.execute(
                update(RecreationArea).values(
                    details_attempted_at=datetime.now(tz=timezone.utc)
                    - timedelta(hours=2)
                )
            )
        await provider.enrich_metadata()
        async with sessions() as session:
            row = await session.get(RecreationArea, ("1", 3))
            assert row is not None and row.details is not None
            assert row.details["photos"] == []
            assert row.details["fetched_at"] != old["fetched_at"]
    finally:
        await engine.dispose()
