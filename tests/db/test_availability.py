"""Verify consecutive stays and saved preferences independently of providers."""

import datetime

import pytest

from camply.db.availability import (
    matches_scan_filters,
    matching_available_dates,
    matching_scan_results,
)
from camply.db.models import ScanResult, UniqueTarget, UserScan


@pytest.mark.parametrize(
    ("dates", "minimum", "expected"),
    [
        ([], 1, []),
        (["2027-07-01"], 1, ["2027-07-01"]),
        (["2027-07-01", "2027-07-03"], 2, []),
        (
            ["2027-07-02", "2027-07-01", "2027-07-01", "2027-07-05"],
            2,
            ["2027-07-01", "2027-07-02"],
        ),
        (["2027-12-31", "2028-01-01"], 2, ["2027-12-31", "2028-01-01"]),
        (
            ["2028-02-28", "2028-02-29", "2028-03-01"],
            3,
            ["2028-02-28", "2028-02-29", "2028-03-01"],
        ),
    ],
)
def test_matching_stays(dates: list[str], minimum: int, expected: list[str]) -> None:
    """Deduplicate nights, respect gaps, and support month/year boundaries."""
    assert matching_available_dates(dates, min_stay_length=minimum) == expected


def test_unknown_attributes_require_a_refresh_for_restrictive_filters() -> None:
    """Legacy snapshots remain usable without falsely satisfying site preferences."""
    scan = UserScan(min_stay_length=1, require_electric=False)
    assert matches_scan_filters(
        ["2027-07-01"], campsite_type=None, is_electric=None, scan=scan
    )
    scan.require_electric = True
    assert not matches_scan_filters(
        ["2027-07-01"], campsite_type=None, is_electric=None, scan=scan
    )
    scan.require_electric = False
    scan.preferred_types = ["TENT"]
    assert not matches_scan_filters(
        ["2027-07-01"], campsite_type=None, is_electric=None, scan=scan
    )


def test_expire_nights_before_applying_minimum_stay() -> None:
    """Paused snapshots cannot use past or out-of-range nights to qualify stays."""
    today = datetime.datetime.now(tz=datetime.timezone.utc).date()
    yesterday = today - datetime.timedelta(days=1)
    tomorrow = today + datetime.timedelta(days=1)
    checkout = today + datetime.timedelta(days=2)
    target = UniqueTarget(start_date=yesterday, end_date=checkout)
    target.scan_results = [
        ScanResult(campsite_id="expired", available_dates=[yesterday.isoformat()]),
        ScanResult(
            campsite_id="too-short",
            available_dates=[yesterday.isoformat(), today.isoformat()],
        ),
        ScanResult(
            campsite_id="remaining",
            available_dates=[
                yesterday.isoformat(),
                today.isoformat(),
                tomorrow.isoformat(),
                checkout.isoformat(),
            ],
        ),
        ScanResult(
            campsite_id="outside-range",
            available_dates=[
                checkout.isoformat(),
                (checkout + datetime.timedelta(days=1)).isoformat(),
            ],
        ),
    ]
    scan = UserScan(target=target, is_active=False, min_stay_length=2)
    results = matching_scan_results(scan)
    assert [(site.campsite_id, dates) for site, dates in results] == [
        ("remaining", [today.isoformat(), tomorrow.isoformat()])
    ]


def test_area_qualified_matching_and_per_campground_expiration() -> None:
    """Identical campsite IDs across area campgrounds stay separated and expire independently."""
    from camply.db.models import Campground, RecreationArea, ScanTarget

    today = datetime.datetime.now(tz=datetime.timezone.utc).date()
    yesterday = today - datetime.timedelta(days=1)
    tomorrow = today + datetime.timedelta(days=1)
    checkout = today + datetime.timedelta(days=3)

    area = RecreationArea(id="area-1", provider_id=1, name="Area 1", enabled=True)
    cg1 = Campground(
        id="cg-1",
        provider_id=1,
        recreation_area_id="area-1",
        name="Alpha",
        enabled=True,
        reservable=True,
        recreation_area=area,
    )
    cg2 = Campground(
        id="cg-2",
        provider_id=1,
        recreation_area_id="area-1",
        name="Beta",
        enabled=True,
        reservable=True,
        recreation_area=area,
    )
    t1 = UniqueTarget(
        provider_id=1,
        campground_id="cg-1",
        start_date=yesterday,
        end_date=checkout,
        campground=cg1,
    )
    t1.scan_results = [
        ScanResult(
            campsite_id="001",
            campsite_type="TENT",
            is_electric=False,
            available_dates=[yesterday.isoformat(), today.isoformat()],
        )
    ]
    t2 = UniqueTarget(
        provider_id=1,
        campground_id="cg-2",
        start_date=yesterday,
        end_date=checkout,
        campground=cg2,
    )
    t2.scan_results = [
        ScanResult(
            campsite_id="001",
            campsite_type="TENT",
            is_electric=False,
            available_dates=[today.isoformat(), tomorrow.isoformat()],
        )
    ]
    scan = UserScan(
        provider_id=1,
        destination_type="recreation_area",
        recreation_area_id="area-1",
        coverage_mode="all",
        coverage_revision=1,
        selected_campgrounds=[],
        start_date=yesterday,
        end_date=checkout,
        min_stay_length=2,
        is_active=True,
    )
    scan.coverage = [
        ScanTarget(target=t1, coverage_revision=1, outcome="succeeded"),
        ScanTarget(target=t2, coverage_revision=1, outcome="succeeded"),
    ]
    results = matching_scan_results(scan)
    assert [(site.campsite_id, dates) for site, dates in results] == [
        ("001", [today.isoformat(), tomorrow.isoformat()])
    ]
    scan.min_stay_length = 1
    single_night = matching_scan_results(scan)
    assert len(single_night) == 2


@pytest.mark.parametrize("mask", range(1, 128))
def test_every_weekday_subset_filters_booking_nights(mask: int) -> None:
    """Every nonempty day selection retains exactly the requested booking dates."""
    start = datetime.date(2027, 6, 1)
    dates = [start + datetime.timedelta(days=offset) for offset in range(21)]
    selected = [day for day in range(7) if mask & (1 << day)]
    assert matching_available_dates(
        [night.isoformat() for night in dates],
        min_stay_length=1,
        allowed_weekdays=selected,
    ) == [night.isoformat() for night in dates if night.weekday() in selected]


@pytest.mark.parametrize(
    ("dates", "selected", "minimum", "expected"),
    [
        (
            ["2027-07-01", "2027-07-02", "2027-07-03", "2027-07-04"],
            [4, 5],
            2,
            ["2027-07-02", "2027-07-03"],
        ),
        (["2027-07-02", "2027-07-03", "2027-07-04"], [4, 5], 3, []),
        (["2027-07-04", "2027-07-05"], [6, 0], 2, ["2027-07-04", "2027-07-05"]),
        (["2027-07-02", "2027-07-09"], [4], 2, []),
        (["2027-12-31", "2028-01-01"], [4, 5], 2, ["2027-12-31", "2028-01-01"]),
        (["2028-02-28", "2028-02-29", "2028-03-01"], [0, 2], 2, []),
    ],
)
def test_weekday_filter_precedes_consecutive_matching(
    dates: list[str], selected: list[int], minimum: int, expected: list[str]
) -> None:
    """Excluded nights break blocks; week and year boundaries do not."""
    assert (
        matching_available_dates(
            dates, min_stay_length=minimum, allowed_weekdays=selected
        )
        == expected
    )


def test_saved_nights_filter_returned_dates_and_subscribers() -> None:
    """Subscribers share observations without leaking excluded dates into results."""
    target = UniqueTarget(
        start_date=datetime.date(2099, 7, 1), end_date=datetime.date(2099, 7, 9)
    )
    dates = [datetime.date(2099, 7, day).isoformat() for day in range(1, 9)]
    target.scan_results = [ScanResult(campsite_id="one", available_dates=dates)]
    weekends = UserScan(target=target, min_stay_length=2, allowed_weekdays=[4, 5])
    weekdays = UserScan(target=target, min_stay_length=1, allowed_weekdays=[0, 2])
    for scan in [weekends, weekdays]:
        assert matching_scan_results(scan)[0][1] == [
            night
            for night in dates
            if datetime.date.fromisoformat(night).weekday() in scan.allowed_weekdays
        ]
    assert target.scan_results[0].available_dates == dates


@pytest.mark.parametrize(
    ("selected", "minimum", "valid"),
    [
        ([4, 5], 2, True),
        ([4, 5], 3, False),
        ([0, 2], 2, False),
        ([0, 6], 2, True),
        (None, 8, True),
        ([], 1, False),
    ],
)
def test_calendar_feasibility(
    selected: list[int] | None, minimum: int, valid: bool
) -> None:
    """Validate the calendar independently of provider availability."""
    from camply.db.availability import validate_scan_dates

    kwargs = {
        "start_date": datetime.date(2027, 7, 1),
        "end_date": datetime.date(2027, 7, 15),
        "allowed_weekdays": selected,
        "min_stay_length": minimum,
        "today": datetime.date(2027, 1, 1),
    }
    if valid:
        validate_scan_dates(**kwargs)
    else:
        with pytest.raises(ValueError, match="selected nights"):
            validate_scan_dates(**kwargs)
