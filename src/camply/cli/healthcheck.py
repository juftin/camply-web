"""Read-only health probes for the application's foreground serving roles."""

import json
import os
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import click

from camply.cli.runtime import require_modules


def beat_health_path() -> Path:
    """Locate the scheduler heartbeat shared by serving and probing in one container."""
    return (
        Path(
            os.environ.get("CAMPLY_BEAT_HEALTH_FILE")
            or str(Path(tempfile.gettempdir()) / "camply-beat-health.json")
        )
        .expanduser()
        .resolve()
    )


def _check_http(url: str, *, timeout: float) -> None:
    """Check HTTP status without reading an unbounded body or following redirects."""
    import httpx

    try:
        with httpx.stream(
            "GET", url, timeout=timeout, trust_env=False, follow_redirects=False
        ) as response:
            if not response.is_success:
                raise click.ClickException(
                    f"HTTP healthcheck failed with status {response.status_code}."
                )
    except (httpx.HTTPError, ValueError) as exc:
        raise click.ClickException(
            "HTTP healthcheck could not reach the service."
        ) from exc
    click.echo("healthy")


@click.group(invoke_without_command=True)
@click.option(
    "--url", help="Standalone health URL (default: http://127.0.0.1:8000/api/health)."
)
@click.option(
    "--timeout",
    type=click.FloatRange(min=0, min_open=True),
    help="Network timeout in seconds (default: 5).",
)
@click.pass_context
def healthcheck(ctx: click.Context, url: str | None, timeout: float | None) -> None:
    """Check standalone health, or select an individual serving role."""
    if ctx.invoked_subcommand is not None:
        if url is not None or timeout is not None:
            raise click.UsageError("Place healthcheck options after the role name.")
        return
    _check_http(url or "http://127.0.0.1:8000/api/health", timeout=timeout or 5)


@healthcheck.command(name="backend")
@click.option("--url", default="http://127.0.0.1:8000/api/health", show_default=True)
@click.option(
    "--timeout",
    default=5.0,
    type=click.FloatRange(min=0, min_open=True),
    show_default=True,
)
def backend(url: str, timeout: float) -> None:
    """Check the API's existing HTTP health endpoint."""
    _check_http(url, timeout=timeout)


@healthcheck.command(name="frontend")
@click.option("--url", default="http://127.0.0.1:8080/healthz", show_default=True)
@click.option(
    "--timeout",
    default=5.0,
    type=click.FloatRange(min=0, min_open=True),
    show_default=True,
)
def frontend(url: str, timeout: float) -> None:
    """Check Nginx's health endpoint independently of its API upstream."""
    _check_http(url, timeout=timeout)


@healthcheck.command(name="worker")
@click.option(
    "--destination", help="Celery node name (default: celery@<local hostname>)."
)
@click.option(
    "--timeout",
    default=5.0,
    type=click.FloatRange(min=0, min_open=True),
    show_default=True,
)
def worker(destination: str | None, timeout: float) -> None:
    """Require a reply from this worker through its configured broker."""
    require_modules("distributed", ("celery", "redis", "prometheus_client"))
    target = destination or f"celery@{socket.gethostname()}"
    if "," in target:
        raise click.BadParameter(
            "Specify exactly one Celery node.", param_hint="--destination"
        )
    try:
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "celery",
                "-A",
                "camply.worker.celery_app",
                "inspect",
                "--destination",
                target,
                "--timeout",
                str(timeout / 2),
                "ping",
            ],
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise click.ClickException(
            "Worker healthcheck did not receive a response in time."
        ) from exc
    if result.returncode != 0:
        raise click.ClickException(
            "Worker healthcheck failed; check the target worker and broker."
        )
    click.echo("healthy")


@healthcheck.command(name="beat")
@click.option(
    "--heartbeat-file",
    type=click.Path(path_type=Path),
    help="Override CAMPLY_BEAT_HEALTH_FILE.",
)
@click.option(
    "--max-age",
    default=60.0,
    type=click.FloatRange(min=0, min_open=True),
    show_default=True,
)
def beat(heartbeat_file: Path | None, max_age: float) -> None:
    """Require a fresh scheduler-loop heartbeat from a live local process."""
    if os.name == "nt":
        raise click.ClickException("Beat healthchecks require a Unix PID namespace.")
    path = heartbeat_file or beat_health_path()
    try:
        state = json.loads(path.read_text())
        if not isinstance(state, dict):
            raise ValueError("Invalid heartbeat")
        pid, stamp = state.get("pid"), state.get("timestamp")
        if (
            type(pid) is not int
            or pid <= 0
            or not isinstance(stamp, (int, float))
            or isinstance(stamp, bool)
        ):
            raise ValueError("Invalid heartbeat")
        timestamp = float(stamp)
    except (OSError, ValueError, OverflowError) as exc:
        raise click.ClickException("Beat heartbeat is missing or invalid.") from exc
    if not 0 <= time.time() - timestamp <= max_age:
        raise click.ClickException(
            "Beat heartbeat is stale or has an invalid timestamp."
        )
    try:
        os.kill(pid, 0)
    except (OSError, OverflowError) as exc:
        raise click.ClickException(
            "Beat scheduler process is not running or accessible."
        ) from exc
    click.echo("healthy")
