"""
Tests for the check_target_availability scanner task.
"""

import datetime
import uuid as uuid_mod
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

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

    def test_unsorted_dates(self) -> None:
        dates = [
            datetime.date(2026, 9, 3),
            datetime.date(2026, 9, 1),
            datetime.date(2026, 9, 2),
        ]
        assert _longest_consecutive(dates) == 3

    def test_all_same_date(self) -> None:
        dates = [
            datetime.date(2026, 9, 1),
            datetime.date(2026, 9, 1),
            datetime.date(2026, 9, 1),
        ]
        assert _longest_consecutive(dates) == 1


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

    def test_preferred_types_empty_list(self) -> None:
        """Empty preferred_types should match any type."""
        campsite = self._make_campsite(CampsiteType.CABIN)
        scan = self._make_scan(preferred_types=[])
        assert _matches_scan_filters(campsite, scan) is True


class TestScannerTask:
    """Tests for the check_target_availability task."""

    def test_task_returns_error_for_unknown_target(self) -> None:
        """Task should return error for non-existent target_id."""
        from worker.tasks.scanner import check_target_availability

        fake_id = str(uuid_mod.uuid4())
        result = check_target_availability(fake_id)
        assert result is not None
        assert result["status"] in ("skipped", "error")


class TestScannerTaskAsync:
    """Mock-based tests for the async scanner logic."""

    @pytest.mark.anyio
    async def test_check_async_lock_unavailable(self) -> None:
        from worker.tasks.scanner import _check_target_availability_async

        mock_self = MagicMock()
        target_id = str(uuid_mod.uuid4())

        with patch(
            "worker.tasks.scanner.ValkeyLock.acquire",
            new_callable=AsyncMock,
        ) as mock_acquire:
            mock_acquire.side_effect = Exception("Valkey unavailable")

            result = await _check_target_availability_async(mock_self, target_id)

        assert result["status"] == "skipped"  # type: ignore[index]
        assert result["reason"] == "valkey_unavailable"  # type: ignore[index]

    @pytest.mark.anyio
    async def test_check_async_lock_held(self) -> None:
        from worker.tasks.scanner import _check_target_availability_async

        mock_self = MagicMock()
        target_id = str(uuid_mod.uuid4())

        with patch(
            "worker.tasks.scanner.ValkeyLock.acquire",
            new_callable=AsyncMock,
        ) as mock_acquire:
            mock_acquire.return_value = False

            result = await _check_target_availability_async(mock_self, target_id)

        assert result["status"] == "skipped"  # type: ignore[index]
        assert result["reason"] == "lock_held"  # type: ignore[index]

    @pytest.mark.anyio
    async def test_check_async_target_not_found(self) -> None:
        from worker.tasks.scanner import _check_target_availability_async

        mock_self = MagicMock()
        target_id = str(uuid_mod.uuid4())

        with patch(
            "worker.tasks.scanner.ValkeyLock.acquire",
            new_callable=AsyncMock,
        ) as mock_acquire:
            mock_acquire.return_value = True

            with patch(
                "worker.tasks.scanner.ValkeyLock.release",
                new_callable=AsyncMock,
            ) as mock_release:
                mock_release.return_value = True

                mock_session = AsyncMock()
                mock_cursor = MagicMock()
                mock_cursor.scalar_one_or_none.return_value = None
                mock_session.execute.return_value = mock_cursor

                mock_ctx = AsyncMock()
                mock_ctx.__aenter__.return_value = mock_session
                mock_ctx.__aexit__.return_value = None

                mock_db = MagicMock()
                mock_db.get_session.return_value = mock_ctx

                with patch("worker.tasks.scanner.db", mock_db):
                    result = await _check_target_availability_async(
                        mock_self, target_id
                    )

        assert result["status"] == "error"  # type: ignore[index]
        assert result["reason"] == "target_not_found"  # type: ignore[index]
        mock_release.assert_called_once()

    @pytest.mark.anyio
    async def test_check_async_campground_not_found(self) -> None:
        from worker.tasks.scanner import _check_target_availability_async

        mock_self = MagicMock()
        target_id = str(uuid_mod.uuid4())
        target_uuid = uuid_mod.uuid4()

        mock_target = MagicMock()
        mock_target.id = target_uuid
        mock_target.provider_id = 1
        mock_target.campground_id = "cg_missing"

        with patch(
            "worker.tasks.scanner.ValkeyLock.acquire",
            new_callable=AsyncMock,
        ) as mock_acquire:
            mock_acquire.return_value = True

            with patch(
                "worker.tasks.scanner.ValkeyLock.release",
                new_callable=AsyncMock,
            ) as mock_release:
                mock_release.return_value = True

                # Target found, campground not found
                cursor_target = MagicMock()
                cursor_target.scalar_one_or_none.return_value = mock_target
                cursor_cg = MagicMock()
                cursor_cg.scalar_one_or_none.return_value = None

                mock_session = AsyncMock()
                mock_session.execute.side_effect = [cursor_target, cursor_cg]

                mock_ctx = AsyncMock()
                mock_ctx.__aenter__.return_value = mock_session
                mock_ctx.__aexit__.return_value = None

                mock_db = MagicMock()
                mock_db.get_session.return_value = mock_ctx

                with patch("worker.tasks.scanner.db", mock_db):
                    result = await _check_target_availability_async(
                        mock_self, target_id
                    )

        assert result["status"] == "error"  # type: ignore[index]
        assert result["reason"] == "campground_not_found"  # type: ignore[index]
        mock_release.assert_called_once()

    @pytest.mark.anyio
    async def test_check_async_success_basic(self) -> None:
        """
        Minimal success path through the scanner.

        We test the function end-to-end with full mock of DB and provider.
        The function's inner ``finally`` block handles cleanup.
        """
        from worker.tasks.scanner import _check_target_availability_async

        mock_self = MagicMock()
        mock_self.retry = MagicMock()
        target_id = str(uuid_mod.uuid4())
        target_uuid_obj = uuid_mod.UUID(target_id)

        # Setup lock patch at class level to avoid ValkeyLock import issues
        mock_lock = AsyncMock()
        mock_lock.acquire = AsyncMock(return_value=True)
        mock_lock.release = AsyncMock(return_value=True)
        mock_lock.close = AsyncMock()

        # We'll patch the ValkeyLock constructor
        with patch("worker.tasks.scanner.ValkeyLock", return_value=mock_lock):

            mock_target = MagicMock()
            mock_target.id = target_uuid_obj
            mock_target.provider_id = 1
            mock_target.campground_id = "cg_1"
            mock_target.start_date = datetime.date(2026, 9, 1)
            mock_target.end_date = datetime.date(2026, 9, 3)
            mock_target.last_checked_at = None

            mock_campground = MagicMock()
            mock_campground.id = "cg_1"
            mock_campground.name = "Test Campground"
            mock_campground.provider_id = 1

            # Use a real CampsiteDTO to ensure .value works on campsite_type
            from providers.dto import CampsiteDTO as RealCampsiteDTO
            real_campsite = RealCampsiteDTO(
                campsite_id="site_1",
                campsite_name="Site 1",
                campsite_type=CampsiteType.TENT,
                capacity=6,
                available_dates=[datetime.date(2026, 9, 1)],
                is_electric=False,
                is_accessible=False,
            )

            mock_session = MagicMock()
            mock_session.execute = AsyncMock()
            mock_session.execute.side_effect = [
                MagicMock(scalar_one_or_none=MagicMock(return_value=mock_target)),
                MagicMock(scalar_one_or_none=MagicMock(return_value=mock_campground)),
                MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[])))),
                MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[])))),
                MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[])))),
            ]
            mock_session.add_all = MagicMock()
            mock_session.add = MagicMock()
            mock_session.commit = AsyncMock()

            mock_ctx = MagicMock()
            mock_ctx.__aenter__ = AsyncMock(return_value=mock_session)
            mock_ctx.__aexit__ = AsyncMock(return_value=None)

            mock_db = MagicMock()
            mock_db.get_session.return_value = mock_ctx

            mock_provider = MagicMock()
            mock_provider.find_availabilities = AsyncMock(return_value=[real_campsite])
            mock_provider.async_client = MagicMock(aclose=AsyncMock())

            mock_provider_cls = MagicMock(return_value=mock_provider)
            mock_provider_cls.get_campground_url = MagicMock(return_value="https://book")

            with patch("worker.tasks.scanner.db", mock_db):
                with patch.dict(
                    "worker.tasks.scanner.PROVIDERS",
                    {1: mock_provider_cls},
                ):
                    with patch("worker.tasks.scanner.celery_app"):
                        result = await _check_target_availability_async(
                            mock_self, target_id
                        )

        assert result["status"] == "success", f"Got: {result}"  # type: ignore[index]
        assert result["availabilities_found"] == 1  # type: ignore[index]
