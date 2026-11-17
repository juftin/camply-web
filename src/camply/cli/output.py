"""Configure Rich CLI logging and log discovery and availability in classic camply style."""

import asyncio
import json
import logging
import os
import sys
from collections.abc import Mapping, Sequence
from datetime import date
from typing import TYPE_CHECKING

import click
import rich.traceback
from rich.console import Console
from rich.logging import RichHandler
from rich.measure import Measurement
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

_LOG_PREFIX_WIDTH = 64
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


def set_up_logging(*, debug: bool = False, stderr_only: bool = False) -> logging.Logger:
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
    if stderr_only:
        logger.handlers = [stderr_handler]
    else:
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


def diagnostic(
    message: str,
    debug: bool,
    *,
    provider: str | None = None,
    stderr_only: bool = False,
) -> None:
    """Initialize CLI logging, announce the selected provider and emit debug diagnostics."""
    set_up_logging(debug=debug, stderr_only=stderr_only)
    if provider is not None:
        logger.info('Using Camply Provider: "%s"', provider)
    logger.debug("Debug: %s", message)


def _format_recreation_area_name(
    name: str | None, state: str | None, country: str | None = None
) -> str:
    """Format a recreation-area name with state or country suffix like classic camply."""
    area = name or ""
    location = state or country or ""
    if area and location:
        return f"{area}, {location}"
    return area or location


def format_recreation_area_log(result: ProviderSearchResult) -> str:
    """Format a recreation-area search result in classic camply log style."""
    area = _format_recreation_area_name(
        result.recreation_area_name, result.state, result.country
    )
    return f"⛰  {area} (#{result.recreation_area_id})"


def format_campground_log(result: ProviderSearchResult) -> str:
    """Format a campground search result in classic camply log style."""
    area = _format_recreation_area_name(
        result.recreation_area_name, result.state, result.country
    )
    if result.recreation_area_id is not None:
        prefix = f"⛰  {area} (#{result.recreation_area_id}) - "
    elif area:
        prefix = f"⛰  {area} - "
    else:
        prefix = ""
    return f"{prefix}🏕  {result.campground_name} (#{result.campground_id})"


def _format_filter_capabilities(provider_class: type["BaseProvider"]) -> str:
    """Describe site-attribute filters supported by a provider."""
    caps = provider_class.filter_capabilities
    supported: list[str] = []
    if caps.preferred_types:
        supported.append("campsite type")
    if caps.require_electric:
        supported.append("electric hookup")
    if caps.require_accessible:
        supported.append("ADA accessibility")
    if caps.min_rv_length:
        supported.append("RV length")
    return f"filters: {', '.join(supported)}" if supported else "filters: none"


def render_providers(
    entries: Mapping[str, tuple[type["BaseProvider"], "Provider"]],
) -> None:
    """Log supported camping providers and capabilities in classic camply style."""
    logger.info("camply currently supports %s providers:", len(entries))
    for name, (provider_class, identity) in entries.items():
        areas = (
            "no recreation-area catalog"
            if name == "ReserveAmerica"
            else "recreation-area discovery"
        )
        filters = _format_filter_capabilities(provider_class)
        logger.info(
            '    "%s":    %s (%s; campground discovery; campground availability; %s)',
            name,
            identity.name,
            areas,
            filters,
        )


def render_discovery(
    results: Sequence[ProviderSearchResult],
    *,
    empty: str,
    limit: int = DISPLAY_LIMIT,
) -> None:
    """Log unique discovery results in classic camply style and report truncation."""
    ordered = sorted(
        {identity_key(result): result for result in results}.values(),
        key=identity_key,
    )
    if not ordered:
        logger.info(empty)
        return
    displayed = ordered[:limit]
    is_rec_area = all(
        result.entity_type == SearchEntityType.RECREATION_AREA for result in displayed
    )
    if is_rec_area:
        logger.info("%s recreation areas found.", len(displayed))
        for result in displayed:
            logger.info(format_recreation_area_log(result))
    else:
        logger.info("%s Matching Campgrounds Found", len(displayed))
        for result in displayed:
            logger.info(format_campground_log(result))
    if len(ordered) > limit:
        logger.warning(
            "Showing %s results; more results exist. Narrow --search or --state.",
            limit,
        )


def stay_booking_url(stay: "AvailabilityStay") -> str:
    """Resolve campsite-level booking URL when using Recreation.gov campground URLs."""
    if stay.booking_url.startswith("https://www.recreation.gov/camping/campgrounds/"):
        return f"https://www.recreation.gov/camping/campsites/{stay.campsite_id}"
    return stay.booking_url


_stay_booking_url = stay_booking_url


def render_stays(stays: list["AvailabilityStay"]) -> None:
    """Log qualifying stays grouped by arrival date and campground in classic camply style."""
    emoji = "⛺️" if stays else "❌"
    logger.info(
        "%s%s Reservable Campsites Matching Search Preferences",
        f"{emoji} " * 4,
        len(stays),
    )
    if not stays:
        logger.info("No matching campsite stays found in this check.")
        return
    by_arrival: dict[date, list[AvailabilityStay]] = {}
    for stay in sorted(
        stays,
        key=lambda item: (
            item.arrival,
            item.campground.recreation_area_name or "",
            item.campground.campground_name,
            (item.checkout - item.arrival).days,
            item.campsite_id,
        ),
    ):
        by_arrival.setdefault(stay.arrival, []).append(stay)
    for arrival, date_stays in by_arrival.items():
        logger.info(
            "📅 %s 🏕  %s sites",
            arrival.strftime("%a, %B %d"),
            len(date_stays),
        )
        by_location: dict[tuple[str, str], list[AvailabilityStay]] = {}
        for stay in date_stays:
            target = stay.campground
            rec_area = _format_recreation_area_name(
                target.recreation_area_name, target.state, target.country
            )
            by_location.setdefault((rec_area, target.campground_name), []).append(stay)
        for (rec_area, campground_name), campground_stays in by_location.items():
            location_label = (
                f"{rec_area}  🏕  {campground_name}"
                if rec_area
                else f"🏕  {campground_name}"
            )
            logger.info(
                "\t⛰️  %s: ⛺ %s sites",
                location_label,
                len(campground_stays),
            )
            by_nights: dict[int, set[str]] = {}
            for stay in campground_stays:
                nights = (stay.checkout - stay.arrival).days
                url = _stay_booking_url(stay)
                if url:
                    by_nights.setdefault(nights, set()).add(url)
            for nights, urls in sorted(by_nights.items()):
                suffix = "s" if nights > 1 else ""
                for url in sorted(urls):
                    logger.info("\t\t🔗 %s (%s night%s)", url, nights, suffix)


def render_providers_json(
    entries: Mapping[str, tuple[type["BaseProvider"], "Provider"]],
) -> None:
    """Emit supported camping providers and filter capabilities as JSON on stdout."""
    payload = [
        {
            "name": name,
            "display_name": identity.name,
            "provider_id": identity.id,
            "url": identity.url,
            "recreation_area_discovery": name != "ReserveAmerica",
            "filter_capabilities": {
                "preferred_types": provider_class.filter_capabilities.preferred_types,
                "require_electric": provider_class.filter_capabilities.require_electric,
                "require_accessible": provider_class.filter_capabilities.require_accessible,
                "min_rv_length": provider_class.filter_capabilities.min_rv_length,
            },
        }
        for name, (provider_class, identity) in entries.items()
    ]
    click.echo(json.dumps(payload, indent=2))


def render_discovery_json(
    results: Sequence[ProviderSearchResult],
    *,
    limit: int = DISPLAY_LIMIT,
) -> None:
    """Emit unique discovery results as JSON on stdout and log truncation to stderr."""
    ordered = sorted(
        {identity_key(result): result for result in results}.values(),
        key=identity_key,
    )
    displayed = ordered[:limit]
    if len(ordered) > limit:
        logger.warning(
            "Showing %s results; more results exist. Narrow --search or --state.",
            limit,
        )
    click.echo(
        json.dumps([item.model_dump(mode="json") for item in displayed], indent=2)
    )


def render_stays_json(stays: Sequence["AvailabilityStay"]) -> None:
    """Emit qualifying stays as a JSON array on stdout."""
    payload = [
        {
            "provider_id": stay.campground.provider_id,
            "provider_name": stay.campground.provider_name,
            "recreation_area_id": stay.campground.recreation_area_id,
            "recreation_area_name": stay.campground.recreation_area_name,
            "campground_id": stay.campground.campground_id,
            "campground_name": stay.campground.campground_name,
            "campsite_id": stay.campsite_id,
            "campsite_name": stay.campsite_name,
            "arrival": stay.arrival.isoformat(),
            "checkout": stay.checkout.isoformat(),
            "nights": (stay.checkout - stay.arrival).days,
            "booking_url": stay_booking_url(stay),
        }
        for stay in stays
    ]
    click.echo(json.dumps(payload, indent=2))
