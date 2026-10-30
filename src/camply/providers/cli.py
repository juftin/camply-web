"""
Populate Database CLI
"""

import asyncio

import click
import rich.traceback

from camply.providers import PROVIDERS

rich.traceback.install(
    show_locals=False,
    suppress=[click, asyncio],
)


@click.command(
    help="Populate provider metadata independently of availability scans.\n\n"
    + "; ".join(
        f"{provider_id} = {provider_cls.__name__.removesuffix('Provider')}"
        for provider_id, provider_cls in PROVIDERS.items()
    )
)
@click.option(
    "--provider-id",
    type=click.Choice([str(provider_id) for provider_id in PROVIDERS] + ["all"]),
    default="1",
    show_default=True,
    help="Provider ID to populate, or 'all' for all providers; use --help to list supported providers.",
)
def populate_database(provider_id: str) -> None:
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


if __name__ == "__main__":
    populate_database()
