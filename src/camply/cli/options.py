"""Reusable CLI options and calendar-date parsing without runtime or provider imports."""

import re
from collections.abc import Callable
from datetime import date
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


def timeout() -> Callable[[_F], _F]:
    """Bound role health checks with a strictly positive network timeout."""
    return click.option(
        "--timeout",
        default=5.0,
        type=click.FloatRange(min=0, min_open=True),
        show_default=True,
    )
