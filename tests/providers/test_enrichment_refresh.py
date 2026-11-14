"""Verify bounded cache refreshes retain correct snapshots and advance work."""

from collections.abc import AsyncGenerator
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from camply.db.models import Base, Campground, Provider, RecreationArea
from camply.providers.details import DestinationDetails, DestinationPhoto
from camply.providers.enrichment import (
    Destination,
    mark_attempt,
    refresh_destinations,
    stale_destinations,
)


def _snapshot(label: str, *, days_old: int = 8) -> dict[str, Any]:
    """Build deterministic-purpose cache data with relative freshness."""
    return DestinationDetails(
        source_url=f"https://parks.example.com/{label}",
        fetched_at=datetime.now(timezone.utc) - timedelta(days=days_old),
        photos=[DestinationPhoto(url=f"https://photos.example.com/{label}.jpg")],
    ).model_dump(mode="json")


@pytest_asyncio.fixture
async def cache_database(
    monkeypatch: pytest.MonkeyPatch,
) -> AsyncGenerator[async_sessionmaker[AsyncSession], None]:
    """Provide isolated catalog storage without touching operator databases."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    maker = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    async with maker.begin() as session:
        session.add_all(
            [
                Provider(
                    id=provider_id,
                    name=f"Synthetic provider {provider_id}",
                    url=f"https://parks.example.com/provider-{provider_id}",
                )
                for provider_id in (1, 2)
            ]
        )
    monkeypatch.setattr(
        "camply.providers.enrichment.db", SimpleNamespace(get_session=maker)
    )
    try:
        yield maker
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_selection_is_bounded_and_excludes_fresh_or_ineligible_records(
    cache_database: async_sessionmaker[AsyncSession],
) -> None:
    """Older caches and never-enriched destinations are selected across both kinds."""
    async with cache_database.begin() as session:
        session.add_all(
            [
                RecreationArea(id="missing", provider_id=1, name="Missing"),
                Campground(
                    id="old", provider_id=1, name="Old", details=_snapshot("old")
                ),
                Campground(
                    id="fresh",
                    provider_id=1,
                    name="Fresh",
                    details=_snapshot("fresh", days_old=0),
                ),
                RecreationArea(
                    id="other-provider", provider_id=2, name="Other provider"
                ),
                RecreationArea(
                    id="disabled", provider_id=1, name="Disabled", enabled=False
                ),
                Campground(
                    id="non-reservable",
                    provider_id=1,
                    name="Non reservable",
                    reservable=False,
                ),
            ]
        )
    destinations = await stale_destinations(1, limit=2)
    assert [(row.entity_type, row.id) for row in destinations] == [
        ("recreation_area", "missing"),
        ("campground", "old"),
    ]
    assert len(await stale_destinations(1, limit=1)) == 1


@pytest.mark.asyncio
async def test_failed_refresh_retains_cache_while_complete_empty_clears_own_entity(
    cache_database: async_sessionmaker[AsyncSession],
) -> None:
    """Refresh outcomes remain isolated across coinciding provider and entity IDs."""
    before_campground = _snapshot("old-campground")
    before_area = _snapshot("old-area")
    other_provider = _snapshot("other-provider")
    async with cache_database.begin() as session:
        session.add_all(
            [
                RecreationArea(
                    id="shared", provider_id=1, name="Area", details=before_area
                ),
                Campground(
                    id="shared",
                    provider_id=1,
                    name="Campground",
                    details=before_campground,
                ),
                Campground(
                    id="shared",
                    provider_id=2,
                    name="Other provider",
                    details=other_provider,
                ),
            ]
        )

    async def fetch(destination: Destination) -> DestinationDetails:
        """Fail one source and return a valid empty gallery for the other."""
        if destination.entity_type == "campground":
            raise ValueError("Synthetic malformed response")
        return DestinationDetails(
            source_url="https://parks.example.com/refreshed-area",
            fetched_at=datetime.now(timezone.utc),
        )

    await refresh_destinations(1, fetch)
    async with cache_database() as session:
        campground = await session.get(Campground, ("shared", 1))
        area = await session.get(RecreationArea, ("shared", 1))
        other = await session.get(Campground, ("shared", 2))
        assert campground is not None and campground.details == before_campground
        assert other is not None and other.details == other_provider
        assert area is not None and area.details is not None
        assert area.details["photos"] == []
        assert area.details["fetched_at"] != before_area["fetched_at"]


@pytest.mark.asyncio
async def test_failed_batch_advances_to_untouched_destinations(
    cache_database: async_sessionmaker[AsyncSession],
) -> None:
    """A bounded failing batch cannot indefinitely starve the rest of the catalog."""
    async with cache_database.begin() as session:
        session.add_all(
            [
                Campground(id=identifier, provider_id=1, name=identifier)
                for identifier in ("a", "b", "c")
            ]
        )
    attempted: list[str] = []

    async def fail(destination: Destination) -> DestinationDetails:
        """Keep failed destinations stale while recording observable work order."""
        attempted.append(destination.id)
        raise ValueError("Synthetic unavailable upstream")

    await refresh_destinations(1, fail, limit=1)
    await refresh_destinations(1, fail, limit=1)
    assert attempted == ["a", "b"]


@pytest.mark.asyncio
async def test_ordinary_catalog_merge_preserves_enrichment(
    cache_database: async_sessionmaker[AsyncSession],
) -> None:
    """Catalog refresh constructors do not erase data they leave unspecified."""
    before = _snapshot("preserved")
    async with cache_database.begin() as session:
        session.add_all(
            [
                Campground(id="same", provider_id=1, name="Old", details=before),
                RecreationArea(id="same", provider_id=1, name="Old", details=before),
            ]
        )
    async with cache_database.begin() as session:
        await session.merge(Campground(id="same", provider_id=1, name="New"))
        await session.merge(RecreationArea(id="same", provider_id=1, name="New"))
    async with cache_database() as session:
        for model in (Campground, RecreationArea):
            row = await session.get(model, ("same", 1))
            assert row is not None
            assert row.name == "New"
            assert row.details == before


@pytest.mark.asyncio
async def test_attempt_is_claimed_only_once(
    cache_database: async_sessionmaker[AsyncSession],
) -> None:
    """Concurrent/manual refreshes cannot both claim an entity during cooldown."""
    async with cache_database.begin() as session:
        session.add(Campground(id="claimed", provider_id=1, name="Claimed"))
    destination = Destination("campground", "claimed", "Claimed")
    assert await mark_attempt(1, destination)
    assert not await mark_attempt(1, destination)
    assert not await stale_destinations(1)


@pytest.mark.asyncio
@pytest.mark.parametrize("failure", [False, True])
async def test_worker_enrichment_follows_catalog_and_closes_on_source_failure(
    failure: bool,
) -> None:
    """Both worker runtimes share post-catalog enrichment with failure isolation."""
    from camply.worker.engine.catalog import populate_provider

    order: list[str] = []

    async def catalog() -> None:
        """Record completed catalog ingestion."""
        order.append("catalog")

    async def enrich() -> None:
        """Record optional enrichment and simulate an upstream outage."""
        order.append("enrichment")
        if failure:
            raise ValueError("Synthetic unavailable source")

    async def close() -> None:
        """Record released HTTP connections."""
        order.append("close")

    provider = SimpleNamespace(
        populate_database=catalog,
        enrich_metadata=enrich,
        async_client=SimpleNamespace(aclose=close),
    )
    factory = MagicMock(return_value=provider)
    factory.__name__ = "SyntheticProvider"
    result = await populate_provider(1, factory)
    assert result["status"] == "success"
    assert order == ["catalog", "enrichment", "close"]


@pytest.mark.parametrize("failure", [False, True])
def test_cli_metadata_includes_optional_enrichment(
    monkeypatch: pytest.MonkeyPatch, failure: bool
) -> None:
    """CLI metadata uses the same post-catalog extension and releases its client."""
    from click.testing import CliRunner

    from camply.cli.db import metadata_cmd

    provider = SimpleNamespace(
        populate_database=AsyncMock(),
        enrich_metadata=AsyncMock(
            side_effect=ValueError("Synthetic source failure") if failure else None
        ),
        async_client=SimpleNamespace(aclose=AsyncMock()),
    )
    monkeypatch.setattr("camply.cli.db.PROVIDERS", {1: lambda: provider})
    result = CliRunner().invoke(metadata_cmd, ["--provider-id", "1"])
    assert result.exit_code == 0, result.output
    provider.populate_database.assert_awaited_once()
    provider.enrich_metadata.assert_awaited_once()
    provider.async_client.aclose.assert_awaited_once()
