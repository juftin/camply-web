"""
Database and provider metadata CLI commands.
"""

import asyncio
import json

import click
import rich.traceback

from camply.db.config import DatabaseConfig
from camply.db.migration import delete_database, sqlite_database_path, upgrade
from camply.providers import CATALOG_PROVIDERS, PROVIDERS

rich.traceback.install(
    show_locals=False,
    suppress=[click, asyncio],
)


@click.group(name="db")
def db_group() -> None:
    """Inspect, migrate, or delete the configured application database."""


def _database_info(database_config: DatabaseConfig | None = None) -> dict[str, object]:
    """Return safe JSON-serializable details for the configured database."""
    resolved_config = database_config or DatabaseConfig()
    parsed_url = resolved_config.url
    database_path = sqlite_database_path(resolved_config)
    return {
        "database_url": parsed_url.render_as_string(hide_password=True),
        "database_url_is_explicit": bool(resolved_config.model_fields_set),
        "dialect": parsed_url.get_backend_name(),
        "driver": parsed_url.get_driver_name(),
        "path": str(database_path) if database_path is not None else None,
        "exists": database_path.is_file() if database_path is not None else None,
    }


@db_group.command(name="info")
def info_cmd() -> None:
    """Print safe configured-database details as JSON."""
    click.echo(json.dumps(_database_info(), indent=2, sort_keys=True))


@db_group.command(name="migrate")
def migrate_cmd() -> None:
    """Apply all pending database migrations."""
    try:
        upgrade(database_config=DatabaseConfig())
    except RuntimeError as exc:
        raise click.ClickException(str(exc)) from exc
    click.echo("Database migrations applied.")


@db_group.command(name="delete")
@click.option(
    "--yes",
    is_flag=True,
    help="Confirm dropping every Camply application table.",
)
def delete_cmd(yes: bool) -> None:
    """Delete the configured SQLite file or drop application tables remotely."""
    database_config = DatabaseConfig()
    safe_url = database_config.url.render_as_string(hide_password=True)
    if not yes and not click.confirm(
        f"Drop every Camply table in {safe_url}?",
        default=False,
    ):
        click.echo("Aborted.")
        return
    try:
        database_file_deleted = asyncio.run(delete_database(database_config))
    except RuntimeError as exc:
        raise click.ClickException(str(exc)) from exc
    if database_file_deleted:
        click.echo("SQLite database file deleted.")
    else:
        click.echo("Database tables deleted.")


@db_group.command(
    name="metadata",
    help="Populate provider metadata independently of availability scans.\n\n"
    + "; ".join(
        f"{provider_id} = {provider_cls.__name__.removesuffix('Provider')}"
        for provider_id, provider_cls in PROVIDERS.items()
    ),
)
@click.option(
    "--provider-id",
    type=click.Choice([str(provider_id) for provider_id in PROVIDERS] + ["all"]),
    default="1",
    show_default=True,
    help="Provider ID to populate, or 'all' for all enabled providers; use --help to list supported providers.",
)
def metadata_cmd(provider_id: str) -> None:
    """
    Populate the Database with Provider Data.

    Parameters
    ----------
    provider_id : str
        Specific provider ID to populate, or 'all' to populate all enabled providers.
    """

    async def populate() -> None:
        """Populate the selected provider (or all providers) and release HTTP connections."""
        target_ids = (
            list(CATALOG_PROVIDERS) if provider_id == "all" else [int(provider_id)]
        )
        for pid in target_ids:
            provider = PROVIDERS[pid]()
            try:
                await provider.populate_database()
            finally:
                await provider.async_client.aclose()

    asyncio.run(populate())
