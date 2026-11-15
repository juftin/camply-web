"""Apply saved scan preferences consistently to availability snapshots and alerts."""

import datetime

from camply.db.coverage import live_targets
from camply.db.models import ScanResult, UserScan


def matching_available_dates(dates: list[str], *, min_stay_length: int) -> list[str]:
    """Return nights in consecutive blocks that meet the minimum stay."""
    ordered = sorted({datetime.date.fromisoformat(value) for value in dates})
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
                available_dates, min_stay_length=scan.min_stay_length or 1
            )
        )
    )


def matching_scan_results(scan: UserScan) -> list[tuple[ScanResult, list[str]]]:
    """Return matching sites after expiring past nights and applying target dates."""
    targets = live_targets(scan)
    if not targets:
        return []
    first_night = max(
        scan.start_date or targets[0].start_date,
        datetime.datetime.now(tz=datetime.timezone.utc).date(),
    ).isoformat()
    checkout = (scan.end_date or targets[0].end_date).isoformat()
    grouped: dict[tuple[int, str, str], tuple[ScanResult, list[str]]] = {}
    for target in targets:
        for result in target.scan_results:
            _, nights = grouped.setdefault(
                (target.provider_id, target.campground_id, result.campsite_id),
                (result, []),
            )
            nights.extend(
                night
                for night in result.available_dates
                if first_night <= night < checkout
            )
    return [
        (
            result,
            matching_available_dates(nights, min_stay_length=scan.min_stay_length or 1),
        )
        for result, nights in grouped.values()
        if matches_scan_filters(
            nights,
            campsite_type=result.campsite_type,
            is_electric=result.is_electric,
            scan=scan,
        )
    ]
