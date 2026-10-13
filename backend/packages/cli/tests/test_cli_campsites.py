"""
Tests for camply campsites command.
"""

from datetime import date
from unittest.mock import AsyncMock, patch

from click.testing import CliRunner

from camply.app import cli
from camply_core.models import CampsiteDTO, CampsiteType


def test_campsites_missing_required_args() -> None:
    """Verify error on missing required options."""
    runner = CliRunner()
    result = runner.invoke(cli, ["campsites"])
    assert result.exit_code != 0
    assert "Missing option" in result.output


def test_campsites_invalid_date_order() -> None:
    """Verify error when arrival is after departure."""
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "campsites",
            "-c",
            "12345",
            "-s",
            "2026-09-05",
            "-e",
            "2026-09-01",
        ],
    )
    assert result.exit_code != 0
    assert "Start date must be strictly before end date" in result.output


def test_campsites_search_success() -> None:
    """Verify successful campsite search execution and table output."""
    mock_sites = [
        CampsiteDTO(
            campsite_id="site_100",
            campsite_name="Standard Site 100",
            campsite_type=CampsiteType.TENT,
            capacity=6,
            available_dates=[date(2026, 9, 1), date(2026, 9, 2)],
            is_electric=False,
            is_accessible=True,
            booking_url="https://www.recreation.gov/camping/campsites/site_100",
        )
    ]

    with patch(
        "camply_core.providers.recreation_gov.RecreationGovClient.find_availabilities",
        new_callable=AsyncMock,
        return_value=mock_sites,
    ):
        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "campsites",
                "-c",
                "12345",
                "-s",
                "2026-09-01",
                "-e",
                "2026-09-03",
            ],
        )
        assert result.exit_code == 0
        assert "site_100" in result.output
        assert "TENT" in result.output


def test_campsites_search_json_output() -> None:
    """Verify --output-json outputs valid JSON."""
    mock_sites = [
        CampsiteDTO(
            campsite_id="site_100",
            campsite_name="Standard Site 100",
            campsite_type=CampsiteType.TENT,
            capacity=6,
            available_dates=[date(2026, 9, 1)],
            is_electric=True,
            is_accessible=True,
            booking_url="https://example.com",
        )
    ]

    with patch(
        "camply_core.providers.recreation_gov.RecreationGovClient.find_availabilities",
        new_callable=AsyncMock,
        return_value=mock_sites,
    ):
        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "campsites",
                "-c",
                "12345",
                "-s",
                "2026-09-01",
                "-e",
                "2026-09-03",
                "--output-json",
            ],
        )
        assert result.exit_code == 0
        assert '"campsite_id": "site_100"' in result.output
