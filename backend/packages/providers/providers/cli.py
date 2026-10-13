"""
Populate Database CLI
"""

import asyncio

import click
import rich.traceback

from providers import PROVIDERS

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
    type=click.Choice([str(provider_id) for provider_id in PROVIDERS]),
    default="1",
    show_default=True,
    help="Provider ID to populate; use --help to list supported providers.",
)
def populate_database(provider_id: str) -> None:
    """
    Populate the Database with Provider Data
    """

    async def populate() -> None:
        """Populate the selected provider and release its HTTP connections."""
        provider = PROVIDERS[int(provider_id)]()
        try:
            await provider.populate_database()
        finally:
            await provider.async_client.aclose()

    asyncio.run(populate())


if __name__ == "__main__":
    populate_database()
