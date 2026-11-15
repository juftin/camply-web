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
