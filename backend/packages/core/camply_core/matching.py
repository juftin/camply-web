"""
Criteria matching and consecutive stay calculations.
"""

from datetime import date, timedelta

from camply_core.models import CampsiteDTO, SearchFilters, SearchWindow, StayWindow


def longest_consecutive_nights(dates: list[date]) -> int:
    """
    Calculate the length of the longest consecutive run of nights.
    """
    if not dates:
        return 0
    unique_sorted = sorted(set(dates))
    longest = 1
    current = 1
    for i in range(1, len(unique_sorted)):
        if (unique_sorted[i] - unique_sorted[i - 1]).days == 1:
            current += 1
            longest = max(longest, current)
        else:
            current = 1
    return longest


def calculate_consecutive_runs(
    dates: list[date],
    min_nights: int = 1,
) -> list[StayWindow]:
    """
    Find all maximal consecutive runs of nights that satisfy min_nights.

    For a sequence of nights [d_1, ..., d_k], the stay window has:
    arrival = d_1
    departure = d_k + 1 day
    nights = k
    """
    if not dates or min_nights < 1:
        return []

    unique_sorted = sorted(set(dates))
    runs: list[list[date]] = []
    current_run = [unique_sorted[0]]

    for i in range(1, len(unique_sorted)):
        if (unique_sorted[i] - unique_sorted[i - 1]).days == 1:
            current_run.append(unique_sorted[i])
        else:
            runs.append(current_run)
            current_run = [unique_sorted[i]]
    runs.append(current_run)

    stay_windows: list[StayWindow] = []
    for run in runs:
        if len(run) >= min_nights:
            stay_windows.append(
                StayWindow(
                    arrival=run[0],
                    departure=run[-1] + timedelta(days=1),
                    nights=len(run),
                )
            )
    return stay_windows


def matches_filters(campsite: CampsiteDTO, filters: SearchFilters) -> bool:
    """
    Check whether a campsite matches search criteria.

    Filters applied:
      - min_consecutive_nights: consecutive nights available >= min_consecutive_nights
      - campsite_types: if set, campsite.campsite_type must be included
      - electric_requirement: if True, campsite.is_electric must be True
    """
    if filters.min_consecutive_nights > 1:
        consec = longest_consecutive_nights(campsite.available_dates)
        if consec < filters.min_consecutive_nights:
            return False

    if filters.campsite_types:
        if campsite.campsite_type not in filters.campsite_types:
            return False

    if filters.electric_requirement and not campsite.is_electric:
        return False

    return True


def find_qualifying_stays(
    campsite: CampsiteDTO,
    window: SearchWindow,
    filters: SearchFilters,
) -> list[StayWindow]:
    """
    Find qualifying stay windows for a campsite within the requested search window.
    """
    if not matches_filters(campsite, filters):
        return []

    valid_nights = [
        d for d in campsite.available_dates if window.arrival <= d < window.departure
    ]
    return calculate_consecutive_runs(
        valid_nights, min_nights=filters.min_consecutive_nights
    )
