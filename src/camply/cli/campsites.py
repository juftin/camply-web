"""Watch campground availability in the foreground and display qualifying stays."""

from datetime import date

import click

from camply.cli import options
from camply.cli.discovery import normalize_ids, resolve_targets
from camply.cli.execution import run
from camply.cli.options import ISODate, resolve_debug
from camply.cli.output import diagnostic, render_stays
from camply.cli.providers import selected_provider


@click.command(name="campsites")
@options.provider()
@options.debug()
@options.rec_area()
@options.campground()
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
@click.pass_context
def campsites_cmd(
    ctx: click.Context,
    provider: str | None,
    debug: bool | None,
    rec_area: tuple[str, ...],
    campground: tuple[str, ...],
    start_date: tuple[date, ...],
    end_date: tuple[date, ...],
    day: tuple[str, ...],
    weekends: bool,
    nights: int,
) -> None:
    """Watch campground availability immediately and until cancelled (Ctrl-C).

    Results appear only in the console. External notifications and legacy run-mode
    switches are deferred.
    """
    from camply.core.search import monitor, normalize_request

    name, provider_class = selected_provider(ctx, provider)
    areas, campgrounds = (
        normalize_ids(rec_area, "--rec-area"),
        normalize_ids(campground, "--campground"),
    )
    if not areas and not campgrounds:
        raise click.UsageError("Select at least one --rec-area or --campground.")
    try:
        request = normalize_request(
            start_dates=start_date,
            end_dates=end_date,
            days=day,
            weekends=weekends,
            nights=nights,
        )
    except ValueError as exc:
        raise click.UsageError(str(exc)) from exc
    for warning in request.warnings:
        click.echo(f"Warning: {warning}", err=True)
    if areas and campgrounds:
        click.echo(
            "Ignoring --rec-area because explicit --campground IDs take precedence.",
            err=True,
        )
    diagnostic(
        f"Watching campground availability on {name}; cancel with Ctrl-C.",
        resolve_debug(ctx, debug),
    )

    async def watch() -> None:
        instance = provider_class()
        try:
            targets = await resolve_targets(instance, areas, campgrounds)
            if not targets:
                click.echo(
                    "No eligible campgrounds found in the selected recreation areas."
                )
                return
            await monitor(instance, targets, request, render_stays)
        finally:
            await instance.async_client.aclose()

    run(watch)
