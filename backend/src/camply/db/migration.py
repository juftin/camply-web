"""Run the installed migration graph without a source checkout or Alembic ini."""

from alembic import command
from alembic.config import Config

from camply.db.config import DatabaseConfig


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


def upgrade(revision: str = "head") -> None:
    """Upgrade the configured database using the installed revision history."""
    command.upgrade(get_alembic_config(), revision=revision)


if __name__ == "__main__":
    upgrade()
