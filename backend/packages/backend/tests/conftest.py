"""
camply-backend test fixtures.

Starts a fresh file-based SQLite database for all tests by overriding the
FastAPI DB dependency with an ``AsyncSession`` backed by a temp-file engine.

A file-based DB is used (rather than :memory:) so that data seeded from one
event loop is visible to connections opened by other event loops (the
``TestClient`` runs its own event loop).
"""

from __future__ import annotations

import asyncio
import os
import tempfile
from collections.abc import AsyncGenerator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from backend.app import app as real_app
from db.config import db
from db.models import Base

# ---------------------------------------------------------------------------
# Temp-file database — shared across all tests (file-based so event-loop-safe)
# ---------------------------------------------------------------------------

_db_fd, _db_path_str = tempfile.mkstemp(suffix="_camply_test.db")
os.close(_db_fd)
_db_path = Path(_db_path_str)
_db_uri = f"sqlite+aiosqlite:///{_db_path}"

engine = create_async_engine(_db_uri, echo=False)
maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def _create_tables() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


asyncio.run(_create_tables())

# ── Seed base data shared across all backend router tests ──────────────────


def _seed_base_data() -> None:
    """Insert seed Provider / RecArea / Campground rows shared by many endpoint tests."""
    from sqlalchemy import select as sa_select

    from db.models import Campground, Provider, RecreationArea

    async def _seed() -> None:
        async with maker() as session:
            # Guard — only seed once
            if (
                await session.execute(sa_select(Provider).limit(1))
            ).scalar_one_or_none():
                return
            session.add_all(
                [
                    Provider(
                        id=1,
                        name="Recreation.gov",
                        description="US Recreation.gov",
                        url="https://recreation.gov",
                        enabled=True,
                    ),
                    Provider(
                        id=2,
                        name="Disabled Provider",
                        url="https://disabled.example.com",
                        enabled=False,
                    ),
                    RecreationArea(
                        id="rec_area_1",
                        provider_id=1,
                        name="Test Recreation Area",
                        country="US",
                        state="CA",
                        reservable=True,
                        enabled=True,
                    ),
                    Campground(
                        id="cg_1",
                        provider_id=1,
                        recreation_area_id="rec_area_1",
                        name="Test Campground",
                        country="US",
                        state="CA",
                        reservable=True,
                        enabled=True,
                    ),
                    Campground(
                        id="cg_non_reservable",
                        provider_id=1,
                        recreation_area_id="rec_area_1",
                        name="Non Reservable Campground",
                        country="US",
                        state="CA",
                        reservable=False,
                        enabled=True,
                    ),
                ]
            )
            await session.commit()

    asyncio.run(_seed())


_seed_base_data()


# ---------------------------------------------------------------------------
# Override FastAPI's DB dependency
# ---------------------------------------------------------------------------


async def _override_session() -> AsyncGenerator[AsyncSession, None]:
    async with maker() as session:
        yield session


real_app.dependency_overrides[db.yield_session] = _override_session


# ---------------------------------------------------------------------------
# Helpers — used by test files via ``conftest.engine`` / ``conftest.maker``
# ---------------------------------------------------------------------------


def seed_data(add_rows: list) -> None:
    """Add rows to the database and commit.

    Usage::

        from db.models import Provider
        from conftest import seed_data

        seed_data(add_rows=[
            Provider(id=1, name="Rec.gov", url="https://recreation.gov"),
        ])
    """

    async def _seed() -> None:
        async with maker() as session:
            for row in add_rows:
                session.add(row)
            await session.commit()

    asyncio.run(_seed())


# ---------------------------------------------------------------------------
# Test fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def anyio_backend() -> str:
    """Limit anyio to asyncio backend only (trio is not installed)."""
    return "asyncio"


@pytest.fixture
def test_client() -> TestClient:
    """Synchronous FastAPI TestClient wired to the temp-file DB."""
    return TestClient(real_app)


# ---------------------------------------------------------------------------
# Cleanup after all tests
# ---------------------------------------------------------------------------


def pytest_unconfigure() -> None:
    """Remove the temp database."""
    try:
        _db_path.unlink(missing_ok=True)
    except OSError:
        pass
