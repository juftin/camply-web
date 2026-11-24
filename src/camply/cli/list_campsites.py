"""List individual campsites in selected campgrounds or recreation areas."""

import click

from camply.cli import options
from camply.cli.discovery import DISPLAY_LIMIT, normalize_ids, resolve_targets
from camply.cli.execution import run
from camply.cli.options import resolve_debug
from camply.cli.output import (
    diagnostic,
    logger,
    render_campsite_catalog,
    render_campsite_catalog_json,
)
from camply.cli.providers import selected_provider, validate_site_filters
from camply.core.search import fetch_campsite_catalog, normalize_campsite_types


@click.command(name="list-campsites")
@options.provider()
@options.debug()
@options.rec_area()
@options.campground()
@options.search()
@options.campsite_type()
@options.electric()
@options.accessible()
@options.rv_length()
@options.limit()
@options.json_output()
@click.pass_context
def list_campsites_cmd(
    ctx: click.Context,
    provider: str | None,
    debug: bool | None,
    rec_area: tuple[str, ...],
    campground: tuple[str, ...],
    search: str,
    campsite_type: tuple[str, ...],
    electric: bool,
    accessible: bool,
    rv_length: int | None,
    limit: int = DISPLAY_LIMIT,
    json_output: bool = False,
) -> None:
    """List campsites and attributes in selected campgrounds or recreation areas."""
    name, provider_class = selected_provider(ctx, provider)
    areas, campgrounds = (
        normalize_ids(rec_area, "--rec-area"),
        normalize_ids(campground, "--campground"),
    )
    if not areas and not campgrounds:
        raise click.UsageError("Select at least one --rec-area or --campground.")
    try:
        normalized_types = normalize_campsite_types(campsite_type)
    except ValueError as exc:
        raise click.UsageError(str(exc)) from exc
    validate_site_filters(
        name,
        provider_class,
        campsite_types=normalized_types,
        require_electric=electric,
        require_accessible=accessible,
        min_rv_length=rv_length,
    )
    diagnostic(
        f"Listing campsites on {name}.",
        resolve_debug(ctx, debug),
        provider=name,
        stderr_only=json_output,
    )
    if areas and campgrounds:
        logger.warning(
            "Ignoring --rec-area because explicit --campground IDs take precedence."
        )

    async def discover_sites() -> None:
        instance = provider_class()
        try:
            targets = await resolve_targets(instance, areas, campgrounds)
            if not targets:
                logger.info(
                    "No eligible campgrounds found in the selected recreation areas."
                )
                if json_output:
                    render_campsite_catalog_json([], limit=limit)
                return
            entries = await fetch_campsite_catalog(
                instance,
                targets,
                search_query=search,
                campsite_types=normalized_types,
                require_electric=electric,
                require_accessible=accessible,
                min_rv_length=rv_length,
            )
            if json_output:
                render_campsite_catalog_json(entries, limit=limit)
            else:
                render_campsite_catalog(entries, limit=limit)
        finally:
            await instance.async_client.aclose()

    run(discover_sites)
