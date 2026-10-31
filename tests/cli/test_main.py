"""Verify the Camply CLI entrypoint reports its program name and version."""

import subprocess
import sys
from pathlib import Path
from unittest.mock import Mock

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


@pytest.mark.parametrize(
    ("command", "executable", "arguments"),
    [
        (
            ["backend", "serve", "--bind", "127.0.0.1:9000"],
            "gunicorn",
            [
                "--config",
                "python:camply.server.gunicorn",
                "--bind",
                "127.0.0.1:9000",
                "camply.server.app:app",
            ],
        ),
        (
            ["worker", "serve", "--concurrency=2"],
            "celery",
            [
                "-A",
                "camply.worker.celery_app",
                "worker",
                "-l",
                "info",
                "-Q",
                "celery",
                "--concurrency=4",
                "--concurrency=2",
            ],
        ),
        (
            ["worker", "beat", "--schedule", "/tmp/synthetic-schedule"],
            "celery",
            [
                "-A",
                "camply.worker.celery_app",
                "beat",
                "-l",
                "info",
                "--schedule",
                "/tmp/synthetic-schedule",
            ],
        ),
    ],
)
def test_runtime_commands_replace_the_process(
    monkeypatch: pytest.MonkeyPatch,
    command: list[str],
    executable: str,
    arguments: list[str],
) -> None:
    """Each launcher preserves default behavior and forwards runtime arguments."""
    from camply.db import migration

    monkeypatch.delenv("SKIP_MIGRATIONS", raising=False)
    monkeypatch.setattr("shutil.which", lambda name: f"/synthetic/bin/{name}")
    upgrade = Mock()
    execute = Mock(side_effect=SystemExit(0))
    monkeypatch.setattr(migration, "upgrade", upgrade)
    monkeypatch.setattr("os.execv", execute)

    result = CliRunner().invoke(cli, command)

    assert result.exit_code == 0, result.output
    path = f"/synthetic/bin/{executable}"
    execute.assert_called_once_with(path, [path, *arguments])
    assert upgrade.call_count == (1 if command[0] == "backend" else 0)


@pytest.mark.parametrize("skip", [False, True])
def test_backend_migration_ownership(
    monkeypatch: pytest.MonkeyPatch, skip: bool
) -> None:
    """Backend launch honors the existing explicit migration skip setting."""
    from camply.db import migration

    monkeypatch.setenv("SKIP_MIGRATIONS", "1" if skip else "0")
    monkeypatch.setattr("shutil.which", lambda name: f"/synthetic/bin/{name}")
    upgrade = Mock()
    monkeypatch.setattr(migration, "upgrade", upgrade)
    monkeypatch.setattr("os.execv", Mock(side_effect=SystemExit(0)))

    result = CliRunner().invoke(cli, ["backend", "serve"])

    assert result.exit_code == 0, result.output
    assert upgrade.call_count == (0 if skip else 1)


@pytest.mark.parametrize(
    ("command", "hint"),
    [
        (["frontend", "serve"], "Nginx"),
        (["backend", "serve"], "camply[server]"),
        (["worker", "serve"], "camply[distributed]"),
        (["worker", "beat"], "camply[distributed]"),
    ],
)
def test_runtime_commands_explain_missing_executables(
    monkeypatch: pytest.MonkeyPatch, command: list[str], hint: str
) -> None:
    """Missing runtime tools fail before resource setup or database migrations."""
    monkeypatch.setattr("shutil.which", lambda name: None)

    result = CliRunner().invoke(cli, command)

    assert result.exit_code == 1
    assert hint in result.stderr


def test_frontend_serve_renders_packaged_configuration(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Nginx receives quoted resource paths while its own variables survive rendering."""
    package = tmp_path / "installed package" / "camply"
    static = package / "server" / "static"
    static.mkdir(parents=True)
    (static / "index.html").write_text("synthetic frontend")
    monkeypatch.setattr(camply.cli.main, "__file__", str(package / "cli" / "main.py"))
    monkeypatch.setattr("shutil.which", lambda name: "/synthetic/bin/nginx")
    captured: dict[str, str | list[str]] = {}

    def execute(path: str, args: list[str]) -> None:
        """Capture files before simulated process replacement unwinds temporary state."""
        assert path == "/synthetic/bin/nginx"
        captured["args"] = args
        config = Path(args[args.index("-c") + 1])
        captured["main"] = config.read_text()
        captured["server"] = config.with_name("server.conf").read_text()
        raise SystemExit(0)

    monkeypatch.setattr("os.execv", execute)

    result = CliRunner().invoke(cli, ["frontend", "serve"])

    assert result.exit_code == 0, result.output
    assert captured["args"][-2:] == ["-g", "daemon off;"]
    assert f'root "{static.resolve()}";' in captured["server"]
    assert "try_files $uri $uri/ /index.html;" in captured["server"]
    assert "proxy_set_header Host $host;" in captured["server"]
    assert "/etc/nginx/conf.d/" not in captured["main"]
    assert "pid nginx.pid;" in captured["main"]
