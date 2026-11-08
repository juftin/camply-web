"""Render terminal diagnostics, discovery results and matching stays."""

from collections.abc import Sequence
from typing import TYPE_CHECKING

import click

from camply.cli.discovery import DISPLAY_LIMIT, identity_key
from camply.providers.dto import ProviderSearchResult, SearchEntityType

if TYPE_CHECKING:
    from camply.core.search import AvailabilityStay


def diagnostic(message: str, debug: bool) -> None:
    """Write an explicitly enabled diagnostic to stderr."""
    if debug:
        click.echo(f"Debug: {message}", err=True)


def render_discovery(results: Sequence[ProviderSearchResult], *, empty: str) -> None:
    """Display unique discovery results and report actual display truncation."""
    ordered = sorted(
        {identity_key(result): result for result in results}.values(),
        key=identity_key,
    )
    if not ordered:
        click.echo(empty)
        return
    for result in ordered[:DISPLAY_LIMIT]:
        entity = (
            f"Campground {result.campground_id}: {result.campground_name}"
            if result.entity_type == SearchEntityType.CAMPGROUND
            else f"Recreation area {result.recreation_area_id}: {result.recreation_area_name}"
        )
        click.echo(f"{result.provider_name} | {entity}")
        if result.campground_id is not None and result.recreation_area_id is not None:
            click.echo(
                f"  Recreation area {result.recreation_area_id}: {result.recreation_area_name or ''}"
            )
        location = ", ".join(
            value for value in (result.city, result.state, result.country) if value
        )
        if location:
            click.echo(f"  {location}")
        if result.booking_url:
            click.echo(f"  {result.booking_url}")
    if len(ordered) > DISPLAY_LIMIT:
        click.echo(
            "Showing 50 results; more results exist. Narrow --search or --state.",
            err=True,
        )


def render_stays(stays: list["AvailabilityStay"]) -> None:
    """Display qualifying dates, provider identities and booking links."""
    if not stays:
        click.echo("No matching campsite stays found in this check.")
        return
    for stay in stays:
        target = stay.campground
        click.echo(
            f"{target.provider_name} | Campground {target.campground_id}: {target.campground_name}"
        )
        if target.recreation_area_id is not None:
            click.echo(
                f"  Recreation area {target.recreation_area_id}: {target.recreation_area_name or ''}"
            )
        count = (stay.checkout - stay.arrival).days
        click.echo(
            f"  Campsite {stay.campsite_id}: {stay.campsite_name} | {stay.arrival.isoformat()} to {stay.checkout.isoformat()} | {count} night(s)"
        )
        if stay.booking_url:
            click.echo(f"  {stay.booking_url}")
