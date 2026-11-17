"""Browse campgrounds and resolve exact campground or recreation-area selectors."""

import click

from camply.cli import options
from camply.cli.discovery import (
    DISPLAY_LIMIT,
    discovery_query,
    normalize_ids,
    resolve_targets,
)
from camply.cli.execution import run
from camply.cli.options import resolve_debug
from camply.cli.output import (
    diagnostic,
    logger,
    render_discovery,
    render_discovery_json,
)
from camply.cli.providers import selected_provider
from camply.providers.dto import ProviderSearchResult, SearchEntityType


@click.command(name="campgrounds")
@options.provider()
@options.debug()
@options.search()
@options.state()
@options.rec_area()
@options.campground()
@options.limit()
@options.json_output()
@click.pass_context
def campgrounds_cmd(
    ctx: click.Context,
    provider: str | None,
    debug: bool | None,
    search: str,
    state: str | None,
    rec_area: tuple[str, ...],
    campground: tuple[str, ...],
    limit: int = DISPLAY_LIMIT,
    json_output: bool = False,
) -> None:
    """Find campgrounds, or resolve exact campground and recreation-area IDs."""
    name, provider_class = selected_provider(ctx, provider)
    query = discovery_query(search, state, limit=limit)
    areas, campgrounds = (
        normalize_ids(rec_area, "--rec-area"),
        normalize_ids(campground, "--campground"),
    )
    diagnostic(
        f"Discovering campgrounds on {name}.",
        resolve_debug(ctx, debug),
        provider=name,
        stderr_only=json_output,
    )
    if areas and campgrounds:
        logger.warning(
            "Ignoring --rec-area because explicit --campground IDs take precedence."
        )
    if query.query:
        logger.info('Searching for Campgrounds: "%s"', query.query)
    elif not areas and not campgrounds:
        logger.info("Searching for Campgrounds")

    async def discover() -> None:
        instance = provider_class()
        try:
            results: list[ProviderSearchResult]
            if areas or campgrounds:
                candidates = await resolve_targets(instance, areas, campgrounds)
                results = list(
                    await instance.filter_campgrounds(
                        candidates, query=query.query, state=query.state
                    )
                )
            else:
                results = await instance.search(
                    query.query,
                    state=query.state,
                    entity_type=SearchEntityType.CAMPGROUND,
                    limit=query.limit,
                )
            if json_output:
                render_discovery_json(results, limit=limit)
            else:
                render_discovery(
                    results,
                    empty="No eligible campgrounds found for these selectors and filters.",
                    limit=limit,
                )
        finally:
            await instance.async_client.aclose()

    run(discover)
