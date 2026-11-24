"""
Alembic Migration Environment Configuration
"""

import asyncio
import logging

from alembic import context
from alembic.config import Config
from sqlalchemy import Connection
from sqlalchemy.ext.asyncio import AsyncEngine

from camply.db.config import DatabaseConfig, db
from camply.db.models import Base

config: Config = context.config
database_config = config.attributes.get("database_config") or (
    DatabaseConfig() if DatabaseConfig().model_fields_set else db
)
"""Explicit migration settings, or the application's CAMPLY_DB_* defaults."""
target_metadata = Base.metadata

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)8s]: %(message)s",
)


def run_migrations_offline() -> None:
    """
    Run migrations in 'offline' mode.
    """
    context.configure(
        url=database_config.url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_migrations(connection: Connection) -> None:
    """
    Perform migrations using the provided connection.
    """
    sqlite = connection.dialect.name == "sqlite"
    if sqlite:
        connection.exec_driver_sql("PRAGMA foreign_keys=OFF")
        connection.commit()
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
    )
    try:
        with context.begin_transaction():
            context.run_migrations()
        if sqlite and connection.exec_driver_sql("PRAGMA foreign_key_check").first():
            raise RuntimeError("Migration left invalid foreign-key references")
    finally:
        if sqlite:
            connection.commit()
            connection.exec_driver_sql("PRAGMA foreign_keys=ON")


async def run_migrations_online_async() -> None:
    """
    Run migrations in 'online' mode (Async).
    """
    engine: AsyncEngine = database_config.create_async_engine()
    try:
        async with engine.connect() as connection:
            await connection.run_sync(do_migrations)
    finally:
        await engine.dispose()


def run_migrations_online() -> None:
    """
    Run migrations in 'online' mode.
    """
    asyncio.run(run_migrations_online_async())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
