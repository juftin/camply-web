"""Verify the Camply CLI entrypoint reports its program name and version."""

import subprocess
import sys
from pathlib import Path

import pytest
from click.testing import CliRunner

import camply.cli.main
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


def test_frontend_dir_prints_absolute_asset_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The path is shell-friendly and independent of the current directory."""
    package = tmp_path / "installed package" / "camply"
    static = package / "server" / "static"
    static.mkdir(parents=True)
    (static / "index.html").write_text("synthetic frontend")
    monkeypatch.setattr(camply.cli.main, "__file__", str(package / "cli" / "main.py"))
    monkeypatch.chdir(tmp_path)

    result = CliRunner().invoke(cli, ["frontend", "dir"])

    assert result.exit_code == 0, result.output
    assert result.output == f"{static.resolve()}\n"


def test_frontend_dir_rejects_missing_assets(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Editable installs without a prepared UI report a useful error on stderr."""
    monkeypatch.setattr(camply.cli.main, "__file__", str(tmp_path / "cli" / "main.py"))

    result = CliRunner().invoke(cli, ["frontend", "dir"])

    assert result.exit_code == 1
    assert result.stdout == ""
    assert "Frontend assets are missing" in result.stderr
