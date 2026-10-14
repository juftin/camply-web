"""
Tests for Search model, composable search, and facets.
"""

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from db.models import Base, Search


@pytest_asyncio.fixture(name="async_session")
async def async_session_fixture():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with maker() as session:
        yield session

    await engine.dispose()


@pytest_asyncio.fixture(name="seeded_search_data")
async def seeded_search_data_fixture(async_session: AsyncSession):
    rows = [
        Search(
            id="RecArea/1/1001",
            entity_type="RecreationArea",
            provider_id=1,
            provider_name="recreation_dot_gov",
            recreation_area_id="1001",
            recreation_area_name="Yosemite National Park",
            campground_id=None,
            campground_name=None,
            city="Yosemite Valley",
            state="CA",
            country="USA",
            latitude=37.8651,
            longitude=-119.5383,
            reservable=True,
            has_electric=False,
            pets_allowed=True,
            max_rv_length=35,
        ),
        Search(
            id="Camp/1/1001/2001",
            entity_type="Campground",
            provider_id=1,
            provider_name="recreation_dot_gov",
            recreation_area_id="1001",
            recreation_area_name="Yosemite National Park",
            campground_id="2001",
            campground_name="Upper Pines",
            city="Yosemite Valley",
            state="CA",
            country="USA",
            latitude=37.737,
            longitude=-119.565,
            reservable=True,
            has_electric=True,
            pets_allowed=True,
            max_rv_length=35,
        ),
        Search(
            id="Camp/1/1001/2002",
            entity_type="Campground",
            provider_id=1,
            provider_name="recreation_dot_gov",
            recreation_area_id="1001",
            recreation_area_name="Yosemite National Park",
            campground_id="2002",
            campground_name="Lower Pines",
            city="Yosemite Valley",
            state="CA",
            country="USA",
            latitude=37.740,
            longitude=-119.568,
            reservable=True,
            has_electric=False,
            pets_allowed=False,
            max_rv_length=24,
        ),
        Search(
            id="Camp/2/3001/4001",
            entity_type="Campground",
            provider_id=2,
            provider_name="usedirect",
            recreation_area_id="3001",
            recreation_area_name="Big Sur State Park",
            campground_id="4001",
            campground_name="Pfeiffer Big Sur Campground",
            city="Big Sur",
            state="CA",
            country="USA",
            latitude=36.248,
            longitude=-121.781,
            reservable=True,
            has_electric=True,
            pets_allowed=True,
            max_rv_length=32,
        ),
        Search(
            id="Camp/1/5001/6001",
            entity_type="Campground",
            provider_id=1,
            provider_name="recreation_dot_gov",
            recreation_area_id="5001",
            recreation_area_name="Rocky Mountain National Park",
            campground_id="6001",
            campground_name="Moraine Park",
            city="Estes Park",
            state="CO",
            country="USA",
            latitude=40.358,
            longitude=-105.597,
            reservable=True,
            has_electric=False,
            pets_allowed=True,
            max_rv_length=40,
        ),
    ]
    for row in rows:
        async_session.add(row)
    await async_session.commit()
    return rows


@pytest.mark.asyncio
async def test_search_by_term_exact_and_prefix(
    async_session: AsyncSession, seeded_search_data: list[Search]
) -> None:
    results, total, facets = await Search.search(
        session=async_session,
        term="Upper Pines",
    )
    assert total >= 1
    assert results[0].campground_name == "Upper Pines"
    assert facets["states"]["CA"] >= 1


@pytest.mark.asyncio
async def test_search_compound_multi_token(
    async_session: AsyncSession, seeded_search_data: list[Search]
) -> None:
    # "Yosemite Upper Pines" crosses rec area name ("Yosemite") and campground name ("Upper Pines")
    results, total, _ = await Search.search(
        session=async_session,
        term="Yosemite Upper Pines",
    )
    assert total == 1
    assert results[0].campground_name == "Upper Pines"


@pytest.mark.asyncio
async def test_search_filters_state_and_amenities(
    async_session: AsyncSession, seeded_search_data: list[Search]
) -> None:
    # Electric campgrounds in CA
    results, total, facets = await Search.search(
        session=async_session,
        state="CA",
        has_electric=True,
    )
    assert total == 2
    campground_names = {r.campground_name for r in results}
    assert "Upper Pines" in campground_names
    assert "Pfeiffer Big Sur Campground" in campground_names
    assert "CA" in facets["states"]


@pytest.mark.asyncio
async def test_search_min_rv_length(
    async_session: AsyncSession, seeded_search_data: list[Search]
) -> None:
    # Campgrounds accommodating RV length >= 35 ft
    results, total, _ = await Search.search(
        session=async_session,
        min_rv_length=35,
        entity_types=["Campground"],
    )
    assert total == 2
    names = {r.campground_name for r in results}
    assert "Upper Pines" in names
    assert "Moraine Park" in names
    assert "Lower Pines" not in names


@pytest.mark.asyncio
async def test_search_geospatial_radius(
    async_session: AsyncSession, seeded_search_data: list[Search]
) -> None:
    # Radius of 15 miles around Yosemite Valley center (37.74, -119.56)
    results, total, _ = await Search.search(
        session=async_session,
        lat=37.74,
        lng=-119.56,
        radius_miles=15.0,
    )
    assert total >= 2
    rec_names = {r.recreation_area_name for r in results}
    assert "Yosemite National Park" in rec_names
    assert "Rocky Mountain National Park" not in rec_names


@pytest.mark.asyncio
async def test_search_pagination_and_sorting(
    async_session: AsyncSession, seeded_search_data: list[Search]
) -> None:
    results, total, _ = await Search.search(
        session=async_session,
        sort_by="name_asc",
        limit=2,
        offset=0,
    )
    assert total == 5
    assert len(results) == 2


@pytest.mark.asyncio
async def test_search_algorithm_backward_compatibility(
    async_session: AsyncSession, seeded_search_data: list[Search]
) -> None:
    items = await Search.algorithm(
        session=async_session,
        term="Moraine",
        limit=10,
    )
    assert len(items) == 1
    assert items[0].campground_name == "Moraine Park"


def test_build_text_search_postgres_compilation() -> None:
    """
    Verify PostgreSQL pg_trgm expressions compile properly with trigram similarity.
    """
    from sqlalchemy import select
    from sqlalchemy.dialects import postgresql

    from db.models.search import _build_text_search

    text_filter, total_score = _build_text_search(
        cls=Search,
        term="yosemitty",
        dialect_name="postgresql",
    )
    assert text_filter is not None
    assert total_score is not None

    stmt = select(Search, total_score).where(text_filter)
    compiled = str(stmt.compile(dialect=postgresql.dialect()))

    assert "to_tsvector(" in compiled
    assert "ts_rank_cd(" in compiled
    assert "@@" in compiled
    assert "%>" in compiled
    assert "word_similarity(" in compiled
    assert "greatest(" in compiled


def test_build_text_search_empty_term() -> None:
    """
    Verify empty search terms return None filter and score.
    """
    from db.models.search import _build_text_search

    text_filter, total_score = _build_text_search(
        cls=Search,
        term="   ",
        dialect_name="postgresql",
    )
    assert text_filter is None
    assert total_score is None


@pytest.mark.asyncio
async def test_search_keeps_short_location_tokens(
    async_session: AsyncSession, seeded_search_data: list[Search]
) -> None:
    """A state token remains required even alongside a campground name."""
    rows, total, _ = await Search.search(session=async_session, term="Pines CO")
    assert rows == []
    assert total == 0


@pytest.mark.asyncio
async def test_search_punctuation_is_not_a_wildcard(
    async_session: AsyncSession, seeded_search_data: list[Search]
) -> None:
    """SQL wildcard punctuation never turns a query into a catalog-wide match."""
    rows, total, _ = await Search.search(session=async_session, term="%_!")
    assert rows == []
    assert total == 0


@pytest.mark.asyncio
async def test_search_false_amenity_filter(
    async_session: AsyncSession, seeded_search_data: list[Search]
) -> None:
    """Explicit negative filters exclude rows that have the selected amenity."""
    rows, total, _ = await Search.search(session=async_session, pets_allowed=False)
    assert total == 1
    assert rows[0].campground_name == "Lower Pines"


@pytest.mark.asyncio
async def test_autocomplete_avoids_aggregate_queries(
    async_session: AsyncSession, seeded_search_data: list[Search]
) -> None:
    """Autocomplete fetches matching rows without counts or facet aggregations."""
    from unittest.mock import AsyncMock, patch

    with patch.object(
        async_session, "execute", new=AsyncMock(wraps=async_session.execute)
    ) as execute:
        rows = await Search.algorithm(session=async_session, term="Pines")
    assert len(rows) == 2
    assert execute.await_count == 1


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "options,expected",
    [
        (
            {
                "state": " ca ",
                "has_electric": False,
                "pets_allowed": False,
                "min_rv_length": 0,
            },
            1,
        ),
        ({"provider_ids": [2]}, 1),
        ({"lat": 0, "radius_miles": 1}, 5),
        ({"term": "Upper Pines"}, 1),
    ],
)
async def test_matching_defaults_survive_predicate_extraction(
    async_session: AsyncSession,
    seeded_search_data: list[Search],
    options: dict,
    expected: int,
) -> None:
    """Preserve explicit false, nonpositive and incomplete-radius semantics."""
    _, total, _ = await Search.search(async_session, **options)
    assert total == expected


@pytest.mark.asyncio
async def test_search_backfill_populates_missing_coordinates(
    async_session: AsyncSession,
) -> None:
    """A search row missing coordinates is populated from its catalog entity."""
    from sqlalchemy import text

    from db.models import Campground, Provider

    provider = Provider(id=99, name="Test", url="https://example.test", enabled=True)
    cg = Campground(
        id="cg-1",
        provider_id=99,
        name="Backfilled Campground",
        state="OR",
        country="USA",
        city="Bend",
        latitude=44.0582,
        longitude=-121.3153,
        reservable=True,
    )
    unpopulated = Search(
        id="Campground/99/cg-1",
        entity_type="Campground",
        provider_id=99,
        provider_name="Test",
        campground_id="cg-1",
        campground_name="Backfilled Campground",
        latitude=None,
        longitude=None,
        city=None,
        state=None,
        country=None,
    )
    async_session.add_all([provider, cg, unpopulated])
    await async_session.commit()

    await async_session.execute(
        text(
            """
            UPDATE search
            SET latitude = (
                    SELECT latitude FROM campgrounds c
                    WHERE c.provider_id = search.provider_id AND c.id = search.campground_id
                ),
                longitude = (
                    SELECT longitude FROM campgrounds c
                    WHERE c.provider_id = search.provider_id AND c.id = search.campground_id
                ),
                city = (
                    SELECT city FROM campgrounds c
                    WHERE c.provider_id = search.provider_id AND c.id = search.campground_id
                ),
                state = (
                    SELECT state FROM campgrounds c
                    WHERE c.provider_id = search.provider_id AND c.id = search.campground_id
                ),
                country = (
                    SELECT country FROM campgrounds c
                    WHERE c.provider_id = search.provider_id AND c.id = search.campground_id
                )
            WHERE entity_type = 'Campground' AND (latitude IS NULL OR longitude IS NULL);
            """
        )
    )
    await async_session.commit()
    await async_session.refresh(unpopulated)

    reloaded = await async_session.get(Search, "Campground/99/cg-1")
    assert reloaded is not None
    assert reloaded.latitude == 44.0582
    assert reloaded.longitude == -121.3153
    assert reloaded.state == "OR"
