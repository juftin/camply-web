"""Exercise the packaged migration history independently of checkout paths."""

import sqlite3
from pathlib import Path

import pytest
from alembic import command
from alembic.script import ScriptDirectory
from sqlalchemy import inspect

from camply.db.config import DatabaseConfig, DatabaseDrivers
from camply.db.migration import (
    delete_database,
    drop_all_tables,
    get_alembic_config,
    upgrade_database,
)


def test_migration_config_uses_packaged_history() -> None:
    """Runtime configuration finds the unchanged graph without developer hooks."""
    config = get_alembic_config()
    scripts = ScriptDirectory.from_config(config)
    assert scripts.get_heads() == ["f024a1b2c3d4"]
    assert len(list(scripts.walk_revisions())) == 19
    assert config.config_file_name is None
    assert config.get_section("post_write_hooks") is None
    assert (Path(scripts.dir) / "env.py").is_file()
    assert (Path(scripts.dir) / "script.py.mako").is_file()


@pytest.mark.parametrize("earlier_revision", [None, "067d9d721253"])
def test_migration_upgrade_is_cwd_independent(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    earlier_revision: str | None,
) -> None:
    """Fresh and previously versioned SQLite databases upgrade from another cwd."""
    database_file = tmp_path / "synthetic.sqlite"
    config = get_alembic_config(
        DatabaseConfig(
            DRIVERNAME=DatabaseDrivers.SQLITE,
            HOST=f"/{database_file}",
        )
    )
    monkeypatch.chdir(tmp_path)
    if earlier_revision:
        command.upgrade(config, revision=earlier_revision)
        with sqlite3.connect(database_file) as connection:
            connection.execute(
                "INSERT INTO providers (id, name, url, enabled) VALUES (?, ?, ?, ?)",
                (999, "Synthetic provider", "https://synthetic.example.test", True),
            )
    command.upgrade(config, revision="head")
    with sqlite3.connect(database_file) as connection:
        assert connection.execute(
            "SELECT version_num FROM alembic_version"
        ).fetchone() == ("f024a1b2c3d4",)
        if earlier_revision:
            assert connection.execute(
                "SELECT name FROM providers WHERE id = 999"
            ).fetchone() == ("Synthetic provider",)


def test_drop_all_tables_removes_schema_and_migration_state(
    tmp_path: Path,
) -> None:
    """Allow a later migration to rebuild a fully deleted database schema."""
    import asyncio

    database = DatabaseConfig(
        DRIVERNAME=DatabaseDrivers.SQLITE,
        HOST=f"/{tmp_path / 'reset.db'}",
    )
    upgrade_database(database)

    asyncio.run(drop_all_tables(database))

    async def get_tables() -> list[str]:
        engine = database.create_async_engine()
        try:
            async with engine.connect() as connection:
                return await connection.run_sync(
                    lambda sync_connection: inspect(sync_connection).get_table_names()
                )
        finally:
            await engine.dispose()

    assert asyncio.run(get_tables()) == []

    upgrade_database(database)
    assert {"alembic_version", "providers", "users", "user_scans"} <= set(
        asyncio.run(get_tables())
    )


@pytest.mark.asyncio
async def test_delete_database_removes_sqlite_file_and_sidecars(
    tmp_path: Path,
) -> None:
    """Remove every file that preserves a deleted SQLite database state."""
    database_path = tmp_path / "camply.db"
    database = DatabaseConfig(
        DRIVERNAME=DatabaseDrivers.SQLITE,
        HOST=f"/{database_path}",
    )
    sidecars = (
        database_path.with_name("camply.db-journal"),
        database_path.with_name("camply.db-shm"),
        database_path.with_name("camply.db-wal"),
    )
    for path in (database_path, *sidecars):
        path.touch()

    assert await delete_database(database) is True
    assert not any(path.exists() for path in (database_path, *sidecars))
