"""Plain terminal discovery and foreground availability commands."""

import asyncio
import contextlib
import os
import re
import signal
from collections.abc import Awaitable, Callable, Iterator, MutableMapping, Sequence
from datetime import date
from typing import TYPE_CHECKING, Any, NoReturn, TypeVar

import click
import structlog
from pydantic import ValidationError

from camply.db.data import providers as identities
from camply.db.models import Provider
from camply.providers import PROVIDERS
from camply.providers.base import BaseProvider
from camply.providers.dto import (
    CampgroundSearchResult,
    ProviderSearchQuery,
    ProviderSearchResult,
    SearchEntityType,
)

if TYPE_CHECKING:
    from camply.core.search import AvailabilityStay

_STATE_CODE_LENGTH = 2
_DISPLAY_LIMIT = 50
_RESULT_PROBE = _DISPLAY_LIMIT + 1
_T = TypeVar("_T")


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


def _entries() -> dict[str, tuple[type[BaseProvider], Provider]]:
    """Read registered identities without constructing clients or touching storage."""
    return {
        name: (PROVIDERS[identity.id], identity)
        for name, identity in vars(identities).items()
        if isinstance(identity, Provider) and identity.id in PROVIDERS
    }


def _selected_provider(
    ctx: click.Context, command_provider: str | None
) -> tuple[str, type[BaseProvider]]:
    """Resolve only the winning explicit option, environment value or default."""
    selected = command_provider
    if selected is None:
        selected = ctx.find_root().params.get("provider")
    if selected is None:
        selected = os.environ.get("CAMPLY_PROVIDER", "RecreationDotGov")
    for name, (provider_class, _) in _entries().items():
        if selected.casefold() in {name.casefold(), provider_class.__name__.casefold()}:
            return name, provider_class
    raise click.BadParameter(
        f"Unsupported provider {selected!r}. Run 'camply providers' for supported names; legacy deployments such as GoingToCamp are deferred.",
        param_hint="--provider",
    )


def _debug(ctx: click.Context, command_debug: bool | None) -> bool:
    """Respect an explicit command-level no-debug over the root switch."""
    return (
        command_debug
        if command_debug is not None
        else bool(ctx.find_root().params.get("debug"))
    )


def _diagnostic(message: str, debug: bool) -> None:
    if debug:
        click.echo(f"Debug: {message}", err=True)


def _discard_provider_log(
    _: object, __: str, ___: MutableMapping[str, Any]
) -> NoReturn:
    """Keep provider response payloads and exception credentials out of terminal logs."""
    raise structlog.DropEvent


@contextlib.contextmanager
def _quiet_provider_logs() -> Iterator[None]:
    """Scope provider logging suppression to this foreground command only.

    Public diagnostics are emitted explicitly without HTTP headers, settings or
    exception payloads. Restoring configuration preserves serving behavior.
    """
    previous = structlog.get_config()
    structlog.configure(
        processors=[_discard_provider_log], cache_logger_on_first_use=False
    )
    try:
        yield
    finally:
        structlog.configure(**previous)


async def _cancellable(operation: Callable[[], Awaitable[_T]]) -> _T:
    """Translate termination into cancellation so owned-resource finally blocks run."""
    loop = asyncio.get_running_loop()
    task = asyncio.current_task()
    installed = False
    previous = signal.getsignal(signal.SIGTERM)
    if task is not None:
        try:
            loop.add_signal_handler(signal.SIGTERM, task.cancel)
            installed = True
        except (NotImplementedError, RuntimeError, ValueError):
            pass  # Windows and non-main-thread invocations have no loop signal API.
    try:
        return await operation()
    finally:
        if installed:
            loop.remove_signal_handler(signal.SIGTERM)
            signal.signal(signal.SIGTERM, previous)


def _run(operation: Callable[[], Awaitable[_T]]) -> _T:
    """Run async commands with sanitized failures and deterministic client cleanup."""
    try:
        with _quiet_provider_logs():
            return asyncio.run(_cancellable(operation))
    except (KeyboardInterrupt, asyncio.CancelledError) as exc:
        raise click.Abort() from exc
    except ValidationError as exc:
        raise click.ClickException(
            "Provider returned invalid data (ValidationError); try again later."
        ) from exc
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc
    except Exception as exc:
        raise click.ClickException(
            f"Provider request failed ({type(exc).__name__}); check connectivity and try again."
        ) from exc


def _ids(values: Sequence[str], option: str) -> tuple[str, ...]:
    result = tuple(dict.fromkeys(value.strip() for value in values))
    if any(not value for value in result):
        raise click.BadParameter("IDs must not be blank.", param_hint=option)
    return result


def _query(search: str, state: str | None) -> ProviderSearchQuery:
    if state is not None:
        state = state.strip().upper()
        if (
            len(state) != _STATE_CODE_LENGTH
            or not state.isascii()
            or not state.isalpha()
        ):
            raise click.BadParameter(
                "Use a two-letter state code.", param_hint="--state"
            )
    return ProviderSearchQuery(query=search.strip(), state=state, limit=_RESULT_PROBE)


def _identity_key(result: ProviderSearchResult) -> tuple[int, str, str]:
    return (
        result.provider_id,
        result.entity_type,
        result.campground_id or result.recreation_area_id or "",
    )


def _render_discovery(results: Sequence[ProviderSearchResult], *, empty: str) -> None:
    ordered = sorted(
        {_identity_key(result): result for result in results}.values(),
        key=_identity_key,
    )
    if not ordered:
        click.echo(empty)
        return
    for result in ordered[:_DISPLAY_LIMIT]:
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
    if len(ordered) > _DISPLAY_LIMIT:
        click.echo(
            "Showing 50 results; more results exist. Narrow --search or --state.",
            err=True,
        )


async def _targets(
    provider: BaseProvider,
    areas: Sequence[str],
    campgrounds: Sequence[str],
) -> list[CampgroundSearchResult]:
    """Resolve every selected ID before any availability request is allowed."""
    if campgrounds:
        results = [
            await provider.get_campground(identifier) for identifier in campgrounds
        ]
    else:
        results = []
        for area in areas:
            results.extend([result async for result in provider.iter_campgrounds(area)])
    return sorted(
        {_identity_key(result): result for result in results}.values(),
        key=_identity_key,
    )


@click.command(name="providers")
@click.option(
    "--debug/--no-debug", default=None, help="Show safe diagnostics on stderr."
)
@click.pass_context
def providers_cmd(ctx: click.Context, debug: bool | None) -> None:
    """List currently supported camping providers and discovery capabilities."""
    _diagnostic(
        "Listing registered providers without network access.", _debug(ctx, debug)
    )
    for name, (_, identity) in _entries().items():
        areas = (
            "no recreation-area catalog"
            if name == "ReserveAmerica"
            else "recreation-area discovery"
        )
        click.echo(
            f"{name} | {identity.name} | {areas}; campground discovery; campground availability"
        )


@click.command(name="recreation-areas")
@click.option(
    "--provider", default=None, help="Camping provider; overrides the root selection."
)
@click.option(
    "--debug/--no-debug", default=None, help="Show safe diagnostics on stderr."
)
@click.option("--search", default="", help="Text to find; omit to browse.")
@click.option("--state", default=None, help="Two-letter state code.")
@click.pass_context
def recreation_areas_cmd(
    ctx: click.Context,
    provider: str | None,
    debug: bool | None,
    search: str,
    state: str | None,
) -> None:
    """Discover recreation areas directly from the booking provider."""
    name, provider_class = _selected_provider(ctx, provider)
    query = _query(search, state)
    _diagnostic(f"Discovering recreation areas on {name}.", _debug(ctx, debug))

    async def discover() -> None:
        instance = provider_class()
        try:
            results = await instance.search(
                query.query,
                state=query.state,
                entity_type=SearchEntityType.RECREATION_AREA,
                limit=_RESULT_PROBE,
            )
            _render_discovery(
                results,
                empty="No recreation areas found. This provider may not have a recreation-area catalog.",
            )
        finally:
            await instance.async_client.aclose()

    _run(discover)


@click.command(name="campgrounds")
@click.option(
    "--provider", default=None, help="Camping provider; overrides the root selection."
)
@click.option(
    "--debug/--no-debug", default=None, help="Show safe diagnostics on stderr."
)
@click.option("--search", default="", help="Text to find; omit to browse.")
@click.option("--state", default=None, help="Two-letter state code.")
@click.option(
    "--rec-area",
    multiple=True,
    help="Exact recreation-area ID; repeat to combine areas.",
)
@click.option(
    "--campground",
    multiple=True,
    help="Exact campground ID; overrides recreation areas.",
)
@click.pass_context
def campgrounds_cmd(
    ctx: click.Context,
    provider: str | None,
    debug: bool | None,
    search: str,
    state: str | None,
    rec_area: tuple[str, ...],
    campground: tuple[str, ...],
) -> None:
    """Find campgrounds, or resolve exact campground and recreation-area IDs."""
    name, provider_class = _selected_provider(ctx, provider)
    query = _query(search, state)
    areas, campgrounds = _ids(rec_area, "--rec-area"), _ids(campground, "--campground")
    if areas and campgrounds:
        click.echo(
            "Ignoring --rec-area because explicit --campground IDs take precedence.",
            err=True,
        )
    _diagnostic(f"Discovering campgrounds on {name}.", _debug(ctx, debug))

    async def discover() -> None:
        instance = provider_class()
        try:
            results: list[ProviderSearchResult]
            if areas or campgrounds:
                candidates = await _targets(instance, areas, campgrounds)
                results = list(
                    await instance.filter_campgrounds(
                        candidates, query=query.query, state=query.state
                    )
                )
            else:
                results = await instance.search(
                    query.query,
                    state=query.state,
                    entity_type=SearchEntityType.CAMPGROUND,
                    limit=_RESULT_PROBE,
                )
            _render_discovery(
                results,
                empty="No eligible campgrounds found for these selectors and filters.",
            )
        finally:
            await instance.async_client.aclose()

    _run(discover)


def _render_stays(stays: list["AvailabilityStay"]) -> None:
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


@click.command(name="campsites")
@click.option(
    "--provider", default=None, help="Camping provider; overrides the root selection."
)
@click.option(
    "--debug/--no-debug", default=None, help="Show safe diagnostics on stderr."
)
@click.option(
    "--rec-area",
    multiple=True,
    help="Exact recreation-area ID; repeat to combine areas.",
)
@click.option(
    "--campground",
    multiple=True,
    help="Exact campground ID; overrides recreation areas.",
)
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

    name, provider_class = _selected_provider(ctx, provider)
    areas, campgrounds = _ids(rec_area, "--rec-area"), _ids(campground, "--campground")
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
    _diagnostic(
        f"Watching campground availability on {name}; cancel with Ctrl-C.",
        _debug(ctx, debug),
    )

    async def watch() -> None:
        instance = provider_class()
        try:
            targets = await _targets(instance, areas, campgrounds)
            if not targets:
                click.echo(
                    "No eligible campgrounds found in the selected recreation areas."
                )
                return
            await monitor(instance, targets, request, _render_stays)
        finally:
            await instance.async_client.aclose()

    _run(watch)


COMMANDS = {
    "providers": providers_cmd,
    "recreation-areas": recreation_areas_cmd,
    "campgrounds": campgrounds_cmd,
    "campsites": campsites_cmd,
}
