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
                    latitude=10,
                    longitude=10,
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
            ("null_island", 0, 0),
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
        136,
        133,
        3,
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
    assert (
        "missing" not in visited
        and "invalid" not in visited
        and "null_island" not in visited
    )


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


@pytest.mark.asyncio
async def test_explore_filters_items_counts_facets_and_pages_by_viewport(
    map_session: AsyncSession,
) -> None:
    """Viewport filtering covers the full catalog before counts and pagination."""
    bounds = Bounds(west=9, south=9, east=11, north=11)
    rows, total, facets = await Search.search(
        session=map_session, bounds=bounds, limit=20, offset=20, has_electric=True
    )
    assert len(rows) == 20
    assert total == 65
    assert facets["states"] == {"CA": 65}
    assert all(row.latitude == 10 and row.longitude == 10 for row in rows)
    zero_bounds = Bounds(west=-1, south=-1, east=1, north=1)
    zero_rows, zero_total, _ = await Search.search(
        session=map_session, bounds=zero_bounds
    )
    assert zero_total == 0
    assert len(zero_rows) == 0
    dateline = Bounds(west=178, south=0, east=-178, north=3)
    rows, total, _ = await Search.search(session=map_session, bounds=dateline)
    assert {row.id for row in rows} == {"west", "east"}
    assert total == 2
    rows, total, _ = await Search.search(
        session=map_session, bounds=Bounds(west=-180, south=-90, east=180, north=90)
    )
    assert total == 133


@pytest.mark.asyncio
async def test_lat_lon_zero_filtering(map_session: AsyncSession) -> None:
    """Mapping results filter out lat/lon of 0/0 while keeping 0 latitude or 0 longitude."""
    map_session.add(
        Search(
            id="equator_place",
            entity_type="RecreationArea",
            provider_id=1,
            provider_name="Fixture",
            recreation_area_id="equator_place",
            recreation_area_name="Equator Place",
            latitude=0.0,
            longitude=10.0,
        )
    )
    map_session.add(
        Search(
            id="prime_meridian_place",
            entity_type="RecreationArea",
            provider_id=1,
            provider_name="Fixture",
            recreation_area_id="prime_meridian_place",
            recreation_area_name="Prime Meridian Place",
            latitude=10.0,
            longitude=0.0,
        )
    )
    await map_session.commit()
    summary = await map_summary(map_session, filters={"term": "Place"})
    assert summary.total == 2
    assert summary.mappable_total == 2
    assert summary.unmappable_total == 0

    co_summary = await map_summary(map_session, filters={"state": "co"})
    assert co_summary.total == 6
    assert co_summary.mappable_total == 3
    assert co_summary.unmappable_total == 3
