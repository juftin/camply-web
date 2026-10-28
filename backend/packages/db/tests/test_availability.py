"""Verify consecutive stays and saved preferences independently of providers."""

import datetime

import pytest

from db.availability import (
    matches_scan_filters,
    matching_available_dates,
    matching_scan_results,
)
from db.models import ScanResult, UniqueTarget, UserScan


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
