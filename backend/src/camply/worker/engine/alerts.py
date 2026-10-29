"""Prepare current matching alerts consistently for both execution runtimes."""

import datetime as dt

from camply.db.availability import matches_scan_filters, matching_available_dates
from camply.db.models import UniqueTarget, UserScan
from camply.worker.notifications.base import NotificationDTO


def matching_opening(
    payload: NotificationDTO, scan: UserScan, target: UniqueTarget, today: dt.date
) -> NotificationDTO | None:
    """Retain only unexpired nights in qualifying stays under current preferences."""
    dates = sorted(
        {
            value
            for value in payload.metadata["available_dates"]
            if max(today, target.start_date)
            <= dt.date.fromisoformat(value)
            < target.end_date
        }
    )
    if not matches_scan_filters(
        dates,
        campsite_type=payload.metadata["campsite_type"],
        is_electric=payload.metadata["is_electric"],
        scan=scan,
    ):
        return None
    dates = matching_available_dates(dates, min_stay_length=scan.min_stay_length or 1)
    return payload.model_copy(
        update={
            "start_date": dt.date.fromisoformat(dates[0]),
            "end_date": dt.date.fromisoformat(dates[-1]) + dt.timedelta(days=1),
            "metadata": {**payload.metadata, "available_dates": dates},
        }
    )


def summarize_openings(
    openings: list[NotificationDTO],
    scan: UserScan,
    target: UniqueTarget,
    *,
    app_url: str,
) -> NotificationDTO:
    """Summarize a scan's new matching sites and retain snapshots for revalidation."""
    count = len(openings)
    park_name = openings[0].park_name
    return NotificationDTO(
        title=f"{count} new campsite{'s' if count != 1 else ''}: {park_name}",
        message=(
            f"{count} campsite{'s' if count != 1 else ''} with new availability "
            f"matching your scan at {park_name}.\n"
            f"{target.start_date.isoformat()} to {target.end_date.isoformat()}.\n"
            "View available stays and booking options in Camply."
        ),
        booking_url=f"{app_url.rstrip('/')}/dashboard/scans/{scan.id}#results",
        url_title="View campsites",
        park_name=park_name,
        campsite_name="",
        start_date=target.start_date,
        end_date=target.end_date,
        metadata={
            "new_campsite_count": count,
            "openings": [opening.model_dump(mode="json") for opening in openings],
        },
    )
