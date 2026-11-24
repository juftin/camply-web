"""Exercise destination enrichment migration against isolated SQLite storage."""

import io
import json
import sqlite3
from pathlib import Path

from alembic import command

from camply.db.config import DatabaseConfig, DatabaseDrivers
from camply.db.migration import get_alembic_config, upgrade_database


def test_destination_details_upgrade_and_downgrade_preserve_catalog(
    tmp_path: Path,
) -> None:
    """Existing rows gain nullable snapshots and survive migration round trips."""
    database = DatabaseConfig(HOST=str(tmp_path / "destinations.db"))
    upgrade_database(database, revision="f024d1e2f3a4")
    with sqlite3.connect(database.HOST) as connection:
        for table in ("recreation_areas", "campgrounds"):
            connection.execute(
                f"INSERT INTO {table} (id, provider_id, name, description, reservable, enabled, created_at, updated_at) "
                "VALUES ('synthetic-destination', 1, 'Synthetic destination', 'Existing description', 1, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
            )
    upgrade_database(database)
    snapshot = {
        "source_url": "https://parks.example.com/destination",
        "fetched_at": "2030-01-01T00:00:00Z",
        "photos": [{"url": "https://photos.example.com/photo.jpg"}],
    }
    with sqlite3.connect(database.HOST) as connection:
        for table in ("campgrounds", "recreation_areas"):
            assert connection.execute(
                f"SELECT description, details, details_attempted_at FROM {table} WHERE id='synthetic-destination'"
            ).fetchone() == ("Existing description", None, None)
            connection.execute(
                f"UPDATE {table} SET details=? WHERE id='synthetic-destination'",
                (json.dumps(snapshot),),
            )
    upgrade_database(database)
    with sqlite3.connect(database.HOST) as connection:
        for table in ("campgrounds", "recreation_areas"):
            assert (
                json.loads(
                    connection.execute(
                        f"SELECT details FROM {table} WHERE id='synthetic-destination'"
                    ).fetchone()[0]
                )
                == snapshot
            )
    command.downgrade(
        get_alembic_config(database_config=database), revision="f024d1e2f3a4"
    )
    with sqlite3.connect(database.HOST) as connection:
        for table in ("campgrounds", "recreation_areas"):
            assert {"details", "details_attempted_at"}.isdisjoint(
                {row[1] for row in connection.execute(f"PRAGMA table_info({table})")}
            )
            assert connection.execute(
                f"SELECT name, description FROM {table} WHERE id='synthetic-destination'"
            ).fetchone() == ("Synthetic destination", "Existing description")
    upgrade_database(database)
    with sqlite3.connect(database.HOST) as connection:
        assert connection.execute("PRAGMA foreign_key_check").fetchall() == []
        for table in ("campgrounds", "recreation_areas"):
            assert connection.execute(
                f"SELECT details FROM {table} WHERE id='synthetic-destination'"
            ).fetchone() == (None,)


def test_destination_migration_compiles_for_postgresql() -> None:
    """The isolated revision emits portable PostgreSQL JSON/timestamp DDL offline."""
    output = io.StringIO()
    config = get_alembic_config(
        DatabaseConfig(
            DRIVERNAME=DatabaseDrivers.POSTGRES, HOST="127.0.0.1", DATABASE="synthetic"
        )
    )
    config.output_buffer = output
    command.upgrade(config, revision="f024d1e2f3a4:d027a1b2c3d4", sql=True)
    ddl = output.getvalue()
    for table in ("campgrounds", "recreation_areas"):
        assert f"ALTER TABLE {table} ADD COLUMN details JSON" in ddl
        assert f"ALTER TABLE {table} ADD COLUMN details_attempted_at TIMESTAMP" in ddl
