"""Validate optional runtime dependencies without importing application bootstraps."""

import importlib.util

import click


def require_modules(extra: str, modules: tuple[str, ...]) -> None:
    """Reject incomplete extras in this interpreter before runtime side effects."""
    missing = [name for name in modules if importlib.util.find_spec(name) is None]
    if missing:
        raise click.ClickException(
            f"Missing runtime dependencies: {', '.join(missing)}. Install camply[{extra}]."
        )
