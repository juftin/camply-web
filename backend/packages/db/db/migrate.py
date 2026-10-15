"""Apply the same revision graph from a checkout or an installed database wheel."""

from pathlib import Path

from alembic import command
from alembic.config import Config

from db.config import DatabaseConfig, db


def upgrade_database(database: DatabaseConfig = db, *, revision: str = "head") -> None:
    """Upgrade storage before serving, without relying on the working directory."""
    package_dir = Path(__file__).resolve().parent
    migrations = package_dir / "migrations"
    if not migrations.is_dir():
        migrations = package_dir.parent / "migrations"
    if not migrations.is_dir():
        raise RuntimeError(
            "Database migration resources are missing; reinstall the db wheel"
        )
    config = Config()
    config.set_main_option("script_location", str(migrations))
    config.attributes["database_config"] = database
    command.upgrade(config, revision)
