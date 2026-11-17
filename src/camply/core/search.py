"""Normalize local search windows and match live observations into exact stays."""

import asyncio
import inspect
from collections.abc import Awaitable, Callable, Sequence
from datetime import date, datetime, timedelta, timezone

from pydantic import BaseModel, ConfigDict, Field

from camply.db.availability import matching_available_dates
from camply.providers.base import BaseProvider
from camply.providers.dto import CampgroundSearchResult, CampsiteDTO, CampsiteType

# Default polling interval in seconds (10 minutes).
POLL_INTERVAL_SECONDS = 600.0
_MAX_RV_LENGTH_FEET = 200

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
    campsites: tuple[str, ...] = ()
    campsite_types: tuple[CampsiteType, ...] = ()
    require_electric: bool = False
    require_accessible: bool = False
    min_rv_length: int | None = Field(default=None, ge=1, le=_MAX_RV_LENGTH_FEET)
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
    campsites: Sequence[str] = (),
    campsite_types: Sequence[str] = (),
    require_electric: bool = False,
    require_accessible: bool = False,
    min_rv_length: int | None = None,
    today: date | None = None,
) -> SearchRequest:
    """Validate paired windows and union eligible nights without bridging gaps.

    Raises
    ------
    ValueError
        Date pairs, weekday names, site filters, or requested stay length cannot be satisfied.
    """
    if not start_dates or len(start_dates) != len(end_dates):
        raise ValueError(
            "Provide equal, nonzero counts of paired --start-date and --end-date values."
        )
    if isinstance(nights, bool) or not isinstance(nights, int) or nights < 1:
        raise ValueError("--nights must be a positive integer.")
    normalized_campsites = _normalized_campsites(campsites)
    normalized_types = _normalized_campsite_types(campsite_types)
    if min_rv_length is not None and (
        isinstance(min_rv_length, bool)
        or not isinstance(min_rv_length, int)
        or not (1 <= min_rv_length <= _MAX_RV_LENGTH_FEET)
    ):
        raise ValueError("--rv-length must be an integer between 1 and 200 feet.")
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
        campsites=normalized_campsites,
        campsite_types=normalized_types,
        require_electric=bool(require_electric),
        require_accessible=bool(require_accessible),
        min_rv_length=min_rv_length,
        warnings=tuple(warnings),
    )


def _normalized_campsites(campsites: Sequence[str]) -> tuple[str, ...]:
    """Trim and deduplicate campsite selectors, rejecting blank strings."""
    cleaned = tuple(dict.fromkeys(value.strip() for value in campsites))
    if any(not value for value in cleaned):
        raise ValueError("--campsite values must not be blank.")
    return cleaned


def _normalized_campsite_types(
    campsite_types: Sequence[str],
) -> tuple[CampsiteType, ...]:
    """Normalize and deduplicate standardized campsite types."""
    normalized: list[CampsiteType] = []
    for raw in campsite_types:
        try:
            ctype = CampsiteType(raw.strip().upper())
        except ValueError as exc:
            raise ValueError(
                f"Unknown --campsite-type {raw!r}; choose from TENT, RV, CABIN, OTHER."
            ) from exc
        if ctype not in normalized:
            normalized.append(ctype)
    return tuple(normalized)


def site_matches_request(site: CampsiteDTO, request: SearchRequest) -> bool:
    """Evaluate site-attribute and campsite-ID/name filters with fail-closed semantics."""
    if request.campsites:
        site_id = site.campsite_id.strip()
        site_name = site.campsite_name.strip().casefold()
        lowered = {value.casefold() for value in request.campsites}
        if site_id not in request.campsites and site_name not in lowered:
            return False
    return (
        (not request.campsite_types or site.campsite_type in request.campsite_types)
        and (not request.require_electric or site.is_electric is True)
        and (not request.require_accessible or site.is_accessible is True)
        and (
            request.min_rv_length is None
            or (
                site.max_vehicle_length is not None
                and site.max_vehicle_length >= request.min_rv_length
            )
        )
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
        if not site_matches_request(site, request):
            continue
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
    on_results: Callable[[list[AvailabilityStay]], Awaitable[None] | None],
    *,
    wait: Callable[[float], Awaitable[None]] = asyncio.sleep,
    interval: float | None = None,
    once: bool = False,
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
        callback_result = on_results(
            await check_availability(provider, targets, request)
        )
        if inspect.isawaitable(callback_result):
            await callback_result
        if once:
            return
        await wait(delay)
