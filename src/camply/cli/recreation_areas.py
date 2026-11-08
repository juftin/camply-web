"""Discover recreation areas directly from upstream provider metadata."""

import click

from camply.cli import options
from camply.cli.discovery import RESULT_PROBE, discovery_query
from camply.cli.execution import run
from camply.cli.options import resolve_debug
from camply.cli.output import diagnostic, render_discovery
from camply.cli.providers import selected_provider
from camply.providers.dto import SearchEntityType


@click.command(name="recreation-areas")
@options.provider()
@options.debug()
@options.search()
@options.state()
@click.pass_context
def recreation_areas_cmd(
    ctx: click.Context,
    provider: str | None,
    debug: bool | None,
    search: str,
    state: str | None,
) -> None:
    """Discover recreation areas directly from the booking provider."""
    name, provider_class = selected_provider(ctx, provider)
    query = discovery_query(search, state)
    diagnostic(f"Discovering recreation areas on {name}.", resolve_debug(ctx, debug))

    async def discover() -> None:
        instance = provider_class()
        try:
            results = await instance.search(
                query.query,
                state=query.state,
                entity_type=SearchEntityType.RECREATION_AREA,
                limit=RESULT_PROBE,
            )
            render_discovery(
                results,
                empty="No recreation areas found. This provider may not have a recreation-area catalog.",
            )
        finally:
            await instance.async_client.aclose()

    run(discover)
