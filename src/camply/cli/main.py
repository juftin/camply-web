"""
Camply CLI entrypoint.

The ``camply`` console script resolves to :func:`cli`. Subcommands are
registered on this group as the CLI grows.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
from importlib.resources import files
from pathlib import Path

import click

from camply.__about__ import __application__, __version__
from camply.cli.healthcheck import beat_health_path, healthcheck
from camply.cli.runtime import require_modules


@click.group(
    name=__application__,
    invoke_without_command=True,
    context_settings={"help_option_names": ["-h", "--help"]},
)
@click.version_option(
    version=__version__,
    prog_name=__application__,
    message="%(prog)s, version %(version)s",
)
@click.pass_context
def cli(ctx: click.Context) -> None:
    """
    camply, the campsite finder ⛺️.

    Find campsites at sold-out campgrounds.
    """
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


def _executable(name: str, *, hint: str) -> str:
    """Find a runtime executable before performing startup side effects."""
    executable = shutil.which(name)
    if executable is None:
        raise click.ClickException(f"{name} is required. {hint}")
    return executable


def _require_server(*modules: str) -> None:
    """Check shared server dependencies plus any role-specific Python modules."""
    require_modules(
        "server",
        (
            "fastapi",
            "uvicorn",
            "orjson",
            "jwt",
            "cryptography",
            "prometheus_client",
            *modules,
        ),
    )


@cli.group(invoke_without_command=True)
@click.option("--host", help="Standalone bind address (default: 127.0.0.1).")
@click.option(
    "--port", type=click.IntRange(1, 65535), help="Standalone port (default: 8000)."
)
@click.pass_context
def serve(ctx: click.Context, host: str | None, port: int | None) -> None:
    """Serve the standalone app, or select an individual application role."""
    if ctx.invoked_subcommand is not None:
        if host is not None or port is not None:
            raise click.UsageError(
                "--host and --port apply to standalone serving; omit the subcommand."
            )
        return
    _require_server()
    args = [sys.executable, "-m", "camply.server.standalone"]
    if host is not None:
        args.extend(["--host", host])
    if port is not None:
        args.extend(["--port", str(port)])
    os.environ["CAMPLY_RUNTIME_MODE"] = "standalone"
    os.execv(sys.executable, args)


@serve.command(name="frontend")
def serve_frontend() -> None:
    """Serve bundled assets and proxy /api to CAMPLY_BACKEND_URL using Nginx."""
    executable = _executable("nginx", hint="Install Nginx or use the camply-web image.")
    directory = Path(__file__).resolve().parents[1] / "server" / "static"
    if not (directory / "index.html").is_file():
        raise click.ClickException(
            "Frontend assets are missing. Install a prepared camply wheel."
        )
    templates = files("camply.cli").joinpath("nginx")
    with tempfile.TemporaryDirectory(prefix="camply-nginx-") as temporary:
        runtime = Path(temporary).resolve()
        server = runtime / "server.conf"
        config = runtime / "nginx.conf"
        server.write_text(
            templates.joinpath("server.conf")
            .read_text()
            .replace(
                "${CAMPLY_FRONTEND_DIR}", json.dumps(str(directory), ensure_ascii=False)
            )
            .replace(
                "${CAMPLY_BACKEND_URL}",
                json.dumps(
                    os.environ.get("CAMPLY_BACKEND_URL") or "http://backend:8000",
                    ensure_ascii=False,
                ),
            )
        )
        config.write_text(
            templates.joinpath("nginx.conf")
            .read_text()
            .replace(
                "${CAMPLY_NGINX_SERVER_CONFIG}",
                json.dumps(str(server), ensure_ascii=False),
            )
        )
        os.execv(
            executable,
            [executable, "-p", f"{runtime}/", "-c", str(config), "-g", "daemon off;"],
        )


@serve.command(name="backend", context_settings={"ignore_unknown_options": True})
@click.argument("args", nargs=-1, type=click.UNPROCESSED)
def serve_backend(args: tuple[str, ...]) -> None:
    """Migrate the database and serve the API; forward arguments to Gunicorn."""
    _require_server("gunicorn", "uvicorn_worker")
    if os.environ.get("SKIP_MIGRATIONS", "0") != "1":
        from camply.db.migration import upgrade

        upgrade()
    os.execv(
        sys.executable,
        [
            sys.executable,
            "-m",
            "gunicorn",
            "--config",
            "python:camply.server.gunicorn",
            *args,
            "camply.server.app:app",
        ],
    )


@serve.command(name="worker", context_settings={"ignore_unknown_options": True})
@click.argument("args", nargs=-1, type=click.UNPROCESSED)
def serve_worker(args: tuple[str, ...]) -> None:
    """Consume background tasks; forward arguments to the Celery worker."""
    _worker_process("worker", ("-Q", "celery", "--concurrency=4", *args))


@serve.command(name="beat", context_settings={"ignore_unknown_options": True})
@click.option(
    "--sync-providers",
    is_flag=True,
    help="Enqueue an initial provider catalog sync before starting the scheduler.",
)
@click.argument("args", nargs=-1, type=click.UNPROCESSED)
def serve_beat(sync_providers: bool, args: tuple[str, ...]) -> None:
    """Schedule background tasks; optionally enqueue a provider sync before exec."""
    _worker_process(
        "beat",
        (
            "--scheduler",
            "camply.worker.scheduler:HealthScheduler",
            "--max-interval=30",
            *args,
        ),
        sync_providers=sync_providers,
    )


def _worker_process(
    command: str, args: tuple[str, ...], *, sync_providers: bool = False
) -> None:
    """Check dependencies, optionally dispatch a sync, then exec the distributed role."""
    require_modules("distributed", ("celery", "redis", "prometheus_client"))
    if command == "beat":
        path = beat_health_path()
        try:
            path.unlink(missing_ok=True)
        except OSError as exc:
            raise click.ClickException(
                "Cannot prepare the beat heartbeat file."
            ) from exc
        os.environ["CAMPLY_BEAT_HEALTH_FILE"] = str(path)
    if sync_providers:
        try:
            subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "celery",
                    "-A",
                    "camply.worker.celery_app",
                    "call",
                    "camply.catalog.sync_all_providers",
                    "--expires=600",
                ],
                check=True,
            )
        except subprocess.CalledProcessError as exc:
            raise click.ClickException(
                f"Could not enqueue provider sync (exit status {exc.returncode})."
            ) from exc
    os.execv(
        sys.executable,
        [
            sys.executable,
            "-m",
            "celery",
            "-A",
            "camply.worker.celery_app",
            command,
            "-l",
            "info",
            *args,
        ],
    )


serve.add_command(healthcheck)
