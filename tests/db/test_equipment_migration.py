"""Populated upgrade, constraint, and downgrade regressions for equipment metadata."""

import uuid
from pathlib import Path

import pytest
from alembic import command
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import IntegrityError

from camply.db.config import DatabaseConfig
from camply.db.migration import get_alembic_config


def test_equipment_upgrade_preserves_existing_rows_and_round_trips(
    tmp_path: Path,
) -> None:
    """Upgrading from 2d7ab29d3a46 preserves existing rows and supports clean downgrade."""
    path = tmp_path / "equipment.db"
    config = get_alembic_config(DatabaseConfig(HOST=str(path)))
    command.upgrade(config, "2d7ab29d3a46")
    engine = create_engine(f"sqlite:///{path}")
    user_id = uuid.uuid4().hex
    target_id = uuid.uuid4().hex
    scan_id = uuid.uuid4().hex
    result_id = uuid.uuid4().hex
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO users (id,email,is_admin,is_early_access_user,scanning_enabled) "
                "VALUES (:id,'equip@example.test',0,1,1)"
            ),
            {"id": user_id},
        )
        conn.execute(
            text(
                "INSERT INTO campgrounds (id,provider_id,name,reservable,enabled) "
                "VALUES ('cg-030',1,'Legacy Camp',1,1)"
            )
        )
        conn.execute(
            text(
                "INSERT INTO unique_targets (id,provider_id,campground_id,start_date,end_date,hash) "
                "VALUES (:id,1,'cg-030','2027-07-01','2027-07-04','hash-030')"
            ),
            {"id": target_id},
        )
        conn.execute(
            text(
                "INSERT INTO user_scans "
                "(id,user_id,target_id,destination_type,provider_id,campground_id,destination_name,"
                "selected_campgrounds,start_date,end_date,definition_hash,is_active,min_stay_length,require_electric) "
                "VALUES (:id,:user,:target,'campground',1,'cg-030','Legacy Camp','[]',"
                "'2027-07-01','2027-07-04','def-030',1,1,0)"
            ),
            {"id": scan_id, "user": user_id, "target": target_id},
        )
        conn.execute(
            text(
                "INSERT INTO scan_results (id,target_id,campsite_id,campsite_name,available_dates) "
                "VALUES (:id,:target,'site-1','Site 1','[\"2027-07-01\"]')"
            ),
            {"id": result_id, "target": target_id},
        )

    command.upgrade(config, "head")
    with engine.connect() as conn:
        inspector = inspect(conn)
        cg_cols = {col["name"] for col in inspector.get_columns("campgrounds")}
        assert {
            "campsite_types",
            "has_electric",
            "has_water",
            "has_sewer",
            "pets_allowed",
            "ada_accessible",
            "max_rv_length",
        } <= cg_cols
        sr_cols = {col["name"] for col in inspector.get_columns("scan_results")}
        assert {"permitted_equipment", "max_vehicle_length"} <= sr_cols
        us_cols = {col["name"] for col in inspector.get_columns("user_scans")}
        assert {"min_rv_length", "require_accessible"} <= us_cols

        scan_row = conn.execute(
            text(
                "SELECT min_rv_length, require_accessible FROM user_scans WHERE id = :id"
            ),
            {"id": scan_id},
        ).one()
        assert tuple(scan_row) == (None, 0)

        sr_row = conn.execute(
            text(
                "SELECT permitted_equipment, max_vehicle_length FROM scan_results WHERE id = :id"
            ),
            {"id": result_id},
        ).one()
        assert tuple(sr_row) == (None, None)

    for bad_length in (0, -5, 201):
        with pytest.raises(IntegrityError):
            with engine.begin() as conn:
                conn.execute(
                    text(
                        "INSERT INTO user_scans "
                        "(id,user_id,target_id,destination_type,provider_id,campground_id,destination_name,"
                        "selected_campgrounds,start_date,end_date,definition_hash,is_active,min_stay_length,require_electric,min_rv_length) "
                        "VALUES (:id,:user,:target,'campground',1,'cg-030','Legacy Camp','[]',"
                        "'2027-07-01','2027-07-04',:def_hash,1,1,0,:min_rv)"
                    ),
                    {
                        "id": uuid.uuid4().hex,
                        "user": user_id,
                        "target": target_id,
                        "def_hash": f"bad-{bad_length}",
                        "min_rv": bad_length,
                    },
                )

    command.downgrade(config, "2d7ab29d3a46")
    with engine.connect() as conn:
        inspector = inspect(conn)
        assert "min_rv_length" not in {
            col["name"] for col in inspector.get_columns("user_scans")
        }
        assert "max_vehicle_length" not in {
            col["name"] for col in inspector.get_columns("scan_results")
        }
        assert "max_rv_length" not in {
            col["name"] for col in inspector.get_columns("campgrounds")
        }
    engine.dispose()
