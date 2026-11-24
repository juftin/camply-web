"""Validate optional runtime dependencies without importing application bootstraps."""

import importlib.util
import os

import click

_MULTIPROC_ENV_VARS = (
    "PROMETHEUS_MULTIPROC_DIR",
    "prometheus_multiproc_dir",
    "CAMPLY_PROMETHEUS_MULTIPROC_DIR",
)


def resolve_prometheus_multiproc_dir() -> str | None:
    """Return the configured Prometheus multiprocess directory, if non-empty."""
    return (
        os.environ.get("CAMPLY_PROMETHEUS_MULTIPROC_DIR")
        or os.environ.get("PROMETHEUS_MULTIPROC_DIR")
        or os.environ.get("prometheus_multiproc_dir")
        or None
    )


def env_without_prometheus_multiproc() -> dict[str, str] | None:
    """Return os.environ without Prometheus multiprocess vars, or None if unset."""
    if not any(var in os.environ for var in _MULTIPROC_ENV_VARS):
        return None
    return {
        key: value
        for key, value in os.environ.items()
        if key not in _MULTIPROC_ENV_VARS
    }


def require_modules(extra: str, modules: tuple[str, ...]) -> None:
    """Reject incomplete extras in this interpreter before runtime side effects."""
    missing = [name for name in modules if importlib.util.find_spec(name) is None]
    if missing:
        raise click.ClickException(
            f"Missing runtime dependencies: {', '.join(missing)}. Install camply-web[{extra}]."
        )
