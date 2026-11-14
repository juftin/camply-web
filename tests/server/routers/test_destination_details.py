"""Verify cached enrichment is scoped correctly and excluded from summaries."""

import asyncio
from collections.abc import Iterator
from typing import Any

import httpx2
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete

from camply.db.models import Campground, RecreationArea
from tests.server.conftest import maker

_ENTITY_ID = "enrichment-shared-id"
"""Synthetic ID intentionally shared across providers and destination types."""


def _snapshot(label: str) -> dict[str, Any]:
    """Build distinct public-source snapshots without personal data."""
    return {
        "source_url": f"https://parks.example.com/{label}",
        "fetched_at": "2030-01-01T00:00:00Z",
        "directions": f"Directions for {label}",
        "photos": [
            {
                "url": f"https://photos.example.com/{label}.jpg",
                "caption": label,
            }
        ],
    }


@pytest.fixture
def destination_snapshots() -> Iterator[None]:
    """Seed and remove isolated provider/type collision fixtures."""

    async def seed() -> None:
        """Use existing provider identities and independent synthetic rows."""
        async with maker() as session:
            for provider_id in (1, 2):
                session.add(
                    RecreationArea(
                        id=_ENTITY_ID,
                        provider_id=provider_id,
                        name=f"Synthetic area {provider_id}",
                        description="Existing area description",
                        details=_snapshot(f"area-{provider_id}"),
                        reservable=True,
                        enabled=True,
                    )
                )
            await session.flush()
            for provider_id in (1, 2):
                session.add(
                    Campground(
                        id=_ENTITY_ID,
                        provider_id=provider_id,
                        recreation_area_id=_ENTITY_ID,
                        name=f"Synthetic campground {provider_id}",
                        description="Existing campground description",
                        details=_snapshot(f"campground-{provider_id}"),
                        reservable=True,
                        enabled=True,
                    )
                )
            session.add(
                Campground(
                    id="enrichment-empty",
                    provider_id=1,
                    recreation_area_id=_ENTITY_ID,
                    name="Synthetic empty campground",
                    description="Description without enrichment",
                    reservable=True,
                    enabled=True,
                )
            )
            await session.commit()

    async def clean() -> None:
        """Leave shared server fixtures unchanged for other router suites."""
        async with maker() as session:
            await session.execute(
                delete(Campground).where(
                    Campground.id.in_([_ENTITY_ID, "enrichment-empty"])
                )
            )
            await session.execute(
                delete(RecreationArea).where(RecreationArea.id == _ENTITY_ID)
            )
            await session.commit()

    asyncio.run(seed())
    yield
    asyncio.run(clean())


@pytest.mark.usefixtures("destination_snapshots")
@pytest.mark.parametrize("provider_id", [1, 2])
@pytest.mark.parametrize(
    "route,label", [("campground", "campground"), ("rec-area", "area")]
)
def test_detail_snapshots_preserve_provider_and_entity_scope(
    test_client: TestClient,
    provider_id: int,
    route: str,
    label: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Detail reads use their own cached data and perform no upstream request."""

    async def reject_upstream(*args: object, **kwargs: object) -> None:
        """Make unexpected provider traffic an explicit regression failure."""
        raise AssertionError("Detail reads must not request upstream information")

    monkeypatch.setattr(httpx2.AsyncClient, "request", reject_upstream)
    response = test_client.get(f"/api/{route}/{provider_id}/{_ENTITY_ID}")
    assert response.status_code == 200
    payload = response.json()
    assert "details_attempted_at" not in payload
    assert payload["provider_id"] == provider_id
    assert payload["details"]["directions"] == f"Directions for {label}-{provider_id}"
    assert payload["details"]["photos"][0]["url"] == (
        f"https://photos.example.com/{label}-{provider_id}.jpg"
    )
    assert payload["details"]["fetched_at"] == "2030-01-01T00:00:00Z"


@pytest.mark.usefixtures("destination_snapshots")
def test_area_child_summaries_exclude_enrichment(test_client: TestClient) -> None:
    """A populated detail cache never expands campground listing responses."""
    response = test_client.get(f"/api/rec-area/1/{_ENTITY_ID}/campgrounds")
    assert response.status_code == 200
    campgrounds = response.json()
    assert {row["id"] for row in campgrounds} == {_ENTITY_ID, "enrichment-empty"}
    assert all("details" not in row for row in campgrounds)


@pytest.mark.usefixtures("destination_snapshots")
def test_destination_without_snapshot_retains_existing_description(
    test_client: TestClient,
) -> None:
    """Older records remain usable with an explicit null detail snapshot."""
    response = test_client.get("/api/campground/1/enrichment-empty")
    assert response.status_code == 200
    assert response.json()["details"] is None
    assert response.json()["description"] == "Description without enrichment"
