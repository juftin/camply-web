"""
Camply CLI entrypoint.

The ``camply`` console script resolves to :func:`cli`. Subcommands are
registered on this group as the CLI grows.
"""

import json
import os
import shutil
import tempfile
from importlib.resources import files
from pathlib import Path

import click

from camply.__about__ import __application__, __version__


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


@cli.group()
def serve() -> None:
    """Run the frontend, backend, worker, or scheduler as a foreground process."""


@serve.command(name="frontend")
def serve_frontend() -> None:
    """Serve bundled assets and proxy /api to backend:8000 using Nginx."""
    executable = _executable("nginx", hint="Install Nginx or use the camply image.")
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
    executable = _executable("gunicorn", hint="Install camply[server].")
    if os.environ.get("SKIP_MIGRATIONS", "0") != "1":
        from camply.db.migration import upgrade

        upgrade()
    os.execv(
        executable,
        [
            executable,
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
@click.argument("args", nargs=-1, type=click.UNPROCESSED)
def serve_beat(args: tuple[str, ...]) -> None:
    """Schedule background tasks; forward arguments to Celery beat."""
    _worker_process("beat", args)


def _worker_process(command: str, args: tuple[str, ...]) -> None:
    """Replace the CLI with a distributed process without importing worker code."""
    executable = _executable("celery", hint="Install camply[distributed].")
    os.execv(
        executable,
        [executable, "-A", "camply.worker.celery_app", command, "-l", "info", *args],
    )
