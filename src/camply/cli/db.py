"""
Database and provider metadata CLI commands.
"""

import asyncio

import click
import rich.traceback

from camply.providers import PROVIDERS

rich.traceback.install(
    show_locals=False,
    suppress=[click, asyncio],
)


@click.group(name="db")
def db_group() -> None:
    """Database and provider metadata commands."""


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
    help="Provider ID to populate, or 'all' for all providers; use --help to list supported providers.",
)
def metadata_cmd(provider_id: str) -> None:
    """
    Populate the Database with Provider Data.

    Parameters
    ----------
    provider_id : str
        Specific provider ID to populate, or 'all' to populate all registered providers.
    """

    async def populate() -> None:
        """Populate the selected provider (or all providers) and release HTTP connections."""
        target_ids = (
            list(PROVIDERS.keys()) if provider_id == "all" else [int(provider_id)]
        )
        for pid in target_ids:
            provider = PROVIDERS[pid]()
            try:
                await provider.populate_database()
            finally:
                await provider.async_client.aclose()

    asyncio.run(populate())


# Also register populate-database as alias under db
db_group.add_command(metadata_cmd, name="populate-database")
