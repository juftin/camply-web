"""Opt-in map parity and query measurements on a disposable PostgreSQL instance."""

from __future__ import annotations

import asyncio
import json
import os
import secrets
import subprocess
import time
from pathlib import Path
from typing import Any, cast

import pytest
from sqlalchemy import Table, text
from sqlalchemy.engine import URL, Connection
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from db.models import Base, Search
from db.search_maps import Bounds, map_features, map_members, map_summary

pytestmark = pytest.mark.skipif(
    os.environ.get("CAMPLY_MAPS_POSTGRES") != "1",
    reason="Run task backend:maps:test-postgres",
)


def _create_catalog(connection: Connection) -> None:
    """Create the unchanged catalog schema without unrelated account tables."""
    Base.metadata.create_all(bind=connection, tables=[cast(Table, Search.__table__)])


async def _verify_viewport(session: AsyncSession) -> None:
    """Keep list counts, pages and facets consistent with real PostgreSQL map queries."""
    bounds = Bounds(west=-3, east=3, south=-2, north=2)
    rows, total, facets = await Search.search(
        session=session, bounds=bounds, limit=20, offset=20, has_electric=True
    )
    visible = await map_features(
        session, bounds=bounds, zoom=8, filters={"has_electric": True}
    )
    assert len(rows) == 20
    assert total == sum(cell.count for cell in visible.cells)
    assert 65 <= total < 2500
    assert facets["states"] == {"CA": total}


async def _verify(port: int, password: str) -> None:
    """Exercise actual fuzzy matching, circular aggregation, cells and cursors."""
    url = URL.create(
        "postgresql+psycopg",
        username="fixture",
        password=password,
        host="127.0.0.1",
        port=port,
        database="maps",
    )
    engine = create_async_engine(url)
    try:
        for attempt in range(100):
            try:
                async with engine.begin() as connection:
                    await connection.execute(
                        text("CREATE EXTENSION IF NOT EXISTS pg_trgm")
                    )
                    await connection.run_sync(_create_catalog)
                break
            except (OSError, OperationalError):
                if attempt == 99:
                    raise
                await asyncio.sleep(0.1)
        async with async_sessionmaker(engine, expire_on_commit=False)() as session:
            session.add_all(
                [
                    Search(
                        id=f"Camp/{i % 2 + 1}/area/{i:05}",
                        entity_type="Campground",
                        provider_id=i % 2 + 1,
                        provider_name="Fixture",
                        campground_id=f"{i:05}",
                        campground_name="Synthetic Pines",
                        recreation_area_id="area",
                        recreation_area_name="Fixture Park",
                        latitude=1.0 if i < 130 else (i % 170) - 85.0,
                        longitude=1.0 if i < 130 else (i * 1.37) % 360 - 180,
                        has_electric=i % 2 == 0,
                        state="CA",
                    )
                    for i in range(5000)
                ]
            )
            await session.commit()
            start = time.perf_counter()
            summary = await map_summary(session, filters={"term": "synthetic pines"})
            assert summary.total == summary.mappable_total == 5000
            world = Bounds(west=-180, south=-90, east=180, north=90)
            features = await map_features(session, bounds=world, zoom=19, filters={})
            assert len(features.cells) <= 512
            assert sum(cell.count for cell in features.cells) == 5000
            ids: set[str] = set()
            for cell in features.cells:
                cursor = None
                while True:
                    page = await map_members(
                        session,
                        bounds=world,
                        cell_id=cell.cell_id,
                        filters={},
                        page_size=100,
                        after_id=cursor,
                    )
                    assert page.total == cell.count and len(page.items) <= 100
                    ids.update(item.id for item in page.items)
                    cursor = page.next_cursor
                    if cursor is None:
                        break
            assert len(ids) == 5000
            cases: list[dict[str, Any]] = [
                {"term": "synthetik pines"},
                {"has_electric": True},
                {"has_electric": False},
                {"state": "ca", "provider_ids": [2]},
                {"min_rv_length": 1},
            ]
            for filters in cases:
                await session.execute(
                    text("SET LOCAL pg_trgm.word_similarity_threshold = 0.9")
                )
                map_total = (await map_summary(session, filters=filters)).total
                _, total, _ = await Search.search(session, limit=1, **filters)
                assert map_total == total
                if filters.get("term"):
                    assert total == 5000
            await _verify_viewport(session)
            plan: Any = (
                await session.execute(
                    text(
                        "EXPLAIN (ANALYZE, FORMAT JSON) SELECT count(*) FROM search WHERE latitude BETWEEN -90 AND 90 AND longitude BETWEEN -180 AND 180"
                    )
                )
            ).scalar_one()
            destination = (
                Path(__file__).resolve().parents[5] / "frontend/tmp/maps-postgres.json"
            )
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(
                json.dumps(
                    {
                        "matches": 5000,
                        "discovered": len(ids),
                        "features": len(features.cells),
                        "verification_seconds": time.perf_counter() - start,
                        "query_plan": plan,
                    },
                    indent=2,
                )
            )
    finally:
        await engine.dispose()


def test_maps_postgres() -> None:
    """Start and remove only a test-owned PostgreSQL container; never use operator DBs."""
    password = secrets.token_urlsafe(24)
    result = subprocess.run(
        [
            "docker",
            "run",
            "--detach",
            "--rm",
            "--publish",
            "127.0.0.1::5432",
            "--env",
            "POSTGRES_USER=fixture",
            "--env",
            "POSTGRES_DB=maps",
            "--env",
            "POSTGRES_PASSWORD",
            "postgres:17-alpine",
        ],
        env={**os.environ, "POSTGRES_PASSWORD": password},
        check=True,
        capture_output=True,
        text=True,
    )
    container = result.stdout.strip()
    try:
        published = subprocess.check_output(
            ["docker", "port", container, "5432"], text=True
        )
        asyncio.run(_verify(int(published.strip().rsplit(":", 1)[1]), password))
    finally:
        subprocess.run(
            ["docker", "rm", "--force", container], check=False, capture_output=True
        )
