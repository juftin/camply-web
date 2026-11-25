"""Reusable CLI options and calendar-date parsing without runtime or provider imports."""

import re
from collections.abc import Callable
from datetime import date
from pathlib import Path
from typing import Any, TypeVar

import click

_F = TypeVar("_F", bound=Callable[..., Any])


class ISODate(click.ParamType):
    """Accept ISO calendar dates with the documented YYYY-MM-DD spelling."""

    name = "YYYY-MM-DD"

    def convert(
        self, value: object, param: click.Parameter | None, ctx: click.Context | None
    ) -> date:
        if isinstance(value, date):
            return value
        try:
            if (
                not isinstance(value, str)
                or re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value) is None
            ):
                raise ValueError
            return date.fromisoformat(value)
        except ValueError:
            self.fail("Use a valid ISO calendar date in YYYY-MM-DD format.", param, ctx)


def resolve_debug(ctx: click.Context, command_debug: bool | None) -> bool:
    """Respect an explicit command-level no-debug over the root switch."""
    return (
        command_debug
        if command_debug is not None
        else bool(ctx.find_root().params.get("debug"))
    )


def provider(*, root: bool = False) -> Callable[[_F], _F]:
    """Select a provider, preserving the root and command help descriptions."""
    return click.option(
        "--provider",
        default=None,
        help=(
            "Camping provider (default: RecreationDotGov; CAMPLY_PROVIDER fallback)."
            if root
            else "Camping provider; overrides the root selection."
        ),
    )


def debug(*, root: bool = False) -> Callable[[_F], _F]:
    """Allow explicit enabling or disabling of safe terminal diagnostics."""
    return click.option(
        "--debug/--no-debug",
        default=None,
        help="Show safe diagnostic messages on stderr."
        if root
        else "Show safe diagnostics on stderr.",
    )


def search() -> Callable[[_F], _F]:
    """Filter discovery by text, with blank text browsing the catalog."""
    return click.option("--search", default="", help="Text to find; omit to browse.")


def state() -> Callable[[_F], _F]:
    """Filter discovery by a two-letter state code."""
    return click.option("--state", default=None, help="Two-letter state code.")


def rec_area() -> Callable[[_F], _F]:
    """Select repeatable exact recreation-area IDs."""
    return click.option(
        "--rec-area",
        multiple=True,
        help="Exact recreation-area ID; repeat to combine areas.",
    )


def campground() -> Callable[[_F], _F]:
    """Select repeatable exact campground IDs with precedence over area IDs."""
    return click.option(
        "--campground",
        multiple=True,
        help="Exact campground ID; overrides recreation areas.",
    )


def campsite() -> Callable[[_F], _F]:
    """Select repeatable exact campsite IDs or names within parent targets."""
    return click.option(
        "--campsite",
        multiple=True,
        help="Exact campsite ID or name within selected campgrounds/areas; repeat to combine.",
    )


def campsite_type() -> Callable[[_F], _F]:
    """Filter availability by standardized campsite types."""
    return click.option(
        "--campsite-type",
        type=click.Choice(["TENT", "RV", "CABIN", "OTHER"], case_sensitive=False),
        multiple=True,
        help="Eligible campsite type (TENT, RV, CABIN, OTHER); repeat to combine.",
    )


def electric() -> Callable[[_F], _F]:
    """Require campsites with electric hookups."""
    return click.option(
        "--electric",
        is_flag=True,
        default=False,
        help="Only match campsites with electric hookups.",
    )


def accessible() -> Callable[[_F], _F]:
    """Require ADA-accessible campsites."""
    return click.option(
        "--accessible",
        is_flag=True,
        default=False,
        help="Only match ADA-accessible campsites.",
    )


def rv_length() -> Callable[[_F], _F]:
    """Require a minimum compatible RV or trailer length in whole feet."""
    return click.option(
        "--rv-length",
        type=click.IntRange(min=1, max=200),
        default=None,
        help="Minimum required RV or trailer length in feet (1-200).",
    )


def notifications(*, required: bool = False) -> Callable[[_F], _F]:
    """Select external notification channels for availability or test delivery."""
    return click.option(
        "--notifications",
        type=click.Choice(
            ["pushover", "ntfy", "webhook", "discord", "slack", "telegram"],
            case_sensitive=False,
        ),
        multiple=True,
        required=required,
        help=(
            "External notification channel (pushover, ntfy, webhook, discord, slack, telegram); "
            "repeat to combine."
        ),
    )


def max_notifications() -> Callable[[_F], _F]:
    """Cap notifications sent per channel per check cycle, summarizing overflow."""
    return click.option(
        "--max-notifications",
        type=click.IntRange(min=1, max=100),
        default=5,
        show_default=True,
        help=(
            "Maximum notifications per channel per check cycle (1-100); "
            "excess stays are collapsed into a summary alert."
        ),
    )


def state_file() -> Callable[[_F], _F]:
    """Specify a local JSON file path for seen-opening alert deduplication."""
    return click.option(
        "--state-file",
        type=click.Path(dir_okay=False, path_type=Path),
        default=None,
        help="JSON file path to persist seen openings across runs.",
    )


def search_once() -> Callable[[_F], _F]:
    """Run a single availability check cycle and exit."""
    return click.option(
        "--search-once",
        is_flag=True,
        default=False,
        help="Check availability once and exit.",
    )


def stop_on_match() -> Callable[[_F], _F]:
    """Stop continuous polling as soon as a check finds qualifying stays."""
    return click.option(
        "--stop-on-match",
        is_flag=True,
        default=False,
        help="Exit after the first check cycle that finds matching stays.",
    )


def interval() -> Callable[[_F], _F]:
    """Configure the wait interval in minutes between continuous checks."""
    return click.option(
        "--interval",
        type=click.IntRange(min=5),
        default=10,
        show_default=True,
        help="Polling interval in minutes between checks (minimum 5).",
    )


def limit() -> Callable[[_F], _F]:
    """Bound the maximum number of discovery results displayed."""
    return click.option(
        "--limit",
        type=click.IntRange(min=1, max=500),
        default=50,
        show_default=True,
        help="Maximum discovery results to display (1-500).",
    )


def json_output() -> Callable[[_F], _F]:
    """Emit structured JSON on stdout while routing logs to stderr."""
    return click.option(
        "--json",
        "json_output",
        is_flag=True,
        default=False,
        help="Emit machine-readable JSON on stdout.",
    )


def timeout() -> Callable[[_F], _F]:
    """Bound role health checks with a strictly positive network timeout."""
    return click.option(
        "--timeout",
        default=5.0,
        type=click.FloatRange(min=0, min_open=True),
        show_default=True,
    )
