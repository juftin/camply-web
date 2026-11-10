"""Configure Rich CLI logging and render discovery and availability tables."""

import asyncio
import io
import logging
import os
import sys
from collections.abc import Mapping, Sequence
from typing import TYPE_CHECKING

import click
import rich.traceback
from rich.console import Console, ConsoleRenderable
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
    """Rich logging handler that renders Rich tables and custom CAMPLY log levels."""

    def get_level_text(self, record: logging.LogRecord) -> Text:
        """Render the custom CAMPLY level with standard Rich info styling."""
        if record.levelno == CAMPLY_LOG_LEVEL:
            return Text.styled(record.levelname.ljust(8), "logging.level.info")
        return super().get_level_text(record)

    def render_message(
        self, record: logging.LogRecord, message: str
    ) -> ConsoleRenderable:
        """Pass Rich renderables such as Table through without string coercion."""
        if isinstance(record.msg, ConsoleRenderable):
            return record.msg
        return super().render_message(record, message)

    def emit(self, record: logging.LogRecord) -> None:
        """Ensure tables and non-interactive logs are not truncated at 80 columns."""
        renderable = (
            record.msg
            if isinstance(record.msg, ConsoleRenderable)
            else self.render_message(record, self.format(record))
        )
        probe = self.console.options.update_width(_PROBE_WIDTH)
        needed = (
            Measurement.get(self.console, probe, renderable).maximum + _LOG_PREFIX_WIDTH
        )
        old_width, old_height = self.console._width, self.console._height
        if (
            not self.console.is_terminal
            or self.console.is_dumb_terminal
            or isinstance(record.msg, ConsoleRenderable)
        ) and self.console.width < needed:
            self.console._width = needed
            self.console._height = old_height or _DEFAULT_HEIGHT
        try:
            super().emit(record)
        finally:
            if not self.console.record:
                self.console._width, self.console._height = old_width, old_height


class CamplyPythonFormatter(logging.Formatter):
    """Plain Python formatter that renders Rich tables when CAMPLY_LOG_HANDLER=python."""

    def format(self, record: logging.LogRecord) -> str:
        """Format standard messages or render Rich tables into plain text."""
        if isinstance(record.msg, ConsoleRenderable):
            buffer = io.StringIO()
            probe_console = Console(file=buffer, no_color=True, highlight=False)
            needed = Measurement.get(
                probe_console,
                probe_console.options.update_width(_PROBE_WIDTH),
                record.msg,
            ).maximum
            render_console = Console(
                file=buffer,
                width=max(80, needed),
                height=_DEFAULT_HEIGHT,
                no_color=True,
                highlight=False,
            )
            render_console.print(record.msg)
            copied = logging.makeLogRecord(record.__dict__)
            copied.msg = "\n" + buffer.getvalue().rstrip("\n")
            copied.args = ()
            return super().format(copied)
        return super().format(record)


def log_camply(message: str, *args: object) -> None:
    """Log a message at the custom CAMPLY notification level."""
    logger.log(CAMPLY_LOG_LEVEL, message, *args)


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
        formatter: logging.Formatter = CamplyPythonFormatter(
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


def render_providers(
    entries: Mapping[str, tuple[type["BaseProvider"], "Provider"]],
) -> None:
    """Log supported camping providers and capabilities in a Rich table."""
    logger.info("camply currently supports %s providers:", len(entries))
    table = Table(title="Camping Providers")
    table.add_column("Provider", style="cyan", no_wrap=True)
    table.add_column("Name", style="green", no_wrap=True)
    table.add_column("Capabilities", no_wrap=True)
    for name, (_, identity) in entries.items():
        areas = (
            "no recreation-area catalog"
            if name == "ReserveAmerica"
            else "recreation-area discovery"
        )
        table.add_row(
            name,
            identity.name,
            f"{areas}; campground discovery; campground availability",
        )
    logger.info(table)


def render_discovery(results: Sequence[ProviderSearchResult], *, empty: str) -> None:
    """Log unique discovery results to a Rich table and report display truncation."""
    ordered = sorted(
        {identity_key(result): result for result in results}.values(),
        key=identity_key,
    )
    if not ordered:
        logger.info(empty)
        return
    displayed = ordered[:DISPLAY_LIMIT]
    is_rec_area = all(
        result.entity_type == SearchEntityType.RECREATION_AREA for result in displayed
    )
    if is_rec_area:
        logger.info("%s recreation areas found.", len(displayed))
        table = Table(title="Recreation Areas")
        table.add_column("Provider", style="cyan", no_wrap=True)
        table.add_column("ID", style="magenta", no_wrap=True)
        table.add_column("Recreation Area", style="green", no_wrap=True)
        table.add_column("Location", no_wrap=True)
        table.add_column("Booking URL", style="bright_blue", no_wrap=True)
        for result in displayed:
            location = ", ".join(
                value for value in (result.city, result.state, result.country) if value
            )
            table.add_row(
                result.provider_name,
                result.recreation_area_id or "",
                result.recreation_area_name or "",
                location,
                result.booking_url,
            )
    else:
        logger.info("%s Matching Campgrounds Found", len(displayed))
        table = Table(title="Campgrounds")
        table.add_column("Provider", style="cyan", no_wrap=True)
        table.add_column("ID", style="magenta", no_wrap=True)
        table.add_column("Campground", style="green", no_wrap=True)
        table.add_column("Recreation Area", no_wrap=True)
        table.add_column("Location", no_wrap=True)
        table.add_column("Booking URL", style="bright_blue", no_wrap=True)
        for result in displayed:
            rec_area = _format_parent(
                result.recreation_area_name, result.recreation_area_id
            )
            location = ", ".join(
                value for value in (result.city, result.state, result.country) if value
            )
            table.add_row(
                result.provider_name,
                result.campground_id or "",
                result.campground_name or "",
                rec_area,
                location,
                result.booking_url,
            )
    logger.info(table)
    if len(ordered) > DISPLAY_LIMIT:
        logger.warning(
            "Showing 50 results; more results exist. Narrow --search or --state."
        )


def render_stays(stays: list["AvailabilityStay"]) -> None:
    """Log qualifying stays, provider identities and booking links in a Rich table."""
    emoji = "⛺️" if stays else "❌"
    logger.info(
        "%s%s Reservable Campsites Matching Search Preferences",
        f"{emoji} " * 4,
        len(stays),
    )
    if not stays:
        logger.info("No matching campsite stays found in this check.")
        return
    table = Table(title="Available Campsites")
    table.add_column("Provider", style="cyan", no_wrap=True)
    table.add_column("Recreation Area", no_wrap=True)
    table.add_column("Campground", style="green", no_wrap=True)
    table.add_column("Campsite", style="magenta", no_wrap=True)
    table.add_column("Arrival", no_wrap=True)
    table.add_column("Checkout", no_wrap=True)
    table.add_column("Nights", justify="right", no_wrap=True)
    table.add_column("Booking URL", style="bright_blue", no_wrap=True)
    for stay in stays:
        target = stay.campground
        rec_area = _format_parent(
            target.recreation_area_name, target.recreation_area_id
        )
        campground_label = f"{target.campground_name} (#{target.campground_id})"
        campsite_label = f"{stay.campsite_name} (#{stay.campsite_id})"
        nights = (stay.checkout - stay.arrival).days
        table.add_row(
            target.provider_name,
            rec_area,
            campground_label,
            campsite_label,
            stay.arrival.isoformat(),
            stay.checkout.isoformat(),
            f"{nights} night(s)",
            stay.booking_url,
        )
    logger.info(table)
