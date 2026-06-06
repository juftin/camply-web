"""
Tests for the check_target_availability scanner task.
"""

import datetime
import uuid as uuid_mod

from db.models import UserScan
from providers.dto import CampsiteDTO, CampsiteType
from worker.tasks.scanner import (
    _longest_consecutive,
    _matches_scan_filters,
)


class TestLongestConsecutive:
    """Tests for the _longest_consecutive helper."""

    def test_empty_dates(self) -> None:
        assert _longest_consecutive([]) == 0

    def test_single_date(self) -> None:
        dates = [datetime.date(2026, 9, 1)]
        assert _longest_consecutive(dates) == 1

    def test_consecutive_dates(self) -> None:
        dates = [
            datetime.date(2026, 9, 1),
            datetime.date(2026, 9, 2),
            datetime.date(2026, 9, 3),
        ]
        assert _longest_consecutive(dates) == 3

    def test_non_consecutive_dates(self) -> None:
        dates = [
            datetime.date(2026, 9, 1),
            datetime.date(2026, 9, 3),
            datetime.date(2026, 9, 5),
        ]
        assert _longest_consecutive(dates) == 1

    def test_mixed_consecutive(self) -> None:
        dates = [
            datetime.date(2026, 9, 1),
            datetime.date(2026, 9, 2),
            datetime.date(2026, 9, 5),
            datetime.date(2026, 9, 6),
            datetime.date(2026, 9, 7),
        ]
        assert _longest_consecutive(dates) == 3


class TestMatchesScanFilters:
    """Tests for the _matches_scan_filters function."""

    def _make_campsite(
        self,
        campsite_type: CampsiteType = CampsiteType.TENT,
        available_dates: list | None = None,
        is_electric: bool = False,
    ) -> CampsiteDTO:
        return CampsiteDTO(
            campsite_id="site_1",
            campsite_name="Test Site",
            campsite_type=campsite_type,
            capacity=6,
            available_dates=available_dates or [datetime.date(2026, 9, 1)],
            is_electric=is_electric,
            is_accessible=False,
        )

    def _make_scan(
        self,
        min_stay_length: int = 1,
        preferred_types: list | None = None,
        require_electric: bool = False,
    ) -> UserScan:
        return UserScan(
            id=uuid_mod.uuid4(),
            user_id=uuid_mod.uuid4(),
            target_id=uuid_mod.uuid4(),
            is_active=True,
            min_stay_length=min_stay_length,
            preferred_types=preferred_types,
            require_electric=require_electric,
        )

    def test_no_filters_matches(self) -> None:
        """A campsite with no restrictive filters should match."""
        campsite = self._make_campsite()
        scan = self._make_scan()
        assert _matches_scan_filters(campsite, scan) is True

    def test_electric_filter_matches(self) -> None:
        """require_electric=True should only match electric campsites."""
        electric_campsite = self._make_campsite(is_electric=True)
        non_electric_campsite = self._make_campsite(is_electric=False)
        scan = self._make_scan(require_electric=True)

        assert _matches_scan_filters(electric_campsite, scan) is True
        assert _matches_scan_filters(non_electric_campsite, scan) is False

    def test_preferred_types_filter(self) -> None:
        """preferred_types should filter by campsite type."""
        tent_campsite = self._make_campsite(CampsiteType.TENT)
        rv_campsite = self._make_campsite(CampsiteType.RV)
        scan = self._make_scan(preferred_types=["TENT"])

        assert _matches_scan_filters(tent_campsite, scan) is True
        assert _matches_scan_filters(rv_campsite, scan) is False

    def test_min_stay_length_filter(self) -> None:
        """min_stay_length should require consecutive nights."""
        campsite_1night = self._make_campsite(
            available_dates=[datetime.date(2026, 9, 1)]
        )
        campsite_3nights = self._make_campsite(
            available_dates=[
                datetime.date(2026, 9, 1),
                datetime.date(2026, 9, 2),
                datetime.date(2026, 9, 3),
            ]
        )
        scan = self._make_scan(min_stay_length=3)

        assert _matches_scan_filters(campsite_1night, scan) is False
        assert _matches_scan_filters(campsite_3nights, scan) is True

    def test_combined_filters(self) -> None:
        """Multiple filters should all apply."""
        campsite = self._make_campsite(
            campsite_type=CampsiteType.RV,
            available_dates=[
                datetime.date(2026, 9, 1),
                datetime.date(2026, 9, 2),
            ],
            is_electric=True,
        )
        scan = self._make_scan(
            min_stay_length=2, preferred_types=["RV"], require_electric=True
        )
        assert _matches_scan_filters(campsite, scan) is True


class TestScannerTask:
    """Tests for the check_target_availability task."""

    def test_task_returns_error_for_unknown_target(self) -> None:
        """Task should return error for non-existent target_id."""
        from worker.tasks.scanner import check_target_availability

        fake_id = str(uuid_mod.uuid4())
        result = check_target_availability(fake_id)
        # With no Valkey available, should return skipped or error
        assert result is not None
        assert result["status"] in ("skipped", "error")
