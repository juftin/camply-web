"""
Tests for catalog commands (campgrounds and recreation-areas).
"""

from unittest.mock import AsyncMock, patch

from click.testing import CliRunner

from camply.app import cli
from camply_core.providers.recreation_gov.models import (
    RecDotGovCampground,
    RecDotGovRecreationArea,
)


def test_campgrounds_missing_arguments() -> None:
    """Verify error when campgrounds invoked with no criteria."""
    runner = CliRunner()
    result = runner.invoke(cli, ["campgrounds"])
    assert result.exit_code != 0
    assert "Please specify at least one search parameter" in result.output


def test_campgrounds_search_success() -> None:
    """Verify campgrounds search renders table."""
    mock_cgs = [
        RecDotGovCampground(
            FacilityID="232463",
            FacilityName="Glacier Basin Campground",
            ParentRecAreaID="2898",
            FacilityTypeDescription="Campground",
            Reservable=True,
        )
    ]

    with patch(
        "camply.commands.campgrounds.search_campgrounds",
        new_callable=AsyncMock,
        return_value=mock_cgs,
    ):
        runner = CliRunner()
        result = runner.invoke(cli, ["campgrounds", "--search", "Glacier Basin"])
        assert result.exit_code == 0
        assert "Glacier Basin Campground" in result.output
        assert "232463" in result.output


def test_recreation_areas_missing_arguments() -> None:
    """Verify error when recreation-areas invoked with no criteria."""
    runner = CliRunner()
    result = runner.invoke(cli, ["recreation-areas"])
    assert result.exit_code != 0
    assert "Please specify at least one search parameter" in result.output


def test_recreation_areas_search_success() -> None:
    """Verify recreation-areas search renders table."""
    mock_ras = [
        RecDotGovRecreationArea(
            RecAreaID="2898",
            RecAreaName="Rocky Mountain National Park",
        )
    ]

    with patch(
        "camply.commands.recreation_areas.search_recreation_areas",
        new_callable=AsyncMock,
        return_value=mock_ras,
    ):
        runner = CliRunner()
        result = runner.invoke(cli, ["recreation-areas", "--search", "Rocky Mountain"])
        assert result.exit_code == 0
        assert "Rocky Mountain National Park" in result.output
        assert "2898" in result.output
