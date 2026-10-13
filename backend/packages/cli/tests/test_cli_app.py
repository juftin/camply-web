"""
Tests for root camply CLI application.
"""

from click.testing import CliRunner

from camply.__about__ import __version__
from camply.app import cli


def test_cli_version() -> None:
    """Verify that --version outputs the correct version."""
    runner = CliRunner()
    result = runner.invoke(cli, ["--version"])
    assert result.exit_code == 0
    assert __version__ in result.output


def test_cli_help() -> None:
    """Verify that --help lists all registered subcommands."""
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "campsites" in result.output
    assert "campgrounds" in result.output
    assert "recreation-areas" in result.output
    assert "configure" in result.output
