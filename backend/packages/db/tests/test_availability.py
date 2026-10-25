"""Verify consecutive stays and saved preferences independently of providers."""

import pytest

from db.availability import matches_scan_filters, matching_available_dates
from db.models import UserScan


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
