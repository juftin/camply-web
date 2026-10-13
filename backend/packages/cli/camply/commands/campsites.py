"""
Campsite availability search command.
"""

import asyncio
from datetime import date
from typing import Sequence

import click

from camply.config import load_settings
from camply.monitor import AvailabilityMonitor
from camply.output import print_campsites_table, print_error, print_json_output
from camply_core.models import CampsiteType, SearchFilters, SearchWindow


@click.command(name="campsites")
@click.option(
    "--campground",
    "-c",
    "campgrounds",
    multiple=True,
    type=int,
    required=True,
    help="Campground facility ID(s) to check (multiple allowed).",
)
@click.option(
    "--start-date",
    "-s",
    required=True,
    type=click.DateTime(formats=["%Y-%m-%d"]),
    help="(YYYY-MM-DD) Arrival date for the booking search.",
)
@click.option(
    "--end-date",
    "-e",
    required=True,
    type=click.DateTime(formats=["%Y-%m-%d"]),
    help="(YYYY-MM-DD) Checkout date for the booking search.",
)
@click.option(
    "--nights",
    "-n",
    default=1,
    type=click.IntRange(min=1),
    show_default=True,
    help="Minimum consecutive nights required for a qualifying stay.",
)
@click.option(
    "--continuous",
    is_flag=True,
    default=False,
    help="Continuously poll until interrupted.",
)
@click.option(
    "--polling-interval",
    default=10,
    type=click.IntRange(min=1),
    show_default=True,
    help="Polling interval in minutes between availability checks.",
)
@click.option(
    "--notifications",
    multiple=True,
    type=click.Choice(["pushover", "silent"], case_sensitive=False),
    default=["silent"],
    help="Notification channels to trigger on openings.",
)
@click.option(
    "--equipment",
    multiple=True,
    type=click.Choice(["tent", "rv", "cabin", "other"], case_sensitive=False),
    help="Preferred campsite types.",
)
@click.option(
    "--electric/--no-electric",
    default=False,
    help="Require campsite to have electrical hookups.",
)
@click.option(
    "--output-json",
    is_flag=True,
    default=False,
    help="Output results in JSON format.",
)
def campsites_command(
    campgrounds: Sequence[int],
    start_date: click.DateTime,
    end_date: click.DateTime,
    nights: int,
    continuous: bool,
    polling_interval: int,
    notifications: Sequence[str],
    equipment: Sequence[str],
    electric: bool,
    output_json: bool,
) -> None:
    """
    Find campsite availabilities and monitor for openings.
    """
    arrival = (
        start_date.date()
        if hasattr(start_date, "date")
        else date.fromisoformat(str(start_date))
    )
    departure = (
        end_date.date()
        if hasattr(end_date, "date")
        else date.fromisoformat(str(end_date))
    )

    if arrival >= departure:
        print_error("Start date must be strictly before end date.")
        raise click.Abort()

    search_window = SearchWindow(arrival=arrival, departure=departure)

    types: list[CampsiteType] | None = None
    if equipment:
        type_mapping = {
            "tent": CampsiteType.TENT,
            "rv": CampsiteType.RV,
            "cabin": CampsiteType.CABIN,
            "other": CampsiteType.OTHER,
        }
        types = [
            type_mapping[e.lower()] for e in equipment if e.lower() in type_mapping
        ]

    filters = SearchFilters(
        min_consecutive_nights=nights,
        campsite_types=types,
        electric_requirement=electric,
    )

    settings = load_settings()
    monitor = AvailabilityMonitor(
        campground_ids=list(campgrounds),
        search_window=search_window,
        filters=filters,
        continuous=continuous,
        polling_interval_minutes=polling_interval,
        notifications=list(notifications),
        settings=settings,
    )

    def _render(sites) -> None:
        if output_json:
            print_json_output(sites)
        else:
            print_campsites_table(sites)

    try:
        asyncio.run(monitor.run(on_results=_render))
    except KeyboardInterrupt:
        click.echo("\nMonitoring stopped by user.")
