"""Exercise real migrations and SQLite connection invariants on local files."""

import asyncio
import datetime as dt
import json
import sqlite3
import time
import uuid
from pathlib import Path

import pytest
from sqlalchemy import text
from sqlalchemy.exc import OperationalError

from camply.db.config import DatabaseConfig
from camply.db.migration import upgrade_database
from camply.db.models import ScanResult, UniqueTarget, User, UserScan


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


def test_previous_pr_database_preserves_pending_delivery(tmp_path: Path) -> None:
    """Upgrade the earlier PR schema and its pending payload through the merge head."""
    database = DatabaseConfig(HOST=str(tmp_path / "previous-pr.db"))
    upgrade_database(database, revision="ef2486672984")
    payload = json.dumps(
        {
            "title": "Synthetic opening",
            "message": "Synthetic pending alert",
            "booking_url": "https://example.test/book",
            "park_name": "Synthetic park",
            "campsite_name": "Synthetic site",
            "start_date": "2027-01-01",
            "end_date": "2027-01-02",
            "metadata": {
                "campsite_id": "synthetic",
                "campsite_type": "TENT",
                "is_electric": False,
                "available_dates": ["2027-01-01"],
            },
        }
    )
    with sqlite3.connect(database.HOST) as connection:
        connection.execute(
            "INSERT INTO notification_outbox (id, detection_id, campsite_id, payload, status, attempt_count, next_attempt_at, created_at) VALUES (?, ?, ?, ?, 'pending', 0, ?, ?)",
            (
                "a" * 32,
                "b" * 32,
                "synthetic",
                payload,
                "2027-01-01 00:00:00",
                "2027-01-01 00:00:00",
            ),
        )
    upgrade_database(database)
    with sqlite3.connect(database.HOST) as connection:
        row = connection.execute(
            "SELECT delivery_key, payload, status, attempt_count FROM notification_outbox"
        ).fetchone()
        assert row == ("synthetic", payload, "pending", 0)
        columns = {
            row[1] for row in connection.execute("PRAGMA table_info(scan_results)")
        }
        assert {
            "campsite_name",
            "campsite_type",
            "is_electric",
            "is_accessible",
        } <= columns
        assert connection.execute("PRAGMA foreign_key_check").fetchall() == []
        assert connection.execute(
            "SELECT version_num FROM alembic_version"
        ).fetchall() == [("d834b6f82260",)]


async def _seed_historical_scan(database: DatabaseConfig) -> tuple[str, str]:
    """Populate an old revision with historical schema columns."""
    database.open()
    try:
        async with database.get_session() as session:
            await session.execute(
                text(
                    "INSERT INTO campgrounds (id, provider_id, name, reservable, enabled) "
                    "VALUES ('synthetic', 1, 'Synthetic park', 1, 1)"
                )
            )
            user_id = uuid.uuid4()
            await session.execute(
                text(
                    "INSERT INTO users (id, email, is_early_access_user, is_admin, scanning_enabled, must_change_password) "
                    "VALUES (:id, 'synthetic@example.test', 0, 0, 1, 0)"
                ),
                {"id": user_id.hex},
            )
            target_id_uuid = uuid.uuid4()
            target_hash = UniqueTarget.calculate_hash(
                1, "synthetic", dt.date(2027, 1, 1), dt.date(2027, 1, 3)
            )
            await session.execute(
                text(
                    "INSERT INTO unique_targets (id, provider_id, campground_id, start_date, end_date, hash) "
                    "VALUES (:id, 1, 'synthetic', '2027-01-01', '2027-01-03', :hash)"
                ),
                {"id": target_id_uuid.hex, "hash": target_hash},
            )
            scan_id_uuid = uuid.uuid4()
            await session.execute(
                text(
                    "INSERT INTO user_scans (id, user_id, target_id, is_active, min_stay_length, preferred_types, require_electric) "
                    "VALUES (:id, :user_id, :target_id, 1, 1, :preferred_types, 0)"
                ),
                {
                    "id": scan_id_uuid.hex,
                    "user_id": user_id.hex,
                    "target_id": target_id_uuid.hex,
                    "preferred_types": json.dumps(["TENT"]),
                },
            )
            await session.execute(
                text(
                    "INSERT INTO scan_results (id, target_id, campsite_id, available_dates) "
                    "VALUES (:id, :target_id, 'synthetic', :available_dates)"
                ),
                {
                    "id": uuid.uuid4().hex,
                    "target_id": target_id_uuid.hex,
                    "available_dates": json.dumps(["2027-01-01"]),
                },
            )
            await session.commit()
            return str(user_id), str(target_id_uuid)
    finally:
        await database.close()


def test_populated_upgrade_and_online_backup(tmp_path: Path) -> None:
    """Preserve linked UUID/JSON/date state across an upgrade and online backup."""
    database = DatabaseConfig(HOST=str(tmp_path / "state.db"))
    upgrade_database(database, revision="09367969f1a4")
    user_id, target_id = asyncio.run(_seed_historical_scan(database))
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
