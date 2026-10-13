"""
Tests for criteria matching and stay calculation in camply_core.
"""

from datetime import date

from camply_core.matching import (
    calculate_consecutive_runs,
    find_qualifying_stays,
    longest_consecutive_nights,
    matches_filters,
)
from camply_core.models import CampsiteDTO, CampsiteType, SearchFilters, SearchWindow


def test_longest_consecutive_nights() -> None:
    """Test streak calculations including edge cases."""
    assert longest_consecutive_nights([]) == 0

    single = [date(2026, 9, 1)]
    assert longest_consecutive_nights(single) == 1

    consecutive = [date(2026, 9, 1), date(2026, 9, 2), date(2026, 9, 3)]
    assert longest_consecutive_nights(consecutive) == 3

    non_consecutive = [date(2026, 9, 1), date(2026, 9, 3), date(2026, 9, 5)]
    assert longest_consecutive_nights(non_consecutive) == 1

    mixed = [
        date(2026, 9, 1),
        date(2026, 9, 2),
        date(2026, 9, 5),
        date(2026, 9, 6),
        date(2026, 9, 7),
    ]
    assert longest_consecutive_nights(mixed) == 3

    # Duplicate dates must not break streak counting
    with_duplicates = [
        date(2026, 9, 1),
        date(2026, 9, 1),
        date(2026, 9, 2),
        date(2026, 9, 3),
    ]
    assert longest_consecutive_nights(with_duplicates) == 3

    unsorted = [date(2026, 9, 3), date(2026, 9, 1), date(2026, 9, 2)]
    assert longest_consecutive_nights(unsorted) == 3


def test_calculate_consecutive_runs() -> None:
    """Test generating StayWindow objects from available dates."""
    dates = [
        date(2026, 9, 1),
        date(2026, 9, 2),
        date(2026, 9, 5),
        date(2026, 9, 6),
        date(2026, 9, 7),
    ]
    # min_nights = 2: should produce [Sept 1-3 (2 nights)] and [Sept 5-8 (3 nights)]
    runs = calculate_consecutive_runs(dates, min_nights=2)
    assert len(runs) == 2
    assert runs[0].arrival == date(2026, 9, 1)
    assert runs[0].departure == date(2026, 9, 3)
    assert runs[0].nights == 2

    assert runs[1].arrival == date(2026, 9, 5)
    assert runs[1].departure == date(2026, 9, 8)
    assert runs[1].nights == 3

    # min_nights = 3: should only produce the second run
    runs_3 = calculate_consecutive_runs(dates, min_nights=3)
    assert len(runs_3) == 1
    assert runs_3[0].nights == 3


def test_matches_filters() -> None:
    """Test campsite filtering against SearchFilters."""
    site = CampsiteDTO(
        campsite_id="1",
        campsite_name="Site 1",
        campsite_type=CampsiteType.TENT,
        available_dates=[date(2026, 9, 1), date(2026, 9, 2)],
        is_electric=True,
    )

    # Base match
    assert matches_filters(site, SearchFilters()) is True

    # Electric requirement
    assert matches_filters(site, SearchFilters(electric_requirement=True)) is True
    site_no_electric = CampsiteDTO(
        campsite_id="2",
        campsite_name="Site 2",
        campsite_type=CampsiteType.TENT,
        available_dates=[date(2026, 9, 1)],
        is_electric=False,
    )
    assert (
        matches_filters(site_no_electric, SearchFilters(electric_requirement=True))
        is False
    )

    # Preferred types
    assert (
        matches_filters(site, SearchFilters(campsite_types=[CampsiteType.TENT])) is True
    )
    assert (
        matches_filters(site, SearchFilters(campsite_types=[CampsiteType.RV])) is False
    )

    # Min stay length
    assert matches_filters(site, SearchFilters(min_consecutive_nights=2)) is True
    assert matches_filters(site, SearchFilters(min_consecutive_nights=3)) is False


def test_find_qualifying_stays() -> None:
    """Test finding stays bounded strictly to the search window."""
    site = CampsiteDTO(
        campsite_id="1",
        campsite_name="Site 1",
        campsite_type=CampsiteType.TENT,
        available_dates=[
            date(2026, 8, 31),  # outside window
            date(2026, 9, 1),
            date(2026, 9, 2),
            date(
                2026, 9, 3
            ),  # checkout day morning: if window departure is Sept 3, this is excluded
        ],
    )
    window = SearchWindow(
        arrival=date(2026, 9, 1),
        departure=date(2026, 9, 3),  # 2 nights: Sept 1, Sept 2
    )
    stays = find_qualifying_stays(
        campsite=site,
        window=window,
        filters=SearchFilters(min_consecutive_nights=2),
    )
    assert len(stays) == 1
    assert stays[0].arrival == date(2026, 9, 1)
    assert stays[0].departure == date(2026, 9, 3)
    assert stays[0].nights == 2
