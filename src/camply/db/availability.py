"""Apply saved scan preferences consistently to availability snapshots and alerts."""

import datetime
from collections.abc import Sequence

from camply.db.models import ScanResult, UserScan


def matching_available_dates(
    dates: list[str],
    *,
    min_stay_length: int,
    allowed_weekdays: Sequence[int] | None = None,
) -> list[str]:
    """Filter booking weekdays before finding consecutive qualifying nights."""
    ordered = sorted(
        night
        for night in {datetime.date.fromisoformat(value) for value in dates}
        if allowed_weekdays is None or night.weekday() in allowed_weekdays
    )
    blocks: list[list[datetime.date]] = []
    for night in ordered:
        if not blocks or night != blocks[-1][-1] + datetime.timedelta(days=1):
            blocks.append([])
        blocks[-1].append(night)
    return [
        night.isoformat()
        for block in blocks
        if len(block) >= min_stay_length
        for night in block
    ]


def validate_scan_dates(
    *,
    start_date: datetime.date,
    end_date: datetime.date,
    min_stay_length: int,
    allowed_weekdays: Sequence[int] | None,
    today: datetime.date | None = None,
) -> None:
    """Reject date/day/stay combinations that cannot contain a future stay.

    This validates calendar feasibility, independently of provider availability.
    Call before creating or changing criteria, not for reads or status changes.
    """
    if end_date <= start_date:
        raise ValueError("Check-out must be after check-in")
    first = max(
        start_date,
        today or datetime.datetime.now(tz=datetime.timezone.utc).date(),
    )
    consecutive = 0
    night = first
    while night < end_date:
        consecutive = (
            consecutive + 1
            if allowed_weekdays is None or night.weekday() in allowed_weekdays
            else 0
        )
        if consecutive >= min_stay_length:
            return
        night += datetime.timedelta(days=1)
    raise ValueError(
        "The remaining dates and selected nights cannot contain the requested "
        "consecutive stay. Extend the dates, select more nights, or reduce the stay length."
    )


def matches_scan_filters(
    available_dates: list[str],
    *,
    campsite_type: str | None,
    is_electric: bool | None,
    scan: UserScan,
) -> bool:
    """Check site preferences; unknown legacy attributes cannot prove a match."""
    return (
        (not scan.preferred_types or campsite_type in scan.preferred_types)
        and (not scan.require_electric or is_electric is True)
        and bool(
            matching_available_dates(
                available_dates,
                min_stay_length=scan.min_stay_length or 1,
                allowed_weekdays=scan.allowed_weekdays,
            )
        )
    )


def matching_scan_results(scan: UserScan) -> list[tuple[ScanResult, list[str]]]:
    """Return matching sites after expiring past nights and applying target dates."""
    first_night = max(
        scan.target.start_date,
        datetime.datetime.now(tz=datetime.timezone.utc).date(),
    ).isoformat()
    checkout = scan.target.end_date.isoformat()
    grouped: dict[str, tuple[ScanResult, list[str]]] = {}
    for result in scan.target.scan_results:
        _, nights = grouped.setdefault(result.campsite_id, (result, []))
        nights.extend(
            night for night in result.available_dates if first_night <= night < checkout
        )
    return [
        (
            result,
            matching_available_dates(
                nights,
                min_stay_length=scan.min_stay_length or 1,
                allowed_weekdays=scan.allowed_weekdays,
            ),
        )
        for result, nights in grouped.values()
        if matches_scan_filters(
            nights,
            campsite_type=result.campsite_type,
            is_electric=result.is_electric,
            scan=scan,
        )
    ]
