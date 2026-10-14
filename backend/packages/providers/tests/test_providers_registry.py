"""
Tests for the providers package: registry, base provider URL generation, CLI.
"""

from providers import PROVIDERS
from providers.recreation_gov.provider import RecreationGovProvider


class TestProvidersRegistry:
    """Tests for the PROVIDERS registry dict."""

    def test_registry_contains_recreation_gov(self) -> None:
        """The PROVIDERS dict should contain recreation_dot_gov."""
        assert 1 in PROVIDERS
        assert PROVIDERS[1] is RecreationGovProvider

    def test_registry_count(self) -> None:
        """The PROVIDERS dict should have at least one provider registered."""
        assert len(PROVIDERS) >= 1


class TestBaseProviderURLGeneration:
    """Tests for BaseProvider URL generation methods (class methods)."""

    def test_rec_area_url(self) -> None:
        """Test that get_rec_area_url returns a valid URL."""
        url = RecreationGovProvider.get_rec_area_url(rec_area_id="234708")
        assert url is not None
        assert isinstance(url, str)
        assert "234708" in url
        assert url.startswith("http")

    def test_campground_url(self) -> None:
        """Test that get_campground_url returns a valid URL."""
        url = RecreationGovProvider.get_campground_url(campground_id="234708")
        assert url is not None
        assert isinstance(url, str)
        assert "234708" in url
        assert url.startswith("http")

    def test_different_rec_area_ids(self) -> None:
        """Different rec_area_ids should produce different URLs."""
        url1 = RecreationGovProvider.get_rec_area_url(rec_area_id="1")
        url2 = RecreationGovProvider.get_rec_area_url(rec_area_id="2")
        assert url1 != url2


class TestProviderCLI:
    """Tests for the populate-database CLI entry point."""

    def test_cli_entry_point_registered(self) -> None:
        """The CLI entry point should be importable."""
        from providers.cli import populate_database

        assert populate_database is not None
        assert callable(populate_database)
        assert populate_database.name == "populate-database"

    def test_cli_help_includes_all(self) -> None:
        """The CLI help output should include the 'all' option."""
        from click.testing import CliRunner

        from providers.cli import populate_database

        runner = CliRunner()
        result = runner.invoke(populate_database, ["--help"])
        assert result.exit_code == 0
        assert "all" in result.output

    def test_cli_populate_all_providers(self, monkeypatch: object) -> None:
        """Running with --provider-id all should populate all registered providers."""
        from unittest.mock import AsyncMock, patch

        from click.testing import CliRunner

        from providers.cli import populate_database

        runner = CliRunner()
        mock_instances = {}
        for pid in PROVIDERS:
            inst = AsyncMock()
            inst.populate_database = AsyncMock()
            inst.async_client.aclose = AsyncMock()
            mock_instances[pid] = inst

        with patch.dict(
            "providers.cli.PROVIDERS",
            {pid: (lambda p=pid: mock_instances[p]) for pid in PROVIDERS},
        ):
            result = runner.invoke(populate_database, ["--provider-id", "all"])
            assert result.exit_code == 0
            for inst in mock_instances.values():
                inst.populate_database.assert_awaited_once()
                inst.async_client.aclose.assert_awaited_once()
