"""Watch campground availability in the foreground and display qualifying stays."""

from datetime import date
from pathlib import Path
from typing import TYPE_CHECKING

import click

from camply.cli import options
from camply.cli.discovery import DISPLAY_LIMIT, normalize_ids, resolve_targets
from camply.cli.execution import run
from camply.cli.notifications import (
    CLINotificationConfig,
    StayDeduplicationState,
    resolve_notification_config,
    send_stay_notifications,
)
from camply.cli.options import ISODate, resolve_debug
from camply.cli.output import (
    diagnostic,
    format_campground_log,
    logger,
    render_stays,
    render_stays_json,
)
from camply.cli.providers import selected_provider

if TYPE_CHECKING:
    from camply.core.search import AvailabilityStay, SearchRequest
    from camply.providers.base import BaseProvider


def _validate_provider_filters(
    provider_name: str,
    provider_class: type["BaseProvider"],
    request: "SearchRequest",
) -> None:
    """Reject site-attribute filters that are unsupported by the selected provider."""
    caps = provider_class.filter_capabilities
    unsupported: list[str] = []
    if request.campsite_types and not caps.preferred_types:
        unsupported.append("campsite type")
    if request.require_electric and not caps.require_electric:
        unsupported.append("electric hookup")
    if request.require_accessible and not caps.require_accessible:
        unsupported.append("ADA accessibility")
    if request.min_rv_length is not None and not caps.min_rv_length:
        unsupported.append("minimum RV / trailer length")
    if unsupported:
        raise click.UsageError(
            f"{provider_name} does not support {', '.join(unsupported)} filtering."
        )


def _announce_watch(
    name: str,
    debug_enabled: bool,
    json_output: bool,
    request: "SearchRequest",
    areas: tuple[str, ...],
    campgrounds: tuple[str, ...],
) -> None:
    """Initialize logging and emit initial search summary messages."""
    diagnostic(
        f"Watching campground availability on {name}; cancel with Ctrl-C.",
        debug_enabled,
        provider=name,
        stderr_only=json_output,
    )
    for warning in request.warnings:
        logger.warning("Warning: %s", warning)
    if areas and campgrounds:
        logger.warning(
            "Ignoring --rec-area because explicit --campground IDs take precedence."
        )
    logger.info(
        "%s booking nights selected for search, ranging from %s to %s",
        len(request.eligible_dates),
        min(request.eligible_dates).isoformat(),
        max(request.eligible_dates).isoformat(),
    )
    if request.nights > 1:
        logger.info(
            "Searching for availabilities with %s consecutive night stays.",
            request.nights,
        )


async def _execute_watch(
    provider_class: type["BaseProvider"],
    areas: tuple[str, ...],
    campgrounds: tuple[str, ...],
    request: "SearchRequest",
    notification_config: CLINotificationConfig,
    dedup_state: StayDeduplicationState,
    *,
    effective_interval: float,
    search_once: bool,
    json_output: bool,
) -> None:
    """Resolve targets, monitor availability, and release the provider HTTP client."""
    from camply.core.search import monitor

    async def handle_stays(stays: list["AvailabilityStay"]) -> None:
        if json_output:
            render_stays_json(stays)
        else:
            render_stays(stays)
        new_stays = dedup_state.record_cycle(stays)
        if notification_config.channels and new_stays:
            await send_stay_notifications(notification_config, new_stays)

    instance = provider_class()
    try:
        targets = await resolve_targets(instance, areas, campgrounds)
        if not targets:
            logger.info(
                "No eligible campgrounds found in the selected recreation areas."
            )
            if json_output:
                render_stays_json([])
            return
        logger.info("%s Matching Campgrounds Found", len(targets))
        for target in targets[:DISPLAY_LIMIT]:
            logger.info(format_campground_log(target))
        logger.info("Searching across %s campgrounds", len(targets))
        await monitor(
            instance,
            targets,
            request,
            handle_stays,
            interval=effective_interval,
            once=search_once,
        )
    finally:
        await instance.async_client.aclose()


@click.command(name="campsites")
@options.provider()
@options.debug()
@options.rec_area()
@options.campground()
@options.campsite()
@click.option(
    "--start-date",
    type=ISODate(),
    multiple=True,
    required=True,
    help="Inclusive arrival date; pair each occurrence with --end-date.",
)
@click.option(
    "--end-date",
    type=ISODate(),
    multiple=True,
    required=True,
    help="Exclusive checkout date; pair each occurrence with --start-date.",
)
@click.option(
    "--day",
    multiple=True,
    help="Eligible weekday name or abbreviation; repeat to combine.",
)
@click.option("--weekends", is_flag=True, help="Include Friday and Saturday nights.")
@click.option(
    "--nights",
    type=click.IntRange(min=1),
    default=1,
    show_default=True,
    help="Exact consecutive nights per stay.",
)
@options.campsite_type()
@options.electric()
@options.accessible()
@options.rv_length()
@options.notifications()
@options.ntfy_topic()
@options.ntfy_server()
@options.state_file()
@options.search_once()
@options.interval()
@options.json_output()
@click.pass_context
def campsites_cmd(
    ctx: click.Context,
    provider: str | None,
    debug: bool | None,
    rec_area: tuple[str, ...],
    campground: tuple[str, ...],
    campsite: tuple[str, ...],
    start_date: tuple[date, ...],
    end_date: tuple[date, ...],
    day: tuple[str, ...],
    weekends: bool,
    nights: int,
    campsite_type: tuple[str, ...],
    electric: bool,
    accessible: bool,
    rv_length: int | None,
    notifications: tuple[str, ...],
    ntfy_topic: str | None,
    ntfy_server: str | None,
    state_file: Path | None,
    search_once: bool = False,
    interval: float = 60.0,
    json_output: bool = False,
) -> None:
    """Watch campground availability immediately and until cancelled (Ctrl-C)."""
    from camply.core.search import POLL_INTERVAL_SECONDS, normalize_request

    if json_output and not search_once:
        raise click.UsageError("--json requires --search-once on campsites.")
    name, provider_class = selected_provider(ctx, provider)
    areas, campgrounds = (
        normalize_ids(rec_area, "--rec-area"),
        normalize_ids(campground, "--campground"),
    )
    if not areas and not campgrounds:
        raise click.UsageError("Select at least one --rec-area or --campground.")
    campsites = normalize_ids(campsite, "--campsite")
    try:
        request = normalize_request(
            start_dates=start_date,
            end_dates=end_date,
            days=day,
            weekends=weekends,
            nights=nights,
            campsites=campsites,
            campsite_types=campsite_type,
            require_electric=electric,
            require_accessible=accessible,
            min_rv_length=rv_length,
        )
        notification_config = resolve_notification_config(
            notifications, ntfy_topic, ntfy_server
        )
    except ValueError as exc:
        raise click.UsageError(str(exc)) from exc
    _validate_provider_filters(name, provider_class, request)
    _announce_watch(
        name,
        resolve_debug(ctx, debug),
        json_output,
        request,
        areas,
        campgrounds,
    )

    dedup_state = StayDeduplicationState.load(state_file)
    effective_interval = (
        interval
        if ctx.get_parameter_source("interval")
        == click.core.ParameterSource.COMMANDLINE
        else POLL_INTERVAL_SECONDS
    )

    run(
        lambda: _execute_watch(
            provider_class,
            areas,
            campgrounds,
            request,
            notification_config,
            dedup_state,
            effective_interval=effective_interval,
            search_once=search_once,
            json_output=json_output,
        )
    )
