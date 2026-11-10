"""Configure Rich CLI logging and print discovery and availability tables."""

import asyncio
import logging
import os
import sys
from collections.abc import Mapping, Sequence
from typing import TYPE_CHECKING

import click
import rich.traceback
from rich.console import Console
from rich.logging import RichHandler
from rich.measure import Measurement
from rich.table import Table
from rich.text import Text

from camply.__about__ import __version__
from camply.cli.discovery import DISPLAY_LIMIT, identity_key
from camply.providers.dto import ProviderSearchResult, SearchEntityType

if TYPE_CHECKING:
    from camply.core.search import AvailabilityStay
    from camply.db.models import Provider
    from camply.providers.base import BaseProvider

CAMPLY_LOG_LEVEL = logging.INFO + 1
logging.addLevelName(CAMPLY_LOG_LEVEL, "CAMPLY")
logger = logging.getLogger("camply.cli")

_LOG_PREFIX_WIDTH = 36
_PROBE_WIDTH = 2000
_DEFAULT_HEIGHT = 25


class CamplyRichHandler(RichHandler):
    """Rich logging handler that styles custom CAMPLY log levels and prevents truncation."""

    def get_level_text(self, record: logging.LogRecord) -> Text:
        """Render the custom CAMPLY level with standard Rich info styling."""
        if record.levelno == CAMPLY_LOG_LEVEL:
            return Text.styled(record.levelname.ljust(8), "logging.level.info")
        return super().get_level_text(record)

    def emit(self, record: logging.LogRecord) -> None:
        """Ensure non-interactive logs are not wrapped or truncated at 80 columns."""
        renderable = self.render_message(record, self.format(record))
        probe = self.console.options.update_width(_PROBE_WIDTH)
        needed = (
            Measurement.get(self.console, probe, renderable).maximum + _LOG_PREFIX_WIDTH
        )
        old_width, old_height = self.console._width, self.console._height
        if (
            not self.console.is_terminal or self.console.is_dumb_terminal
        ) and self.console.width < needed:
            self.console._width = needed
            self.console._height = old_height or _DEFAULT_HEIGHT
        try:
            super().emit(record)
        finally:
            if not self.console.record:
                self.console._width, self.console._height = old_width, old_height


def log_camply(message: str, *args: object) -> None:
    """Log a message at the custom CAMPLY notification level."""
    logger.log(CAMPLY_LOG_LEVEL, message, *args)


def _stdout_console() -> Console:
    """Return the active stdout Rich console or a plain stdout console fallback."""
    for handler in logger.handlers:
        if isinstance(handler, CamplyRichHandler) and not handler.console.stderr:
            return handler.console
    return Console(stderr=False, no_color=True, highlight=False)


def print_table(table: Table) -> None:
    """Print a Rich table directly to stdout without logging prefixes or truncation."""
    console = _stdout_console()
    probe = console.options.update_width(_PROBE_WIDTH)
    needed = Measurement.get(console, probe, table).maximum
    old_width, old_height = console._width, console._height
    if console.width < needed:
        console._width = needed
        console._height = old_height or _DEFAULT_HEIGHT
    try:
        console.print(table)
    finally:
        if not console.record:
            console._width, console._height = old_width, old_height


def set_up_logging(*, debug: bool = False) -> logging.Logger:
    """Configure Rich (or Python) CLI logging with stdout/stderr stream separation."""
    if debug:
        log_level: int = logging.DEBUG
    else:
        env_level = os.environ.get("LOG_LEVEL", "INFO").strip().upper()
        resolved = getattr(logging, env_level, logging.INFO)
        log_level = (
            resolved
            if isinstance(resolved, int) and resolved > logging.DEBUG
            else logging.INFO
        )
    handler_mode = os.environ.get("CAMPLY_LOG_HANDLER", "rich").strip().lower()
    if handler_mode == "python":
        formatter: logging.Formatter = logging.Formatter(
            "%(asctime)s [%(levelname)8s]: %(message)s"
        )
        stdout_handler: logging.Handler = logging.StreamHandler(sys.stdout)
        stderr_handler: logging.Handler = logging.StreamHandler(sys.stderr)
        stdout_handler.setLevel(log_level)
        stderr_handler.setLevel(log_level)
    else:
        formatter = logging.Formatter(datefmt="[%Y-%m-%d %H:%M:%S]", fmt="%(message)s")
        stdout_handler = CamplyRichHandler(
            level=log_level,
            console=Console(stderr=False),
            rich_tracebacks=True,
            omit_repeated_times=False,
            show_path=False,
        )
        stderr_handler = CamplyRichHandler(
            level=log_level,
            console=Console(stderr=True),
            rich_tracebacks=True,
            omit_repeated_times=False,
            show_path=False,
        )
    stdout_handler.setFormatter(formatter)
    stderr_handler.setFormatter(formatter)
    stdout_handler.addFilter(
        lambda record: record.levelno in (logging.INFO, CAMPLY_LOG_LEVEL)
    )
    stderr_handler.addFilter(
        lambda record: record.levelno not in (logging.INFO, CAMPLY_LOG_LEVEL)
    )
    logger.handlers = [stdout_handler, stderr_handler]
    logger.setLevel(log_level)
    logger.propagate = False
    rich.traceback.install(show_locals=False, suppress=[click, asyncio])
    log_camply("camply, the campsite finder ⛺️")
    if debug:
        logger.debug("Setting up camply debugging")
        logger.debug("Camply Version: %s", __version__)
        logger.debug("Python Version: %s", sys.version.split(" ")[0])
        logger.debug("Platform: %s", sys.platform)
    return logger


def diagnostic(message: str, debug: bool, *, provider: str | None = None) -> None:
    """Initialize CLI logging, announce the selected provider and emit debug diagnostics."""
    set_up_logging(debug=debug)
    if provider is not None:
        logger.info('Using Camply Provider: "%s"', provider)
    logger.debug("Debug: %s", message)


def _format_parent(name: str | None, identifier: str | None) -> str:
    """Format recreation-area name and ID consistently for table cells."""
    if name and identifier is not None:
        return f"{name} (#{identifier})"
    if name:
        return name
    if identifier is not None:
        return f"#{identifier}"
    return ""


def _format_location(name: str, city: str | None, state: str | None) -> str:
    """Append concise city/state context to an entity name when available."""
    place = ", ".join(value for value in (city, state) if value)
    return f"{name} ({place})" if place else name


def render_providers(
    entries: Mapping[str, tuple[type["BaseProvider"], "Provider"]],
) -> None:
    """Print supported camping providers and capabilities in a Rich table."""
    logger.info("camply currently supports %s providers:", len(entries))
    table = Table(title="Camping Providers")
    table.add_column("Provider", style="cyan", no_wrap=True)
    table.add_column("Capabilities", no_wrap=True)
    for name, (_, identity) in entries.items():
        areas = (
            "no recreation-area catalog"
            if name == "ReserveAmerica"
            else "recreation-area discovery"
        )
        label = f"{name} ({identity.name})" if name != identity.name else name
        table.add_row(
            label,
            f"{areas}; campground discovery; campground availability",
        )
    print_table(table)


def render_discovery(results: Sequence[ProviderSearchResult], *, empty: str) -> None:
    """Print unique discovery results in a Rich table and report display truncation."""
    ordered = sorted(
        {identity_key(result): result for result in results}.values(),
        key=identity_key,
    )
    if not ordered:
        logger.info(empty)
        return
    displayed = ordered[:DISPLAY_LIMIT]
    provider_name = displayed[0].provider_name
    is_rec_area = all(
        result.entity_type == SearchEntityType.RECREATION_AREA for result in displayed
    )
    if is_rec_area:
        logger.info("%s recreation areas found.", len(displayed))
        table = Table(title=f"{provider_name} Recreation Areas")
        table.add_column("ID", style="magenta", no_wrap=True)
        table.add_column("Recreation Area", style="green", no_wrap=True)
        table.add_column("Location", no_wrap=True)
        for result in displayed:
            location = ", ".join(
                value for value in (result.city, result.state, result.country) if value
            )
            table.add_row(
                result.recreation_area_id or "",
                result.recreation_area_name or "",
                location,
            )
    else:
        logger.info("%s Matching Campgrounds Found", len(displayed))
        table = Table(title=f"{provider_name} Campgrounds")
        table.add_column("ID", style="magenta", no_wrap=True)
        table.add_column("Campground", style="green", no_wrap=True)
        table.add_column("Recreation Area", no_wrap=True)
        for result in displayed:
            rec_area = _format_parent(
                result.recreation_area_name, result.recreation_area_id
            )
            table.add_row(
                result.campground_id or "",
                _format_location(
                    result.campground_name or "", result.city, result.state
                ),
                rec_area,
            )
    print_table(table)
    if len(ordered) > DISPLAY_LIMIT:
        logger.warning(
            "Showing 50 results; more results exist. Narrow --search or --state."
        )


def render_stays(stays: list["AvailabilityStay"]) -> None:
    """Print qualifying stays in a Rich table."""
    emoji = "⛺️" if stays else "❌"
    logger.info(
        "%s%s Reservable Campsites Matching Search Preferences",
        f"{emoji} " * 4,
        len(stays),
    )
    if not stays:
        logger.info("No matching campsite stays found in this check.")
        return
    provider_name = stays[0].campground.provider_name
    table = Table(title=f"{provider_name} Available Campsites")
    table.add_column("Campground", style="green", no_wrap=True)
    table.add_column("Campsite", style="magenta", no_wrap=True)
    table.add_column("Dates", no_wrap=True)
    for stay in stays:
        target = stay.campground
        rec_area = _format_parent(
            target.recreation_area_name, target.recreation_area_id
        )
        campground_label = f"{target.campground_name} (#{target.campground_id})"
        if rec_area:
            campground_label = f"{campground_label} — {rec_area}"
        campsite_label = f"{stay.campsite_name} (#{stay.campsite_id})"
        nights = (stay.checkout - stay.arrival).days
        table.add_row(
            campground_label,
            campsite_label,
            f"{stay.arrival.isoformat()} to {stay.checkout.isoformat()} ({nights} night(s))",
        )
    print_table(table)
