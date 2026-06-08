"""
Tests for the db package configuration and utilities.
"""


import pytest

from db.config import DatabaseConfig, DatabaseDrivers
from db.utils import format_description


class TestDatabaseConfig:
    """Tests for DatabaseConfig (DbSettings) env var loading."""

    def test_default_values(self) -> None:
        """Test default config values."""
        config = DatabaseConfig()
        assert config.DRIVERNAME == DatabaseDrivers.SQLITE
        assert config.USERNAME == "camply"

    def test_env_var_overrides(self) -> None:
        """Test that environment variables override defaults."""
        with pytest.MonkeyPatch.context() as mp:
            mp.setenv("CAMPLY_DB_DRIVERNAME", "postgresql+psycopg")
            mp.setenv("CAMPLY_DB_HOST", "localhost")
            mp.setenv("CAMPLY_DB_PORT", "5432")
            mp.setenv("CAMPLY_DB_DATABASE", "test_camply")

            config = DatabaseConfig()
            assert config.DRIVERNAME == DatabaseDrivers.POSTGRES
            assert config.HOST == "localhost"
            assert config.PORT == 5432
            assert config.DATABASE == "test_camply"

    def test_sqlite_url_format(self) -> None:
        """Test that SQLite URL is formatted as a string path."""
        config = DatabaseConfig()
        url = config.url
        url_str = str(url)
        assert url_str.startswith("sqlite+aiosqlite:///")

    def test_postgres_url_format(self) -> None:
        """Test that PostgreSQL URL is formatted properly."""
        with pytest.MonkeyPatch.context() as mp:
            mp.setenv("CAMPLY_DB_DRIVERNAME", "postgresql+psycopg")
            mp.setenv("CAMPLY_DB_HOST", "pg.example.com")
            mp.setenv("CAMPLY_DB_PORT", "5432")
            mp.setenv("CAMPLY_DB_USERNAME", "test_user")
            mp.setenv("CAMPLY_DB_PASSWORD", "test_pass")
            mp.setenv("CAMPLY_DB_DATABASE", "camply_db")

            config = DatabaseConfig()
            url_str = str(config.url)
            assert "postgresql+psycopg" in url_str
            assert "test_user" in url_str
            assert "pg.example.com" in url_str
            assert "5432" in url_str

    def test_create_async_engine_sqlite(self) -> None:
        """Test that create_async_engine returns a SQLite engine."""
        config = DatabaseConfig()
        engine = config.create_async_engine()
        assert engine is not None
        assert "sqlite+aiosqlite" in str(engine.url)
        # Note: dispose() is async on AsyncEngine; skip in sync test

    def test_get_session_maker(self) -> None:
        """Test that get_session_maker returns a session maker."""
        config = DatabaseConfig()
        maker = config.get_session_maker()
        assert maker is not None


class TestDbModelUtils:
    """Tests for the db utils module."""

    def test_format_description(self) -> None:
        """Test format_description removes excess whitespace."""
        raw = """
            This is a
            multi-line
            description.
        """
        formatted = format_description(raw)
        assert formatted == "This is a multi-line description."
        assert "\n" not in formatted
