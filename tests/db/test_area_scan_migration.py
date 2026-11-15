"""Populated upgrades preserve subscriptions and refuse lossy area downgrades."""

import uuid
from pathlib import Path

import pytest
from alembic import command
from sqlalchemy import create_engine, text

from camply.db.config import DatabaseConfig
from camply.db.migration import get_alembic_config


def test_area_upgrade_backfill_and_rollback(tmp_path: Path) -> None:
    """Legacy IDs, pending intents and inbound foreign keys survive round trips."""
    path = tmp_path / "upgrade.db"
    config = get_alembic_config(DatabaseConfig(HOST=str(path)))
    command.upgrade(config, "d027a1b2c3d4")
    engine = create_engine(f"sqlite:///{path}")
    user_id, target_id, scan_id = [uuid.uuid4().hex for _ in range(3)]
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO users (id,email,is_admin,is_early_access_user,scanning_enabled) VALUES (:id,'migration@example.test',0,1,1)"
            ),
            {"id": user_id},
        )
        conn.execute(
            text(
                "INSERT INTO campgrounds (id,provider_id,name,reservable,enabled) VALUES ('migration-029',1,'Migration',1,1)"
            )
        )
        conn.execute(
            text(
                "INSERT INTO unique_targets (id,provider_id,campground_id,start_date,end_date,hash) VALUES (:id,1,'migration-029','2027-07-01','2027-07-04','migration-029')"
            ),
            {"id": target_id},
        )
        conn.execute(
            text(
                "INSERT INTO user_scans (id,user_id,target_id,is_active,min_stay_length,require_electric) VALUES (:id,:user,:target,1,2,0)"
            ),
            {"id": scan_id, "user": user_id, "target": target_id},
        )
        conn.execute(
            text(
                "INSERT INTO scan_results (id,target_id,campsite_id,campsite_name,available_dates) VALUES (:id,:target,'site-1','Site 1','[\"2027-07-01\"]')"
            ),
            {"id": uuid.uuid4().hex, "target": target_id},
        )
        outbox_id = uuid.uuid4().hex
        conn.execute(
            text(
                "INSERT INTO notification_outbox (id,detection_id,delivery_key,channel,scan_id,user_id,target_id,payload,status,attempt_count,next_attempt_at,created_at) "
                "VALUES (:id,:det,'summary:1','pushover',:scan,:user,:target,'{}','pending',0,'2027-07-01 00:00:00','2027-07-01 00:00:00')"
            ),
            {
                "id": outbox_id,
                "det": uuid.uuid4().hex,
                "scan": scan_id,
                "user": user_id,
                "target": target_id,
            },
        )
    command.upgrade(config, "head")
    with engine.begin() as conn:
        row = (
            conn.execute(text("SELECT * FROM user_scans WHERE id=:id"), {"id": scan_id})
            .mappings()
            .one()
        )
        assert row["provider_id"] == 1 and row["destination_name"] == "Migration"
        assert row["min_stay_length"] == 2 and row["target_id"] == target_id
        assert conn.scalar(text("SELECT count(*) FROM scan_targets")) == 1
        assert conn.scalar(text("SELECT count(*) FROM scan_results")) == 1
        assert (
            conn.scalar(
                text("SELECT status FROM notification_outbox WHERE id=:id"),
                {"id": outbox_id},
            )
            == "pending"
        )
        assert not conn.execute(text("PRAGMA foreign_key_check")).all()
    command.downgrade(config, "d027a1b2c3d4")
    command.upgrade(config, "head")
    with engine.begin() as conn:
        conn.execute(
            text("UPDATE notification_outbox SET payload_kind='area' WHERE id=:id"),
            {"id": outbox_id},
        )
    with pytest.raises(RuntimeError, match="delivery intents"):
        command.downgrade(config, "d027a1b2c3d4")
    with engine.begin() as conn:
        conn.execute(
            text(
                "UPDATE notification_outbox SET payload_kind='campground' WHERE id=:id"
            ),
            {"id": outbox_id},
        )
        conn.execute(
            text(
                "UPDATE user_scans SET destination_type='recreation_area', recreation_area_id='unavailable', campground_id=NULL, target_id=NULL, coverage_mode='all' WHERE id=:id"
            ),
            {"id": scan_id},
        )
    with pytest.raises(RuntimeError, match="Area scans"):
        command.downgrade(config, "d027a1b2c3d4")
    engine.dispose()


def test_area_upgrade_rejects_duplicate_campground_scans(tmp_path: Path) -> None:
    """Preflight fails before schema changes when a user has duplicate campground scans."""
    path = tmp_path / "dup.db"
    config = get_alembic_config(DatabaseConfig(HOST=str(path)))
    command.upgrade(config, "d027a1b2c3d4")
    engine = create_engine(f"sqlite:///{path}")
    user_id, target_id = uuid.uuid4().hex, uuid.uuid4().hex
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO users (id,email,is_admin,is_early_access_user,scanning_enabled) VALUES (:id,'dup@example.test',0,1,1)"
            ),
            {"id": user_id},
        )
        conn.execute(
            text(
                "INSERT INTO campgrounds (id,provider_id,name,reservable,enabled) VALUES ('dup-cg',1,'Dup',1,1)"
            )
        )
        conn.execute(
            text(
                "INSERT INTO unique_targets (id,provider_id,campground_id,start_date,end_date,hash) VALUES (:id,1,'dup-cg','2027-07-01','2027-07-04','dup-hash')"
            ),
            {"id": target_id},
        )
        for scan_id in (uuid.uuid4().hex, uuid.uuid4().hex):
            conn.execute(
                text(
                    "INSERT INTO user_scans (id,user_id,target_id,is_active,min_stay_length,require_electric) VALUES (:id,:user,:target,1,1,0)"
                ),
                {"id": scan_id, "user": user_id, "target": target_id},
            )
    with pytest.raises(RuntimeError, match="Duplicate campground scan definitions"):
        command.upgrade(config, "head")
    with engine.begin() as conn:
        cols = {
            row["name"]
            for row in conn.execute(text("PRAGMA table_info(user_scans)")).mappings()
        }
        assert "destination_type" not in cols
    engine.dispose()
