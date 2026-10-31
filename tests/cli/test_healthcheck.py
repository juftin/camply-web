"""Verify health probes fail clearly and target only the requested serving role."""

import json
import os
import socket
import subprocess
import sys
import time
from contextlib import nullcontext
from pathlib import Path
from unittest.mock import Mock

import httpx
import pytest
from click.testing import CliRunner

from camply.cli.main import cli


@pytest.mark.parametrize(
    ("role", "url"),
    [
        ([], "http://127.0.0.1:8000/api/health"),
        (["backend"], "http://127.0.0.1:8000/api/health"),
        (["frontend"], "http://127.0.0.1:8080/healthz"),
    ],
)
def test_http_health_defaults(
    monkeypatch: pytest.MonkeyPatch, role: list[str], url: str
) -> None:
    """HTTP probes use existing local endpoints without a proxy or redirects."""
    probe = Mock(return_value=nullcontext(httpx.Response(200)))
    monkeypatch.setattr(httpx, "stream", probe)
    result = CliRunner().invoke(cli, ["serve", "healthcheck", *role])
    assert result.exit_code == 0, result.output
    assert result.stdout.strip() == "healthy"
    probe.assert_called_once_with(
        "GET", url, timeout=5.0, trust_env=False, follow_redirects=False
    )


@pytest.mark.parametrize("status", [302, 401, 503])
def test_http_health_rejects_unhealthy_status(
    monkeypatch: pytest.MonkeyPatch, status: int
) -> None:
    """Redirects and errors must never be reported as healthy."""
    monkeypatch.setattr(
        httpx, "stream", Mock(return_value=nullcontext(httpx.Response(status)))
    )
    result = CliRunner().invoke(cli, ["serve", "healthcheck", "backend"])
    assert result.exit_code == 1
    assert str(status) in result.stderr


def test_http_health_override_and_connection_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Custom listeners get bounded probes and errors do not expose URL credentials."""
    probe = Mock(side_effect=httpx.ConnectError("synthetic private diagnostic"))
    monkeypatch.setattr(httpx, "stream", probe)
    result = CliRunner().invoke(
        cli,
        [
            "serve",
            "healthcheck",
            "frontend",
            "--url",
            "http://example.invalid:9000/healthz",
            "--timeout",
            "0.5",
        ],
    )
    assert result.exit_code == 1
    assert "synthetic private diagnostic" not in result.output
    probe.assert_called_once_with(
        "GET",
        "http://example.invalid:9000/healthz",
        timeout=0.5,
        trust_env=False,
        follow_redirects=False,
    )


@pytest.mark.parametrize("destination", [None, "synthetic@other-host"])
def test_worker_health_targets_one_node(
    monkeypatch: pytest.MonkeyPatch, destination: str | None
) -> None:
    """A healthy replica cannot satisfy another worker's health check."""
    execute = Mock(return_value=subprocess.CompletedProcess([], 0))
    monkeypatch.setattr(subprocess, "run", execute)
    args = ["serve", "healthcheck", "worker", "--timeout", "4"]
    if destination:
        args.extend(["--destination", destination])
    result = CliRunner().invoke(cli, args)
    assert result.exit_code == 0, result.output
    arguments = execute.call_args.args[0]
    assert arguments[:3] == [sys.executable, "-m", "celery"]
    assert arguments[arguments.index("--destination") + 1] == (
        destination or f"celery@{socket.gethostname()}"
    )
    assert execute.call_args.kwargs["timeout"] == 4
    assert execute.call_args.kwargs["capture_output"] is True


@pytest.mark.parametrize(
    "failure",
    [
        subprocess.CompletedProcess([], 1),
        subprocess.TimeoutExpired("synthetic", 1),
        OSError("synthetic"),
    ],
)
def test_worker_health_fails_on_missing_response(
    monkeypatch: pytest.MonkeyPatch, failure: object
) -> None:
    """Failed, stalled, or unstartable worker probes return unhealthy."""
    execute = (
        Mock(side_effect=failure)
        if isinstance(failure, Exception)
        else Mock(return_value=failure)
    )
    monkeypatch.setattr(subprocess, "run", execute)
    result = CliRunner().invoke(cli, ["serve", "healthcheck", "worker"])
    assert result.exit_code == 1
    assert "healthy" not in result.stdout


@pytest.mark.parametrize(
    "state", ["healthy", "missing", "stale", "future", "dead", "invalid-pid", "corrupt"]
)
def test_beat_health_validates_loop_and_process(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, state: str
) -> None:
    """Beat must have both a fresh scheduler tick and a live positive PID."""
    path = tmp_path / "beat.json"
    monkeypatch.setenv("CAMPLY_BEAT_HEALTH_FILE", str(path))
    if state != "missing":
        stamp = (
            time.time() - 120
            if state == "stale"
            else time.time() + 120
            if state == "future"
            else time.time()
        )
        path.write_text(
            "invalid"
            if state == "corrupt"
            else json.dumps(
                {
                    "pid": 0 if state == "invalid-pid" else os.getpid(),
                    "timestamp": stamp,
                }
            )
        )
    if state == "dead":
        monkeypatch.setattr(os, "kill", Mock(side_effect=ProcessLookupError))
    result = CliRunner().invoke(cli, ["serve", "healthcheck", "beat"])
    assert result.exit_code == (0 if state == "healthy" else 1), result.output


@pytest.mark.parametrize(
    "args",
    [["--timeout", "0"], ["--timeout", "2", "backend"], ["beat", "--max-age", "0"]],
)
def test_health_rejects_invalid_or_misplaced_options(args: list[str]) -> None:
    """Invalid deadlines and standalone options before an explicit role fail parsing."""
    result = CliRunner().invoke(cli, ["serve", "healthcheck", *args])
    assert result.exit_code == 2, result.output


def test_worker_rejects_multiple_destinations(monkeypatch: pytest.MonkeyPatch) -> None:
    """Celery's comma-separated target syntax must not weaken a single-worker probe."""
    execute = Mock()
    monkeypatch.setattr(subprocess, "run", execute)
    result = CliRunner().invoke(
        cli, ["serve", "healthcheck", "worker", "--destination", "one,two"]
    )
    assert result.exit_code == 2, result.output
    execute.assert_not_called()
