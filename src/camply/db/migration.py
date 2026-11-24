"""Run the installed migration graph and manage application database storage."""

import asyncio
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import Connection, inspect, text

from camply.db.config import DatabaseConfig, DatabaseDrivers
from camply.db.models import Base


def get_alembic_config(database_config: DatabaseConfig | None = None) -> Config:
    """Configure Alembic using packaged scripts and optional database settings.

    Without an override, migrations use the existing ``CAMPLY_DB_*`` settings.
    Formatter hooks belong to the developer ini and are intentionally excluded.
    """
    config = Config()
    config.set_main_option("script_location", "camply.db:migrations")
    config.set_main_option("timezone", "utc")
    if database_config is not None:
        config.attributes["database_config"] = database_config
    return config


def upgrade(
    revision: str = "head", database_config: DatabaseConfig | None = None
) -> None:
    """Upgrade the configured database using the installed revision history."""
    command.upgrade(
        get_alembic_config(database_config=database_config), revision=revision
    )


def upgrade_database(
    database_config: DatabaseConfig | None = None, *, revision: str = "head"
) -> None:
    """Upgrade database supporting either positional database config or keyword revision."""
    upgrade(revision=revision, database_config=database_config)


def sqlite_database_path(
    database_config: DatabaseConfig | None = None,
) -> Path | None:
    """Return the resolved path for a conventional file-backed SQLite database."""
    resolved_config = database_config or DatabaseConfig()
    parsed_url = resolved_config.url
    if (
        resolved_config.DRIVERNAME != DatabaseDrivers.SQLITE
        or parsed_url.database is None
        or parsed_url.database == ":memory:"
        or parsed_url.query.get("mode") == "memory"
        or parsed_url.query.get("uri") == "true"
    ):
        return None
    return Path(parsed_url.database).expanduser().resolve()


def _delete_sqlite_database_files(database_path: Path) -> None:
    """Remove a SQLite database and transient sidecar files when present."""
    for path in (
        database_path,
        database_path.with_name(f"{database_path.name}-journal"),
        database_path.with_name(f"{database_path.name}-shm"),
        database_path.with_name(f"{database_path.name}-wal"),
    ):
        path.unlink(missing_ok=True)


def _drop_application_tables(connection: Connection) -> None:
    """Drop modeled tables and the Alembic version table on one connection."""
    Base.metadata.drop_all(connection)
    if inspect(connection).has_table("alembic_version"):
        connection.execute(text("DROP TABLE alembic_version"))


async def drop_all_tables(database_config: DatabaseConfig | None = None) -> None:
    """Drop every Camply table and its Alembic revision state."""
    resolved_config = database_config or DatabaseConfig()
    engine = resolved_config.create_async_engine()
    try:
        async with engine.begin() as connection:
            await connection.run_sync(_drop_application_tables)
    finally:
        await engine.dispose()


async def delete_database(database_config: DatabaseConfig | None = None) -> bool:
    """Delete a SQLite database file or drop tables from another backend.

    Parameters
    ----------
    database_config : DatabaseConfig | None
        Explicit database configuration, if different from configured storage.

    Returns
    -------
    bool
        ``True`` when a SQLite database file was removed; ``False`` when a
        non-file backend had its application tables dropped.
    """
    resolved_config = database_config or DatabaseConfig()
    database_path = sqlite_database_path(resolved_config)
    if database_path is None:
        await drop_all_tables(resolved_config)
        return False
    await asyncio.to_thread(_delete_sqlite_database_files, database_path)
    return True


if __name__ == "__main__":
    upgrade()
