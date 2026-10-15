"""
Database Connections
"""

from enum import Enum
from pathlib import Path
from typing import Any, AsyncGenerator, ClassVar, Optional

import platformdirs
import sqlalchemy.engine
from pydantic import PrivateAttr
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)


class DatabaseDrivers(str, Enum):
    """
    Database drivers
    """

    POSTGRES = "postgresql+psycopg"
    SQLITE = "sqlite+aiosqlite"


DEFAULT_SQLITE_FILE = Path(platformdirs.user_data_dir(appname="camply")) / "camply.db"


class DatabaseConfig(BaseSettings):
    """
    Database Configuration
    """

    model_config: ClassVar[SettingsConfigDict] = SettingsConfigDict(
        env_prefix="CAMPLY_DB_",
        case_sensitive=False,
    )

    DRIVERNAME: DatabaseDrivers = DatabaseDrivers.SQLITE
    USERNAME: str = "camply"
    PASSWORD: Optional[str] = None
    HOST: str = f"/{DEFAULT_SQLITE_FILE}"
    PORT: Optional[int] = None
    DATABASE: str = "camply"
    _engine: Optional[AsyncEngine] = PrivateAttr(default=None)
    _maker: Optional[async_sessionmaker[AsyncSession]] = PrivateAttr(default=None)

    @property
    def url(self) -> sqlalchemy.engine.URL:
        """
        Get the database URL
        """
        if self.DRIVERNAME == DatabaseDrivers.SQLITE:
            filename = self.HOST.replace("//", "/")
            return sqlalchemy.engine.URL.create(
                drivername=self.DRIVERNAME.value,
                database=filename
                if filename == ":memory:"
                else str(Path(filename).expanduser().resolve()),
            )
        return sqlalchemy.engine.URL.create(
            drivername=str(self.DRIVERNAME.value),
            username=(
                self.USERNAME if self.DRIVERNAME != DatabaseDrivers.SQLITE else None
            ),
            password=(
                self.PASSWORD if self.DRIVERNAME != DatabaseDrivers.SQLITE else None
            ),
            host=self.HOST,
            port=(self.PORT if self.DRIVERNAME != DatabaseDrivers.SQLITE else None),
            database=(
                self.DATABASE if self.DRIVERNAME != DatabaseDrivers.SQLITE else None
            ),
        )

    def create_async_engine(self, **kwargs: Any) -> AsyncEngine:
        """
        Get the SQLAlchemy engine
        """
        if self.DRIVERNAME == DatabaseDrivers.SQLITE and self.HOST != ":memory:":
            sqlite_file = Path(str(self.url.database))
            sqlite_file.parent.mkdir(parents=True, exist_ok=True)
        engine = create_async_engine(self.url, **kwargs)
        if self.DRIVERNAME == DatabaseDrivers.SQLITE:
            from sqlalchemy import event

            @event.listens_for(engine.sync_engine, "connect")
            def configure_connection(connection: Any, record: Any) -> None:
                """Enforce references and bound local write contention on every connection."""
                cursor = connection.cursor()
                cursor.execute("PRAGMA busy_timeout=1000")
                cursor.execute("PRAGMA foreign_keys=ON")
                cursor.execute("PRAGMA journal_mode=WAL")
                cursor.close()

        return engine

    def open(self) -> None:
        """Reuse engine resources within the standalone application's event loop."""
        if self._engine is None:
            self._engine = self.create_async_engine()
            self._maker = async_sessionmaker(
                self._engine, expire_on_commit=False, autoflush=False
            )

    async def close(self) -> None:
        """Dispose lifespan-owned resources before the event loop closes."""
        if self._engine is not None:
            await self._engine.dispose()
        self._engine = None
        self._maker = None

    def get_session_maker(self, **kwargs: Any) -> async_sessionmaker[AsyncSession]:
        """
        Get an async session maker for the database
        """
        if self._maker is not None and not kwargs:
            return self._maker
        return async_sessionmaker(
            self.create_async_engine(**kwargs),
            class_=AsyncSession,
            autocommit=False,
            expire_on_commit=False,
            autoflush=False,
        )

    def get_session(self, **kwargs: Any) -> AsyncSession:
        """
        Get an async session for the database
        """
        async_session_maker = self.get_session_maker(**kwargs)
        return async_session_maker()

    async def yield_session(self) -> AsyncGenerator[AsyncSession, None]:
        """
        Yield an async session for the database
        """
        async with self.get_session() as session:
            yield session


db = DatabaseConfig()
