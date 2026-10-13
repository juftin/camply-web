"""
Terminal output rendering using Rich for tables, panels, and JSON.
"""

import json
from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from camply_core.models import CampsiteDTO
from camply_core.providers.recreation_gov.models import (
    RecDotGovCampground,
    RecDotGovRecreationArea,
)

console: Console = Console()
# Global Rich Console instance for standard output.

error_console: Console = Console(stderr=True)
# Global Rich Console instance for error output.

_MAX_INLINE_DATES: int = 3
# Maximum number of individual dates to display comma-separated before condensing.


def print_campsites_table(campsites: list[CampsiteDTO]) -> None:
    """
    Render a formatted table of campsite availability results.

    Parameters
    ----------
    campsites : list[CampsiteDTO]
        List of campsite availability items.
    """
    if not campsites:
        console.print(
            "[yellow]No campsite openings found for the specified criteria.[/yellow]"
        )
        return

    table = Table(
        title="🏕️ Campsite Availabilities Found",
        header_style="bold magenta",
        show_header=True,
        box=None,
    )
    table.add_column("Campsite ID", style="dim", justify="right")
    table.add_column("Campsite Name", style="bold cyan")
    table.add_column("Type", style="green")
    table.add_column("Capacity", justify="right")
    table.add_column("Electric", justify="center")
    table.add_column("Available Dates", style="yellow")
    table.add_column("Booking URL", style="blue underline")

    for site in campsites:
        date_strs = [d.isoformat() for d in site.available_dates]
        display_dates = (
            ", ".join(date_strs)
            if len(date_strs) <= _MAX_INLINE_DATES
            else f"{date_strs[0]} .. {date_strs[-1]} ({len(date_strs)} nights)"
        )
        table.add_row(
            str(site.campsite_id),
            site.campsite_name,
            str(site.campsite_type.value),
            str(site.capacity),
            "⚡ Yes" if site.is_electric else "No",
            display_dates,
            site.booking_url or "N/A",
        )

    console.print(table)


def print_campgrounds_table(campgrounds: list[RecDotGovCampground]) -> None:
    """
    Render a formatted table of campgrounds.

    Parameters
    ----------
    campgrounds : list[RecDotGovCampground]
        List of campgrounds returned from search.
    """
    if not campgrounds:
        console.print("[yellow]No campgrounds found matching query.[/yellow]")
        return

    table = Table(
        title="⛺ Campgrounds Found",
        header_style="bold blue",
        show_header=True,
        box=None,
    )
    table.add_column("Facility ID", style="dim", justify="right")
    table.add_column("Campground Name", style="bold green")
    table.add_column("Parent Rec Area ID", justify="right")
    table.add_column("Reservable", justify="center")

    for cg in campgrounds:
        table.add_row(
            str(cg.FacilityID),
            cg.FacilityName or "Unnamed",
            str(cg.ParentRecAreaID or "-"),
            "✅ Yes" if cg.Reservable else "❌ No",
        )

    console.print(table)


def print_rec_areas_table(rec_areas: list[RecDotGovRecreationArea]) -> None:
    """
    Render a formatted table of recreation areas.

    Parameters
    ----------
    rec_areas : list[RecDotGovRecreationArea]
        List of recreation areas returned from search.
    """
    if not rec_areas:
        console.print("[yellow]No recreation areas found matching query.[/yellow]")
        return

    table = Table(
        title="🌲 Recreation Areas Found",
        header_style="bold green",
        show_header=True,
        box=None,
    )
    table.add_column("Rec Area ID", style="dim", justify="right")
    table.add_column("Recreation Area Name", style="bold cyan")

    for ra in rec_areas:
        table.add_row(
            str(ra.RecAreaID),
            ra.RecAreaName or "Unnamed",
        )

    console.print(table)


def print_json_output(data: Any) -> None:
    """
    Output data serialized as pretty JSON.

    Parameters
    ----------
    data : Any
        Object, dict, or list to serialize and print.
    """
    if hasattr(data, "model_dump"):
        dumped = data.model_dump(mode="json")
    elif isinstance(data, list) and data and hasattr(data[0], "model_dump"):
        dumped = [item.model_dump(mode="json") for item in data]
    else:
        dumped = data

    console.print(json.dumps(dumped, indent=2, default=str))


def print_banner(title: str, message: str, style: str = "bold green") -> None:
    """
    Render a stylized panel notification.

    Parameters
    ----------
    title : str
        Panel header title.
    message : str
        Body content of the panel.
    style : str
        Border and header color style.
    """
    console.print(Panel(message, title=title, border_style=style))


def print_error(message: str) -> None:
    """
    Print an error message to standard error.

    Parameters
    ----------
    message : str
        Error text to output.
    """
    error_console.print(f"[bold red]Error:[/bold red] {message}")


def print_info(message: str) -> None:
    """
    Print an informational status message.

    Parameters
    ----------
    message : str
        Information text to output.
    """
    console.print(f"[bold blue][INFO][/bold blue] {message}")
