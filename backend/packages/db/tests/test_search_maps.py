"""Behavioral map query tests against a synthetic catalog."""

from collections.abc import AsyncIterator

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from db.models import Base, Search
from db.search_maps import Bounds, map_features, map_members, map_summary


@pytest_asyncio.fixture
async def map_session() -> AsyncIterator[AsyncSession]:
    """Provide a synthetic catalog with co-located and unmappable places."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    async with async_sessionmaker(engine, expire_on_commit=False)() as session:
        session.add_all(
            [
                Search(
                    id=f"Camp/{i % 2 + 1}/area/{i:04}",
                    entity_type="Campground",
                    provider_id=i % 2 + 1,
                    provider_name="Fixture",
                    campground_id=f"{i:04}",
                    campground_name="Fixture Pines",
                    recreation_area_id="area",
                    recreation_area_name="Fixture Park",
                    state="CA",
                    latitude=0,
                    longitude=0,
                    has_electric=i % 2 == 0,
                    pets_allowed=True,
                    max_rv_length=30,
                )
                for i in range(130)
            ]
        )
        for identifier, lat, lng in [
            ("west", 1, 179),
            ("east", 2, -179),
            ("missing", None, None),
            ("invalid", 91, 0),
            ("pole", 90, 180),
        ]:
            session.add(
                Search(
                    id=identifier,
                    entity_type="RecreationArea",
                    provider_id=1,
                    provider_name="Fixture",
                    recreation_area_id=identifier,
                    recreation_area_name="Fixture Park",
                    latitude=lat,
                    longitude=lng,
                    state="CO",
                )
            )
        await session.commit()
        yield session
    await engine.dispose()


@pytest.mark.asyncio
async def test_summary_preserves_unmappable_and_dateline(
    map_session: AsyncSession,
) -> None:
    """Count all matches but frame only usable coordinates on a circular arc."""
    result = await map_summary(map_session, filters={})
    assert (result.total, result.mappable_total, result.unmappable_total) == (
        135,
        133,
        2,
    )
    wrapped = await map_summary(map_session, filters={"state": "co"})
    assert wrapped.bounds is not None
    assert wrapped.bounds.west == 179
    assert wrapped.bounds.east == -179
    empty = await map_summary(map_session, filters={"term": "no such place"})
    assert empty.total == 0 and empty.bounds is None


@pytest.mark.asyncio
async def test_complete_membership_and_keysets(map_session: AsyncSession) -> None:
    """Every mapped match remains reachable without loading all list pages."""
    bounds = Bounds(west=-180, south=-90, east=180, north=90)
    page = await map_features(map_session, bounds=bounds, zoom=19, filters={})
    assert len(page.cells) <= 512
    assert sum(cell.count for cell in page.cells) == 133
    visited: set[str] = set()
    for cell in page.cells:
        if cell.item is not None:
            visited.add(cell.item.id)
            continue
        cursor = None
        while True:
            members = await map_members(
                map_session,
                bounds=bounds,
                cell_id=cell.cell_id,
                filters={},
                after_id=cursor,
                page_size=50,
            )
            assert len(members.items) <= 50
            assert members.total == cell.count
            visited.update(item.id for item in members.items)
            cursor = members.next_cursor
            if cursor is None:
                break
    assert len(visited) == 133
    assert "missing" not in visited and "invalid" not in visited


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "filters",
    [
        {"state": "CA"},
        {"has_electric": True},
        {"has_electric": False},
        {"min_rv_length": 31},
        {"term": "Fixture Pines"},
        {"provider_ids": [2]},
        {"entity_types": ["RecreationArea"]},
        {"lat": 0, "lng": 0, "radius_miles": 1},
    ],
)
async def test_map_filter_membership_matches_list(
    map_session: AsyncSession, filters: dict
) -> None:
    """Use precisely the existing list predicates for all map endpoints."""
    _, total, _ = await Search.search(map_session, limit=1000, **filters)
    result = await map_summary(map_session, filters=filters)
    assert result.total == total


@pytest.mark.asyncio
async def test_wrapped_viewport_and_captured_group_scope(
    map_session: AsyncSession,
) -> None:
    """Viewport counts and member queries use the same cell intersection."""
    bounds = Bounds(west=178, south=-1, east=-178, north=3)
    page = await map_features(map_session, bounds=bounds, zoom=0, filters={})
    assert sum(cell.count for cell in page.cells) == 2
    for cell in page.cells:
        members = await map_members(
            map_session, bounds=bounds, cell_id=cell.cell_id, filters={}
        )
        assert members.total == cell.count


@pytest.mark.asyncio
@pytest.mark.parametrize("zoom", range(20))
async def test_grid_cap_at_every_zoom(map_session: AsyncSession, zoom: int) -> None:
    """Coarsen before aggregation even when the requested viewport is global."""
    page = await map_features(
        map_session,
        bounds=Bounds(west=-180, south=-90, east=180, north=90),
        zoom=zoom,
        filters={},
    )
    assert len(page.cells) <= 512
    assert sum(cell.count for cell in page.cells) == 133
