"""
Tests for the BaseProvider abstract class and NullHandler / DatabasePopulator.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from providers.base import (
    BaseProvider,
    DatabasePopulator,
)

# ===========================================================================
# Concrete subclass for testing BaseProvider
# ===========================================================================


class ConcreteProvider(BaseProvider):
    """Minimal concrete subclass of BaseProvider for testing."""

    async def find_availabilities(self, park_id, start_date, end_date):
        return []

    async def sync_metadata(self):
        pass

    async def populate_database(self):
        pass

    @property
    def provider(self):
        from db.models import Provider

        return Provider(id=1, name="TestProvider", url="https://test.provider")

    @classmethod
    def get_rec_area_url(cls, rec_area_id):
        return f"https://test.provider/area/{rec_area_id}"

    @classmethod
    def get_campground_url(cls, campground_id):
        return f"https://test.provider/camp/{campground_id}"


@pytest.fixture
def anyio_backend() -> str:
    """Limit anyio to asyncio backend only (trio is not installed)."""
    return "asyncio"


# ===========================================================================
# BaseProvider tests
# ===========================================================================


class TestBaseProviderInit:
    """Tests for BaseProvider.__init__."""

    def test_init_sets_user_agent(self) -> None:
        provider = ConcreteProvider()
        assert provider.user_agent is not None
        assert isinstance(provider.user_agent, str)

    def test_init_sets_async_client(self) -> None:
        provider = ConcreteProvider()
        assert provider.async_client is not None

    def test_headers_property(self) -> None:
        provider = ConcreteProvider()
        headers = provider.headers
        assert "User-Agent" in headers
        assert headers["User-Agent"] == provider.user_agent

    def test_user_agent_fallback(self) -> None:
        """When fake_useragent fails, use the fallback UA string."""
        with patch(
            "fake_useragent.UserAgent",
            side_effect=Exception("No fake useragent"),
        ):
            provider = ConcreteProvider()
        assert "Mozilla" in provider.user_agent


class TestBaseProviderSearchStatements:
    """Tests for the search table SQL statements.

    These tests the SQL generation logic without executing against a real DB.
    """

    def test_search_rec_area_statement_is_insert(self) -> None:
        provider = ConcreteProvider()
        stmt = provider.search_rec_area_statement
        from sqlalchemy import Insert

        assert isinstance(stmt, Insert)

    def test_search_campground_statement_is_insert(self) -> None:
        provider = ConcreteProvider()
        stmt = provider.search_campground_statement
        from sqlalchemy import Insert

        assert isinstance(stmt, Insert)


class TestBaseProviderPopulateSearchTable:
    """Tests for populate_search_table.

    Requires an async session mock.
    """

    @pytest.mark.anyio
    async def test_populate_search_table(self) -> None:
        provider = ConcreteProvider()
        mock_session = MagicMock()
        # session.begin() returns an async context manager
        mock_ctx = MagicMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=None)
        mock_ctx.__aexit__ = AsyncMock(return_value=None)
        mock_session.begin.return_value = mock_ctx
        mock_session.execute = AsyncMock()
        mock_session.commit = AsyncMock()

        await provider.populate_search_table(mock_session)

        # Should call execute at least twice (delete + rec area + campground)
        assert mock_session.execute.call_count >= 3


# ===========================================================================
# DatabasePopulator
# ===========================================================================


class TestDatabasePopulator:
    """Tests for DatabasePopulator ABC."""

    def test_abstract(self) -> None:
        """Cannot instantiate DatabasePopulator directly."""
        with pytest.raises(TypeError):
            DatabasePopulator()  # type: ignore[abstract]

    def test_concrete_subclass(self) -> None:
        class Populator(DatabasePopulator):
            async def to_database(self, session):
                pass

        p = Populator()
        assert isinstance(p, DatabasePopulator)
