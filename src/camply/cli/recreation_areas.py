"""Discover recreation areas directly from upstream provider metadata."""

import click

from camply.cli import options
from camply.cli.discovery import DISPLAY_LIMIT, discovery_query
from camply.cli.execution import run
from camply.cli.options import resolve_debug
from camply.cli.output import (
    diagnostic,
    logger,
    render_discovery,
    render_discovery_json,
)
from camply.cli.providers import selected_provider
from camply.providers.dto import SearchEntityType


@click.command(name="recreation-areas")
@options.provider()
@options.debug()
@options.search()
@options.state()
@options.limit()
@options.json_output()
@click.pass_context
def recreation_areas_cmd(
    ctx: click.Context,
    provider: str | None,
    debug: bool | None,
    search: str,
    state: str | None,
    limit: int = DISPLAY_LIMIT,
    json_output: bool = False,
) -> None:
    """Discover recreation areas directly from the booking provider."""
    name, provider_class = selected_provider(ctx, provider)
    query = discovery_query(search, state, limit=limit)
    diagnostic(
        f"Discovering recreation areas on {name}.",
        resolve_debug(ctx, debug),
        provider=name,
        stderr_only=json_output,
    )
    if query.query:
        logger.info('Searching for Recreation Areas: "%s"', query.query)
    else:
        logger.info("Searching for Recreation Areas")

    async def discover() -> None:
        instance = provider_class()
        try:
            results = await instance.search(
                query.query,
                state=query.state,
                entity_type=SearchEntityType.RECREATION_AREA,
                limit=query.limit,
            )
            if json_output:
                render_discovery_json(results, limit=limit)
            else:
                render_discovery(
                    results,
                    empty="No recreation areas found. This provider may not have a recreation-area catalog.",
                    limit=limit,
                )
        finally:
            await instance.async_client.aclose()

    run(discover)
