"""Normalize local search windows and match live observations into exact stays."""

import asyncio
from collections.abc import Awaitable, Callable, Sequence
from datetime import date, datetime, timedelta, timezone

from pydantic import BaseModel, ConfigDict, Field

from camply.db.availability import matching_available_dates
from camply.providers.base import BaseProvider
from camply.providers.dto import CampgroundSearchResult, CampsiteDTO

# Conservative internal wait, deliberately not a public scheduling policy/option.
# The detailed CLI scheduling contract remains deferred under specification D11.
POLL_INTERVAL_SECONDS = 60.0

_DAY_NAMES = (
    ("monday", "mon"),
    ("tuesday", "tue", "tues"),
    ("wednesday", "wed"),
    ("thursday", "thu", "thur", "thurs"),
    ("friday", "fri"),
    ("saturday", "sat"),
    ("sunday", "sun"),
)
_WEEKDAYS = {
    name: weekday for weekday, names in enumerate(_DAY_NAMES) for name in names
}


class DateWindow(BaseModel):
    """An inclusive arrival and exclusive checkout interval."""

    model_config = ConfigDict(frozen=True)
    start_date: date
    end_date: date


class SearchRequest(BaseModel):
    """Validated local windows and eligible nights without account state."""

    model_config = ConfigDict(frozen=True)
    windows: tuple[DateWindow, ...]
    eligible_dates: frozenset[date]
    nights: int = Field(ge=1)
    warnings: tuple[str, ...] = ()


class AvailabilityStay(BaseModel):
    """One exact-length bookable stay derived from a successful observation."""

    campground: CampgroundSearchResult
    campsite_id: str
    campsite_name: str
    arrival: date
    checkout: date
    booking_url: str


def utc_today() -> date:
    """Return the current UTC calendar day used by web and local matching."""
    return datetime.now(tz=timezone.utc).date()


def normalize_request(
    *,
    start_dates: Sequence[date],
    end_dates: Sequence[date],
    days: Sequence[str] = (),
    weekends: bool = False,
    nights: int = 1,
    today: date | None = None,
) -> SearchRequest:
    """Validate paired windows and union eligible nights without bridging gaps.

    Raises
    ------
    ValueError
        Date pairs, weekday names, or requested stay length cannot be satisfied.
    """
    if not start_dates or len(start_dates) != len(end_dates):
        raise ValueError(
            "Provide equal, nonzero counts of paired --start-date and --end-date values."
        )
    if isinstance(nights, bool) or not isinstance(nights, int) or nights < 1:
        raise ValueError("--nights must be a positive integer.")
    allowed_days = _allowed_weekdays(days, weekends=weekends)
    current_day = today if today is not None else utc_today()
    requested_dates, warnings = _requested_dates(start_dates, end_dates, current_day)
    eligible = frozenset(
        night
        for night in requested_dates
        if not allowed_days or night.weekday() in allowed_days
    )
    if not matching_available_dates(
        [night.isoformat() for night in eligible], min_stay_length=nights
    ):
        raise ValueError(
            "The selected windows/weekdays cannot contain the requested --nights consecutive nights."
        )
    return SearchRequest(
        windows=_merged_windows(requested_dates),
        eligible_dates=eligible,
        nights=nights,
        warnings=tuple(warnings),
    )


def _allowed_weekdays(days: Sequence[str], *, weekends: bool) -> set[int]:
    """Resolve the weekday union; an empty set means unrestricted nights."""
    allowed_days: set[int] = set()
    for name in days:
        key = name.strip().casefold()
        if key not in _WEEKDAYS:
            raise ValueError(
                f"Unknown --day {name!r}; use an English weekday name or abbreviation."
            )
        allowed_days.add(_WEEKDAYS[key])
    if weekends:
        allowed_days.update((4, 5))
    return allowed_days


def _requested_dates(
    start_dates: Sequence[date], end_dates: Sequence[date], current_day: date
) -> tuple[set[date], list[str]]:
    """Validate original windows, clamp starts and preserve every covered night."""
    requested_dates: set[date] = set()
    warnings: list[str] = []
    for start, end in zip(start_dates, end_dates, strict=True):
        if end <= start:
            raise ValueError(
                "Each --end-date must be after its paired --start-date (checkout is exclusive)."
            )
        if end <= current_day:
            raise ValueError(
                "A selected date window has no remaining current or future booking nights."
            )
        if start < current_day:
            warning = f"Clamped past start date {start.isoformat()} to UTC today {current_day.isoformat()}."
            if warning not in warnings:
                warnings.append(warning)
            start = current_day
        requested_dates.update(
            start + timedelta(days=offset) for offset in range((end - start).days)
        )
    return requested_dates, warnings


def _merged_windows(requested_dates: set[date]) -> tuple[DateWindow, ...]:
    """Merge contiguous covered nights without requesting any gaps."""
    windows: list[DateWindow] = []
    for night in sorted(requested_dates):
        if windows and windows[-1].end_date == night:
            windows[-1] = DateWindow(
                start_date=windows[-1].start_date, end_date=night + timedelta(days=1)
            )
        else:
            windows.append(
                DateWindow(start_date=night, end_date=night + timedelta(days=1))
            )
    return tuple(windows)


def _stays(
    campground: CampgroundSearchResult,
    observations: list[CampsiteDTO],
    request: SearchRequest,
    *,
    today: date,
) -> list[AvailabilityStay]:
    """Group by observed site identity and construct exact sliding stays."""
    grouped: dict[str, tuple[CampsiteDTO, set[date]]] = {}
    for site in observations:
        _, nights = grouped.setdefault(site.campsite_id, (site, set()))
        nights.update(
            night
            for night in site.available_dates
            if night >= today and night in request.eligible_dates
        )
    stays: list[AvailabilityStay] = []
    for site, nights in grouped.values():
        matching = {
            date.fromisoformat(value)
            for value in matching_available_dates(
                [night.isoformat() for night in nights], min_stay_length=request.nights
            )
        }
        candidate_url = site.metadata.get("booking_url")
        booking_url = (
            candidate_url
            if isinstance(candidate_url, str) and candidate_url
            else campground.booking_url
        )
        for arrival in sorted(matching):
            if all(
                arrival + timedelta(days=offset) in matching
                for offset in range(request.nights)
            ):
                stays.append(
                    AvailabilityStay(
                        campground=campground,
                        campsite_id=site.campsite_id,
                        campsite_name=site.campsite_name,
                        arrival=arrival,
                        checkout=arrival + timedelta(days=request.nights),
                        booking_url=booking_url,
                    )
                )
    return stays


async def check_availability(
    provider: BaseProvider,
    targets: Sequence[CampgroundSearchResult],
    request: SearchRequest,
    *,
    today: date | None = None,
) -> list[AvailabilityStay]:
    """Check unique targets sequentially using provider-owned pacing and retries.

    No child tasks are scheduled. Failed provider requests propagate instead of
    producing false empty results; the caller owns and closes the provider.
    """
    unique = {(target.provider_id, target.campground_id): target for target in targets}
    stays: list[AvailabilityStay] = []
    for key in sorted(unique):
        target = unique[key]
        observations: list[CampsiteDTO] = []
        for window in request.windows:
            current_day = today if today is not None else utc_today()
            start = max(window.start_date, current_day)
            if start < window.end_date:
                observations.extend(
                    await provider.find_availabilities(
                        target.campground_id, start, window.end_date
                    )
                )
        current_day = today if today is not None else utc_today()
        stays.extend(_stays(target, observations, request, today=current_day))
    # An area cycle can span midnight while other targets are still being
    # checked. Expire earlier targets again at delivery without inventing a stay.
    delivery_day = today if today is not None else utc_today()
    return sorted(
        (stay for stay in stays if stay.arrival >= delivery_day),
        key=lambda stay: (
            stay.campground.provider_id,
            stay.campground.campground_id,
            stay.campsite_id,
            stay.arrival,
            stay.checkout,
        ),
    )


async def monitor(
    provider: BaseProvider,
    targets: Sequence[CampgroundSearchResult],
    request: SearchRequest,
    on_results: Callable[[list[AvailabilityStay]], None],
    *,
    wait: Callable[[float], Awaitable[None]] = asyncio.sleep,
    interval: float | None = None,
) -> None:
    """Check immediately and continue after every success until cancellation.

    The caller owns provider closure around resolution and monitoring. Every
    request and wait is awaited directly, so cancelling this coroutine stops
    scheduling work and propagates cancellation to its active request/wait.
    """
    if not targets:
        return
    delay = POLL_INTERVAL_SECONDS if interval is None else interval
    if delay <= 0:
        raise ValueError("Internal polling interval must be positive.")
    while True:
        on_results(await check_availability(provider, targets, request))
        await wait(delay)
