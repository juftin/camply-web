"""Synthetic ReserveAmerica facility detail and original-photo regressions."""

from collections.abc import AsyncGenerator
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from sqlalchemy import update
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from camply.db.models import Base, Campground, Provider
from camply.providers.details import DestinationDetails, DestinationPhoto
from camply.providers.enrichment import Destination
from camply.providers.reserve_america.enrichment import fetch_details
from camply.providers.reserve_america.provider import ReserveAmericaProvider


def facility_information(**changes: Any) -> dict[str, Any]:
    """Return a complete synthetic facility enrichment response."""
    return {
        "id": 1,
        "contrCode": "CO",
        "originalPhotos": [
            {
                "photoURL": "/webphotos/originals/CO/pid1/{pht}one%20image.jpg",
                "description": "Synthetic lake view",
            },
            {
                "photoURL": "/webphotos/originals/CO/pid1/{pht}one%20image.jpg",
                "description": "Duplicate rendition",
            },
        ],
        "facilityPhotos": [
            {"photoURL": "/webphotos/CO/pid1/0", "description": "Alternate rendition"}
        ],
        "notes": [
            {
                "type": "general",
                "headline": "Overview",
                "content": "<p>Quiet synthetic campground.</p>",
            }
        ],
        "directions": {"directionsInfo": {"content": "Follow the signed road."}},
        "amenities": [
            {
                "name": "Drinking water",
                "distanceCode": "2000",
                "distanceName": "Within Facility",
            },
            {
                "name": "Boat launch",
                "distanceCode": "2100",
                "distanceName": "Within 10 Miles",
            },
        ],
        "relatedLinks": [
            {
                "linkLabel": "Official park",
                "linkURL": "https://parks.example.org/synthetic",
            }
        ],
        "feesCancellationsDescription": "Provider fees apply.",
        "seasons": [
            {
                "name": "Camping",
                "datePeriod": {"startDate": "2030-04-01", "endDate": "2030-10-31"},
            }
        ],
        **changes,
    }


@pytest_asyncio.fixture
async def provider() -> AsyncGenerator[ReserveAmericaProvider, None]:
    """Release the provider's retry sockets without making real HTTP requests."""
    instance = ReserveAmericaProvider()
    yield instance
    await instance.async_client.aclose()


@pytest.mark.asyncio
async def test_original_photos_and_practical_information(
    provider: ReserveAmericaProvider, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Keep original photos once, retain escaped paths, and qualify nearby amenities."""
    request = AsyncMock(return_value=facility_information())
    monkeypatch.setattr(provider, "_request", request)
    details = await fetch_details(
        provider,
        Destination(
            entity_type="campground", id="CO_1", name="Camp", recreation_area_id=None
        ),
    )
    assert details is not None
    request.assert_awaited_once_with("facilities/CO/1", {"detailsOnly": "false"})
    assert len(details.photos) == 1
    assert (
        details.photos[0].url
        == "https://a1.reserveamerica.com/webphotos/originals/CO/pid1/%7Bpht%7Done%20image.jpg"
    )
    assert details.photos[0].caption == "Synthetic lake view"
    assert details.description == "<p>Quiet synthetic campground.</p>"
    assert details.directions == "Follow the signed road."
    assert details.fee_information == "Provider fees apply."
    assert details.amenities == ["Drinking water", "Boat launch (Within 10 Miles)"]
    assert details.links[0].url == "https://parks.example.org/synthetic"
    assert details.hours[0].label == "Season: Camping"
    assert "2030-04-01" in details.hours[0].value


@pytest.mark.asyncio
async def test_complete_empty_photo_list_is_valid(
    provider: ReserveAmericaProvider, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A destination without a gallery still has useful cached practical details."""
    monkeypatch.setattr(
        provider,
        "_request",
        AsyncMock(return_value=facility_information(originalPhotos=[])),
    )
    details = await fetch_details(
        provider,
        Destination(
            entity_type="campground", id="CO_1", name="Camp", recreation_area_id=None
        ),
    )
    assert details is not None and details.photos == [] and details.amenities


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "changes",
    [
        {"id": 2},
        {"contrCode": "NY"},
        {"originalPhotos": None},
        {"originalPhotos": [{}]},
        {"amenities": "wrong type"},
    ],
)
async def test_wrong_identity_or_malformed_snapshot_fails(
    provider: ReserveAmericaProvider,
    monkeypatch: pytest.MonkeyPatch,
    changes: dict[str, Any],
) -> None:
    """Invalid identity or incomplete data must preserve earlier successful enrichment."""
    monkeypatch.setattr(
        provider, "_request", AsyncMock(return_value=facility_information(**changes))
    )
    with pytest.raises(ValueError):
        await fetch_details(
            provider,
            Destination(
                entity_type="campground",
                id="CO_1",
                name="Camp",
                recreation_area_id=None,
            ),
        )


@pytest.mark.asyncio
async def test_missing_photo_member_is_not_a_successful_empty_gallery(
    provider: ReserveAmericaProvider, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A partial response cannot silently erase a previously populated gallery."""
    partial = facility_information()
    del partial["originalPhotos"]
    monkeypatch.setattr(provider, "_request", AsyncMock(return_value=partial))
    with pytest.raises(ValueError):
        await fetch_details(
            provider,
            Destination(
                entity_type="campground",
                id="CO_1",
                name="Camp",
                recreation_area_id=None,
            ),
        )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "url",
    [
        "https://evil.example.org/photo.jpg",
        "//evil.example.org/photo.jpg",
        "/webphotos/originals/NY/pid1/photo.jpg",
        "/webphotos/originals/CO/pid2/photo.jpg",
        "/webphotos/originals/CO/pid1/../photo.jpg",
    ],
)
async def test_media_must_belong_to_requested_facility_on_known_source(
    provider: ReserveAmericaProvider, monkeypatch: pytest.MonkeyPatch, url: str
) -> None:
    """Untrusted origins and another facility's media cannot become cached photos."""
    monkeypatch.setattr(
        provider,
        "_request",
        AsyncMock(
            return_value=facility_information(originalPhotos=[{"photoURL": url}])
        ),
    )
    with pytest.raises(ValueError):
        await fetch_details(
            provider,
            Destination(
                entity_type="campground",
                id="CO_1",
                name="Camp",
                recreation_area_id=None,
            ),
        )


@pytest.mark.asyncio
async def test_recreation_areas_are_unsupported_without_requests(
    provider: ReserveAmericaProvider, monkeypatch: pytest.MonkeyPatch
) -> None:
    """ReserveAmerica cannot fabricate a parent park catalog during enrichment."""
    request = AsyncMock()
    monkeypatch.setattr(provider, "_request", request)
    assert (
        await fetch_details(
            provider,
            Destination(
                entity_type="recreation_area",
                id="1",
                name="Park",
                recreation_area_id=None,
            ),
        )
        is None
    )
    request.assert_not_awaited()


@pytest.mark.asyncio
async def test_optional_empty_season_dates_and_unsafe_links(
    provider: ReserveAmericaProvider, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Missing seasonal dates and unsafe supplementary links do not invent facts."""
    monkeypatch.setattr(
        provider,
        "_request",
        AsyncMock(
            return_value=facility_information(
                seasons=[{"name": "Camping", "datePeriod": None}],
                relatedLinks=[
                    {"linkLabel": "Unsafe", "linkURL": "javascript:alert(1)"}
                ],
            )
        ),
    )
    details = await fetch_details(
        provider,
        Destination(
            entity_type="campground", id="CO_1", name="Camp", recreation_area_id=None
        ),
    )
    assert details is not None and details.hours == [] and details.links == []


@pytest.mark.asyncio
async def test_cached_refresh_retains_partial_response_then_accepts_empty_gallery(
    provider: ReserveAmericaProvider, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Partial source data never erases the old gallery or successful timestamp."""
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
        session.add(Provider(id=13, name="Synthetic", url="https://parks.example.org"))
        await session.flush()
        session.add(Campground(id="CO_1", provider_id=13, name="Camp", details=old))
    request = AsyncMock(return_value={"id": 1, "contrCode": "CO"})
    monkeypatch.setattr(provider, "_request", request)
    try:
        await provider.enrich_metadata()
        async with sessions() as session:
            row = await session.get(Campground, ("CO_1", 13))
            assert row is not None and row.details == old
        request.return_value = facility_information(originalPhotos=[])
        async with sessions.begin() as session:
            await session.execute(
                update(Campground).values(
                    details_attempted_at=datetime.now(tz=timezone.utc)
                    - timedelta(hours=2)
                )
            )
        await provider.enrich_metadata()
        async with sessions() as session:
            row = await session.get(Campground, ("CO_1", 13))
            assert row is not None and row.details is not None
            assert row.details["photos"] == []
            assert row.details["fetched_at"] != old["fetched_at"]
    finally:
        await engine.dispose()
