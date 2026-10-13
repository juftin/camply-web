"""
Availability snapshot tracking and opening detection.
"""

from dataclasses import dataclass, field
from datetime import date

from camply_core.models import CampsiteDTO


@dataclass
class AvailabilitySnapshot:
    """
    In-memory snapshot of campsite availability at a point in time.
    """

    site_dates: dict[str, set[date]] = field(default_factory=dict)

    @classmethod
    def from_campsites(cls, campsites: list[CampsiteDTO]) -> "AvailabilitySnapshot":
        """
        Create a snapshot from a list of CampsiteDTO objects.
        """
        site_dates: dict[str, set[date]] = {}
        for site in campsites:
            site_dates[site.campsite_id] = set(site.available_dates)
        return cls(site_dates=site_dates)

    def is_empty(self) -> bool:
        """Return True if no sites have available dates."""
        return not any(dates for dates in self.site_dates.values())


def diff_new_openings(
    previous: AvailabilitySnapshot | None,
    current: AvailabilitySnapshot,
) -> dict[str, set[date]]:
    """
    Compare previous and current snapshots to find newly opened dates.

    Returns a dict mapping campsite_id to the set of dates that are
    newly available in current compared to previous.
    If previous is None, all dates in current are considered new.
    """
    new_openings: dict[str, set[date]] = {}
    if previous is None:
        for site_id, dates in current.site_dates.items():
            if dates:
                new_openings[site_id] = set(dates)
        return new_openings

    for site_id, curr_dates in current.site_dates.items():
        prev_dates = previous.site_dates.get(site_id, set())
        opened = curr_dates - prev_dates
        if opened:
            new_openings[site_id] = opened

    return new_openings


def identify_new_campsites(
    previous: AvailabilitySnapshot | None,
    current_campsites: list[CampsiteDTO],
) -> list[CampsiteDTO]:
    """
    Filter current campsites down to those with newly available dates.
    """
    if previous is None:
        return [c for c in current_campsites if c.available_dates]

    newly_opened = diff_new_openings(
        previous=previous,
        current=AvailabilitySnapshot.from_campsites(current_campsites),
    )
    return [c for c in current_campsites if c.campsite_id in newly_opened]
