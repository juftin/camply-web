"""Opt-in real PostgreSQL search and migration regressions with synthetic data."""

from __future__ import annotations

import os
import subprocess
import sys
import time
from collections.abc import AsyncGenerator, Generator
from pathlib import Path
from typing import Any

import psycopg
import pytest
import pytest_asyncio
from sqlalchemy import select, text
from sqlalchemy.dialects import postgresql
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from camply.db.models import Search
from camply.db.models.search import _build_postgres_text_search

pytestmark = pytest.mark.skipif(
    os.environ.get("CAMPLY_POSTGRES_SEARCH_TEST") != "1", reason="Run task search:smoke"
)


@pytest.fixture(scope="module")
def postgres_url() -> Generator[str, None, None]:
    """Migrate an isolated test-owned PostgreSQL container and always remove it."""
    container = subprocess.run(
        [
            "docker",
            "run",
            "--detach",
            "--rm",
            "--publish",
            "127.0.0.1::5432",
            "--env",
            "POSTGRES_PASSWORD=synthetic-search-key",
            "postgres:17",
        ],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    try:
        port = (
            subprocess.run(
                ["docker", "port", container, "5432/tcp"],
                check=True,
                capture_output=True,
                text=True,
            )
            .stdout.strip()
            .rsplit(":", 1)[1]
        )
        url = f"postgresql://postgres:synthetic-search-key@127.0.0.1:{port}/postgres"
        deadline = time.monotonic() + 30
        while True:
            try:
                with psycopg.connect(url):
                    break
            except psycopg.OperationalError:
                if time.monotonic() >= deadline:
                    raise
                time.sleep(0.2)
        env = {
            **os.environ,
            "CAMPLY_DB_DRIVERNAME": "postgresql+psycopg",
            "CAMPLY_DB_HOST": "127.0.0.1",
            "CAMPLY_DB_PORT": port,
            "CAMPLY_DB_USERNAME": "postgres",
            "CAMPLY_DB_PASSWORD": "synthetic-search-key",
            "CAMPLY_DB_DATABASE": "postgres",
        }
        db_dir = Path(__file__).resolve().parents[2]
        for args in (["upgrade", "head"], ["downgrade", "-1"], ["upgrade", "head"]):
            subprocess.run(
                [sys.executable, "-m", "alembic", *args],
                cwd=db_dir,
                env=env,
                check=True,
                capture_output=True,
                text=True,
            )
        yield url.replace("postgresql://", "postgresql+psycopg://")
    finally:
        subprocess.run(
            ["docker", "rm", "--force", container], check=False, capture_output=True
        )


@pytest_asyncio.fixture
async def postgres_session(postgres_url: str) -> AsyncGenerator[AsyncSession, None]:
    """Seed synthetic discovery rows in a transaction rolled back after each test."""
    engine = create_async_engine(postgres_url)
    try:
        async with AsyncSession(engine) as session:
            rows: list[dict[str, Any]] = [
                {
                    "id": "area",
                    "entity_type": "RecreationArea",
                    "provider_id": 1,
                    "recreation_area_name": "Juniper National Park",
                    "campground_name": None,
                    "state": "CA",
                    "has_electric": False,
                },
                {
                    "id": "upper",
                    "entity_type": "Campground",
                    "provider_id": 1,
                    "recreation_area_name": "Juniper National Park",
                    "campground_name": "Upper Pines",
                    "state": "CA",
                    "has_electric": True,
                },
                {
                    "id": "lower",
                    "entity_type": "Campground",
                    "provider_id": 1,
                    "recreation_area_name": "Juniper National Park",
                    "campground_name": "Lower Pines",
                    "state": "CA",
                    "has_electric": False,
                },
                {
                    "id": "exact",
                    "entity_type": "Campground",
                    "provider_id": 2,
                    "recreation_area_name": "Other Park",
                    "campground_name": "Juniper",
                    "state": "CO",
                    "has_electric": True,
                },
                {
                    "id": "tie-a",
                    "entity_type": "Campground",
                    "provider_id": 2,
                    "recreation_area_name": "Other Park",
                    "campground_name": "Twin Pines",
                    "state": "CO",
                    "has_electric": False,
                },
                {
                    "id": "tie-b",
                    "entity_type": "Campground",
                    "provider_id": 2,
                    "recreation_area_name": "Other Park",
                    "campground_name": "Twin Pines",
                    "state": "CO",
                    "has_electric": False,
                },
            ]
            await session.execute(
                text("""
                INSERT INTO search (id, entity_type, provider_id, provider_name,
                    recreation_area_name, campground_name, city, state, has_electric)
                VALUES (:id, :entity_type, :provider_id, 'synthetic_provider',
                    :recreation_area_name, :campground_name, 'Pine Valley', :state, :has_electric)
                """),
                rows,
            )
            yield session
            await session.rollback()
    finally:
        await engine.dispose()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "term", ["Junipr Uper Pines", "Juniper Upper Pin", "Juniper, Upper Pines!"]
)
async def test_cross_field_typo_and_prefix(
    postgres_session: AsyncSession, term: str
) -> None:
    """All words match across parent/campground fields, including typos and prefixes."""
    rows, total, facets = await Search.search(session=postgres_session, term=term)
    assert [row.id for row in rows] == ["upper"]
    assert total == 1
    assert facets["states"] == {"CA": 1}


@pytest.mark.asyncio
async def test_exact_display_name_beats_parent_match(
    postgres_session: AsyncSession,
) -> None:
    """An exact campground name ranks above park-name and inherited matches."""
    rows, _, _ = await Search.search(session=postgres_session, term="Juniper")
    assert rows[0].id == "exact"


@pytest.mark.asyncio
@pytest.mark.parametrize("term", ["Juniper nonexistent", "Pines CO CA", "%_!"])
async def test_every_token_required(postgres_session: AsyncSession, term: str) -> None:
    """Fuzzy matching cannot discard restrictive words or short state codes."""
    rows, total, _ = await Search.search(session=postgres_session, term=term)
    assert rows == []
    assert total == 0


@pytest.mark.asyncio
async def test_filters_facets_and_stable_pagination(
    postgres_session: AsyncSession,
) -> None:
    """Provider/amenity filters and exact facets apply before stable pagination."""
    rows, total, facets = await Search.search(
        session=postgres_session,
        term="Pines",
        provider_ids=[2],
        has_electric=False,
        limit=1,
        offset=1,
        sort_by="name_asc",
    )
    assert [row.id for row in rows] == ["tie-b"]
    assert total == 2
    assert facets["states"] == {"CO": 2}
    assert facets["entity_types"] == {"Campground": 2}


@pytest.mark.asyncio
async def test_indexes_support_candidates(postgres_session: AsyncSession) -> None:
    """The planner chooses GIN across 20,000 rows without disabling table scans."""
    await postgres_session.execute(
        text("""
        INSERT INTO search (id, entity_type, provider_id, provider_name,
            campground_name, city, state)
        SELECT 'filler-' || n, 'Campground', 9, 'synthetic_provider',
            'Remote Meadow ' || n, 'Faraway', 'TX'
        FROM generate_series(1, 20000) AS n
        """)
    )
    await postgres_session.execute(text("ANALYZE search"))
    filters, _ = _build_postgres_text_search(cls=Search, term_cleaned="junipr")
    statement = select(Search.id).where(filters)
    sql = str(
        statement.compile(
            dialect=postgresql.dialect(paramstyle="named"),
            compile_kwargs={"literal_binds": True},
        )
    )
    plan = "\n".join((await postgres_session.execute(text(f"EXPLAIN {sql}"))).scalars())
    assert "ix_search_text_vector" in plan
    assert "ix_search_campground_trgm" in plan
    assert "ix_search_rec_area_trgm" in plan
    assert "ix_search_city_trgm" in plan
