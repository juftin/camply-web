"""Verify the Camply CLI entrypoint reports its program name and version."""

import subprocess
import sys

from click.testing import CliRunner

from camply.__about__ import __application__, __version__
from camply.cli.main import cli


def test_version_reports_program_and_installed_version() -> None:
    """``--version`` prints the distribution name and installed version."""
    result = CliRunner().invoke(cli, ["--version"])
    assert result.exit_code == 0, result.output
    assert result.output == f"{__application__}, version {__version__}\n"


def test_help_names_program() -> None:
    """Both help flags describe the ``camply`` program and its version flag."""
    runner = CliRunner()
    for flag in ("--help", "-h"):
        result = runner.invoke(cli, [flag], prog_name=__application__)
        assert result.exit_code == 0, result.output
        assert f"Usage: {__application__}" in result.output
        assert "--version" in result.output
        assert "campsite finder" in result.output


def test_bare_invocation_prints_help() -> None:
    """Running without arguments prints help and exits successfully."""
    result = CliRunner().invoke(cli, [], prog_name=__application__)
    assert result.exit_code == 0, result.output
    assert f"Usage: {__application__}" in result.output


def test_module_execution_reports_version() -> None:
    """``python -m camply.cli`` resolves to the same entrypoint."""
    result = subprocess.run(
        [sys.executable, "-m", "camply.cli", "--version"],
        capture_output=True,
        text=True,
        timeout=60,
        check=True,
    )
    assert result.stdout == f"{__application__}, version {__version__}\n"
