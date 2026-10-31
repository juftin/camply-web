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


def test_serve_namespace_lists_all_roles() -> None:
    """The serve group advertises each runtime under one namespace."""
    result = CliRunner().invoke(cli, ["serve", "--help"])

    assert result.exit_code == 0, result.output
    for role in ("frontend", "backend", "worker", "beat"):
        assert role in result.output


@pytest.mark.parametrize("args", [[], ["--host", "0.0.0.0", "--port", "9000"]])
def test_serve_defaults_to_standalone(
    monkeypatch: pytest.MonkeyPatch, args: list[str]
) -> None:
    """Bare serving reuses the standalone launcher in the current Python environment."""
    monkeypatch.setenv("CAMPLY_RUNTIME_MODE", "distributed")
    execute = Mock(side_effect=SystemExit(0))
    monkeypatch.setattr("os.execv", execute)

    result = CliRunner().invoke(cli, ["serve", *args])

    assert result.exit_code == 0, result.output
    execute.assert_called_once_with(
        sys.executable,
        [sys.executable, "-m", "camply.server.standalone", *args],
    )
    import os

    assert os.environ["CAMPLY_RUNTIME_MODE"] == "standalone"


def test_serve_requires_server_extra(monkeypatch: pytest.MonkeyPatch) -> None:
    """Missing server dependencies fail before starting the standalone runtime."""
    from unittest.mock import patch

    monkeypatch.setattr("os.execv", Mock(side_effect=AssertionError("Unexpected exec")))
    with patch("importlib.util.find_spec", return_value=None):
        result = CliRunner().invoke(cli, ["serve"])

    assert result.exit_code == 1
    assert "camply[server]" in result.stderr


@pytest.mark.parametrize(
    "args", [["--port", "0"], ["--port", "9000", "backend"], ["unknown"]]
)
def test_serve_rejects_ambiguous_or_invalid_arguments(
    monkeypatch: pytest.MonkeyPatch, args: list[str]
) -> None:
    """Invalid or misplaced standalone arguments cannot silently start another role."""
    execute = Mock()
    monkeypatch.setattr("os.execv", execute)

    result = CliRunner().invoke(cli, ["serve", *args])

    assert result.exit_code == 2, result.output
    execute.assert_not_called()


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


def test_frontend_serve_rejects_missing_assets(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Editable installs without a prepared UI report a useful error on stderr."""
    monkeypatch.setattr(camply.cli.main, "__file__", str(tmp_path / "cli" / "main.py"))
    monkeypatch.setattr("shutil.which", lambda name: "/synthetic/bin/nginx")

    result = CliRunner().invoke(cli, ["serve", "frontend"])

    assert result.exit_code == 1
    assert result.stdout == ""
    assert "Frontend assets are missing" in result.stderr


@pytest.mark.parametrize(
    ("command", "module", "arguments"),
    [
        (
            ["serve", "backend", "--bind", "127.0.0.1:9000"],
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
            ["serve", "worker", "--concurrency=2"],
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
            ["serve", "beat", "--schedule", "/tmp/synthetic-schedule"],
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
    module: str,
    arguments: list[str],
) -> None:
    """Each launcher preserves default behavior and forwards runtime arguments."""
    from camply.db import migration

    monkeypatch.delenv("SKIP_MIGRATIONS", raising=False)
    monkeypatch.setenv("PATH", "")
    upgrade = Mock()
    execute = Mock(side_effect=SystemExit(0))
    monkeypatch.setattr(migration, "upgrade", upgrade)
    monkeypatch.setattr("os.execv", execute)

    result = CliRunner().invoke(cli, command)

    assert result.exit_code == 0, result.output
    execute.assert_called_once_with(
        sys.executable, [sys.executable, "-m", module, *arguments]
    )
    assert upgrade.call_count == (1 if command[1] == "backend" else 0)


@pytest.mark.parametrize("skip", [False, True])
def test_backend_migration_ownership(
    monkeypatch: pytest.MonkeyPatch, skip: bool
) -> None:
    """Backend launch honors the existing explicit migration skip setting."""
    from camply.db import migration

    monkeypatch.setenv("SKIP_MIGRATIONS", "1" if skip else "0")
    upgrade = Mock()
    monkeypatch.setattr(migration, "upgrade", upgrade)
    monkeypatch.setattr("os.execv", Mock(side_effect=SystemExit(0)))

    result = CliRunner().invoke(cli, ["serve", "backend"])

    assert result.exit_code == 0, result.output
    assert upgrade.call_count == (0 if skip else 1)


@pytest.mark.parametrize(
    ("command", "extra", "modules"),
    [
        (
            ["serve"],
            "server",
            (
                "fastapi",
                "uvicorn",
                "orjson",
                "jwt",
                "cryptography",
                "prometheus_client",
            ),
        ),
        (
            ["serve", "backend"],
            "server",
            (
                "fastapi",
                "uvicorn",
                "orjson",
                "jwt",
                "cryptography",
                "prometheus_client",
                "gunicorn",
                "uvicorn_worker",
            ),
        ),
        (["serve", "worker"], "distributed", ("celery", "redis", "prometheus_client")),
        (["serve", "beat"], "distributed", ("celery", "redis", "prometheus_client")),
    ],
)
def test_python_roles_check_dependencies_before_side_effects(
    monkeypatch: pytest.MonkeyPatch,
    command: list[str],
    extra: str,
    modules: tuple[str, ...],
) -> None:
    """Partial extras fail before migrations even when unrelated executables exist."""
    from camply.db import migration

    upgrade = Mock()
    execute = Mock()
    monkeypatch.setattr(migration, "upgrade", upgrade)
    monkeypatch.setattr("os.execv", execute)
    monkeypatch.setattr("shutil.which", lambda name: f"/unrelated/bin/{name}")
    for missing in modules:
        monkeypatch.setattr(
            "importlib.util.find_spec",
            lambda name, missing=missing: None if name == missing else object(),
        )
        result = CliRunner().invoke(cli, command)
        assert result.exit_code == 1, (missing, result.output)
        assert f"camply[{extra}]" in result.stderr
        assert missing in result.stderr
        upgrade.assert_not_called()
        execute.assert_not_called()


def test_frontend_explains_missing_nginx(monkeypatch: pytest.MonkeyPatch) -> None:
    """The frontend requires a system Nginx installation rather than Python extras."""
    monkeypatch.setattr("shutil.which", lambda name: None)

    result = CliRunner().invoke(cli, ["serve", "frontend"])

    assert result.exit_code == 1
    assert "Nginx" in result.stderr


@pytest.mark.parametrize(
    "backend_url",
    [
        None,
        "",
        "http://api.example.invalid:9000",
        "https://api.example.invalid/base/api/",
    ],
)
def test_frontend_serve_renders_packaged_configuration(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, backend_url: str | None
) -> None:
    """Render the selected upstream and quoted paths while preserving Nginx variables."""
    if backend_url is None:
        monkeypatch.delenv("CAMPLY_BACKEND_URL", raising=False)
    else:
        monkeypatch.setenv("CAMPLY_BACKEND_URL", backend_url)
    package = tmp_path / "installed package" / "camply"
    static = package / "server" / "static"
    static.mkdir(parents=True)
    (static / "index.html").write_text("synthetic frontend")
    monkeypatch.setattr(camply.cli.main, "__file__", str(package / "cli" / "main.py"))
    monkeypatch.chdir(tmp_path)
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

    result = CliRunner().invoke(cli, ["serve", "frontend"])

    assert result.exit_code == 0, result.output
    assert captured["args"][-2:] == ["-g", "daemon off;"]
    assert f'root "{static.resolve()}";' in captured["server"]
    assert "try_files $uri $uri/ /index.html;" in captured["server"]
    assert "proxy_set_header Host $host;" in captured["server"]
    expected = backend_url or "http://backend:8000"
    assert f'proxy_pass "{expected}";' in captured["server"]
    assert "${CAMPLY_BACKEND_URL}" not in captured["server"]
    assert "/etc/nginx/conf.d/" not in captured["main"]
    assert "pid nginx.pid;" in captured["main"]
