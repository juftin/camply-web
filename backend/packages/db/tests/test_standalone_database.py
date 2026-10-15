"""Exercise real migrations and SQLite connection invariants on local files."""

import asyncio
import datetime as dt
import sqlite3
import time
from pathlib import Path

import pytest
from sqlalchemy import text
from sqlalchemy.exc import OperationalError

from db.config import DatabaseConfig
from db.migrate import upgrade_database
from db.models import Campground, ScanResult, UniqueTarget, User, UserScan


@pytest.mark.asyncio
async def test_sqlite_connection_policy(tmp_path: Path) -> None:
    """Every local connection enforces references and uses bounded contention."""
    database = DatabaseConfig(HOST=str(tmp_path / "state.db"))
    engine = database.create_async_engine()
    try:
        async with engine.connect() as connection:
            assert await connection.scalar(text("PRAGMA foreign_keys")) == 1
            assert await connection.scalar(text("PRAGMA journal_mode")) == "wal"
            assert 0 < await connection.scalar(text("PRAGMA busy_timeout")) <= 1000
        assert engine.url.database == str(tmp_path / "state.db")
    finally:
        await engine.dispose()


def test_fresh_and_populated_upgrade(tmp_path: Path) -> None:
    """Apply the complete revision graph and repeat without losing saved rows."""
    database = DatabaseConfig(HOST=str(tmp_path / "state.db"))
    upgrade_database(database)
    with sqlite3.connect(database.HOST) as connection:
        before = connection.execute(
            "SELECT id, name FROM providers ORDER BY id"
        ).fetchall()
        assert before
        assert connection.execute("PRAGMA foreign_key_check").fetchall() == []
    upgrade_database(database)
    with sqlite3.connect(database.HOST) as connection:
        assert (
            connection.execute("SELECT id, name FROM providers ORDER BY id").fetchall()
            == before
        )


def test_populated_upgrade_and_online_backup(tmp_path: Path) -> None:
    """Preserve linked UUID/JSON/date state across an upgrade and online backup."""
    database = DatabaseConfig(HOST=str(tmp_path / "state.db"))
    upgrade_database(database, revision="9b2c3d4e5f6a")

    async def seed() -> tuple[str, str]:
        """Populate an old revision using the same ORM mappings as the app."""
        database.open()
        try:
            async with database.get_session() as session:
                session.add(
                    Campground(id="synthetic", provider_id=1, name="Synthetic park")
                )
                await session.flush()
                user = User(email="synthetic@example.test")
                session.add(user)
                target = UniqueTarget(
                    provider_id=1,
                    campground_id="synthetic",
                    start_date=dt.date(2027, 1, 1),
                    end_date=dt.date(2027, 1, 3),
                )
                session.add(target)
                await session.flush()
                session.add(
                    UserScan(
                        user_id=user.id, target_id=target.id, preferred_types=["TENT"]
                    )
                )
                session.add(
                    ScanResult(
                        target_id=target.id,
                        campsite_id="synthetic",
                        available_dates=["2027-01-01"],
                    )
                )
                await session.commit()
                return str(user.id), str(target.id)
        finally:
            await database.close()

    user_id, target_id = asyncio.run(seed())
    upgrade_database(database)
    backup_path = tmp_path / "backup.db"
    with (
        sqlite3.connect(database.HOST) as source,
        sqlite3.connect(backup_path) as backup,
    ):
        source.backup(backup)
    with sqlite3.connect(backup_path) as connection:
        assert connection.execute("PRAGMA foreign_key_check").fetchall() == []
        assert connection.execute("SELECT COUNT(*) FROM user_scans").fetchone() == (1,)
        assert connection.execute(
            "SELECT COUNT(*) FROM notification_outbox"
        ).fetchone() == (0,)
    restored = DatabaseConfig(HOST=str(backup_path))
    upgrade_database(restored)

    async def verify() -> None:
        """Read restored values through their production type conversions."""
        from uuid import UUID

        from sqlalchemy import select

        restored.open()
        try:
            async with restored.get_session() as session:
                assert await session.get(User, UUID(user_id)) is not None
                target = await session.get(UniqueTarget, UUID(target_id))
                assert target is not None and target.start_date == dt.date(2027, 1, 1)
                scan = (await session.scalars(select(UserScan))).one()
                result = (await session.scalars(select(ScanResult))).one()
                assert scan.preferred_types == ["TENT"]
                assert result.available_dates == ["2027-01-01"]
        finally:
            await restored.close()

    asyncio.run(verify())


@pytest.mark.asyncio
async def test_wal_reader_responds_during_write_contention(tmp_path: Path) -> None:
    """Readers stay responsive and contending writes fail within the busy timeout."""
    database = DatabaseConfig(HOST=str(tmp_path / "contention.db"))
    engine = database.create_async_engine()
    try:
        async with engine.begin() as connection:
            await connection.execute(text("CREATE TABLE synthetic (value INTEGER)"))
        async with engine.connect() as writer:
            await writer.execute(text("BEGIN IMMEDIATE"))
            await writer.execute(text("INSERT INTO synthetic VALUES (1)"))
            started = time.monotonic()
            async with engine.connect() as reader:
                assert await reader.scalar(text("SELECT COUNT(*) FROM synthetic")) == 0
            assert time.monotonic() - started < 2
            started = time.monotonic()
            async with engine.connect() as contender:
                with pytest.raises(OperationalError):
                    await contender.execute(text("INSERT INTO synthetic VALUES (2)"))
            assert time.monotonic() - started < 2
            await writer.rollback()
    finally:
        await engine.dispose()
