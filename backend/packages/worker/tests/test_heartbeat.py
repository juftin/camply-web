"""
Tests for the heartbeat discover_targets task.
"""

import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.orm import Session

from db.models import UniqueTarget, UserScan


class TestDiscoverTargets:
    """Tests for the heartbeat target discovery logic."""

    def test_never_checked_target_discovered(
        self, session: Session, target: UniqueTarget, user_scan: UserScan
    ) -> None:
        """
        A target with last_checked_at=None and an active UserScan
        should be discovered.
        """
        assert target.last_checked_at is None
        assert user_scan.is_active is True

        from sqlalchemy import select

        stmt = (
            select(UniqueTarget)
            .join(UserScan, UserScan.target_id == UniqueTarget.id)
            .where(
                UserScan.is_active == True,  # noqa: E712
                (UniqueTarget.last_checked_at == None),  # noqa: E711
            )
            .distinct()
        )
        result = session.execute(stmt)
        targets = result.scalars().all()

        assert len(targets) == 1
        assert targets[0].id == target.id

    def test_recently_checked_target_excluded(
        self, session: Session, target: UniqueTarget, user_scan: UserScan
    ) -> None:
        """
        A target checked very recently should NOT be discovered
        (within cooldown period).
        """
        target.last_checked_at = datetime.datetime.now(tz=datetime.timezone.utc)
        session.add(target)
        session.commit()

        from datetime import timedelta, timezone

        now = datetime.datetime.now(tz=timezone.utc)
        cooldown = now - timedelta(seconds=55)

        from sqlalchemy import select

        stmt = (
            select(UniqueTarget)
            .join(UserScan, UserScan.target_id == UniqueTarget.id)
            .where(
                UserScan.is_active == True,  # noqa: E712
                (
                    (UniqueTarget.last_checked_at == None)  # noqa: E711
                    | (UniqueTarget.last_checked_at < cooldown)
                ),
            )
            .distinct()
        )
        result = session.execute(stmt)
        targets = result.scalars().all()

        assert len(targets) == 0

    def test_stale_target_discovered(
        self, session: Session, target: UniqueTarget, user_scan: UserScan
    ) -> None:
        """
        A target checked more than cooldown seconds ago should be discovered.
        """
        from datetime import timedelta, timezone

        target.last_checked_at = datetime.datetime.now(tz=timezone.utc) - timedelta(
            seconds=120
        )
        session.add(target)
        session.commit()

        now = datetime.datetime.now(tz=timezone.utc)
        cooldown = now - timedelta(seconds=55)

        from sqlalchemy import select

        stmt = (
            select(UniqueTarget)
            .join(UserScan, UserScan.target_id == UniqueTarget.id)
            .where(
                UserScan.is_active == True,  # noqa: E712
                (
                    (UniqueTarget.last_checked_at == None)  # noqa: E711
                    | (UniqueTarget.last_checked_at < cooldown)
                ),
            )
            .distinct()
        )
        result = session.execute(stmt)
        targets = result.scalars().all()

        assert len(targets) == 1
        assert targets[0].id == target.id

    def test_inactive_scan_excluded(
        self, session: Session, target: UniqueTarget, user_scan: UserScan
    ) -> None:
        """
        A target with only inactive UserScans should NOT be discovered.
        """
        user_scan.is_active = False
        session.add(user_scan)
        session.commit()

        from sqlalchemy import select

        stmt = (
            select(UniqueTarget)
            .join(UserScan, UserScan.target_id == UniqueTarget.id)
            .where(
                UserScan.is_active == True,  # noqa: E712
            )
            .distinct()
        )
        result = session.execute(stmt)
        targets = result.scalars().all()

        assert len(targets) == 0

    def test_no_scans_target_excluded(
        self, session: Session, target: UniqueTarget
    ) -> None:
        """
        A target with no linked UserScans should NOT be discovered.
        """
        for scan in session.query(UserScan).all():
            session.delete(scan)
        session.commit()

        from sqlalchemy import select

        stmt = (
            select(UniqueTarget)
            .join(UserScan, UserScan.target_id == UniqueTarget.id)
            .where(
                UserScan.is_active == True,  # noqa: E712
            )
            .distinct()
        )
        result = session.execute(stmt)
        targets = result.scalars().all()

        assert len(targets) == 0


class TestDiscoverTargetsAsync:
    """Tests for the async _discover_targets_async function."""

    @pytest.mark.anyio
    async def test_discover_targets_async_enqueues_tasks(self) -> None:
        """
        _discover_targets_async should discover due targets and enqueue
        check_target_availability tasks for each.
        """
        from worker.tasks.heartbeat import _discover_targets_async

        mock_target_1 = MagicMock(spec=UniqueTarget)
        mock_target_1.id = "target-1"
        mock_target_2 = MagicMock(spec=UniqueTarget)
        mock_target_2.id = "target-2"

        # Mock the DB session
        # NB: execute returns a CursorResult, .scalars() is sync and returns
        # a ScalarResult, .all() is sync
        mock_session = AsyncMock()
        mock_cursor = MagicMock()
        mock_scalar = MagicMock()
        mock_scalar.all.return_value = [
            mock_target_1,
            mock_target_2,
        ]
        mock_cursor.scalars.return_value = mock_scalar
        mock_session.execute.return_value = mock_cursor

        # Mock db.get_session as async context manager
        mock_db = MagicMock()
        mock_db.get_session.return_value = AsyncMock(
            __aenter__=AsyncMock(return_value=mock_session),
            __aexit__=AsyncMock(return_value=None),
        )

        with patch("worker.tasks.heartbeat.db", mock_db):
            with patch(
                "worker.tasks.heartbeat.celery_app"
            ) as mock_celery:
                result = await _discover_targets_async()

        assert result["discovered"] == 2
        assert result["enqueued"] == 2
        assert mock_celery.send_task.call_count == 2

    @pytest.mark.anyio
    async def test_discover_targets_async_empty(self) -> None:
        """
        _discover_targets_async should return zero counts when no
        targets are due.
        """
        from worker.tasks.heartbeat import _discover_targets_async

        mock_session = AsyncMock()
        mock_cursor = MagicMock()
        mock_scalar = MagicMock()
        mock_scalar.all.return_value = []
        mock_cursor.scalars.return_value = mock_scalar
        mock_session.execute.return_value = mock_cursor

        mock_db = MagicMock()
        mock_db.get_session.return_value = AsyncMock(
            __aenter__=AsyncMock(return_value=mock_session),
            __aexit__=AsyncMock(return_value=None),
        )

        with patch("worker.tasks.heartbeat.db", mock_db):
            with patch(
                "worker.tasks.heartbeat.celery_app"
            ) as mock_celery:
                result = await _discover_targets_async()

        assert result["discovered"] == 0
        assert result["enqueued"] == 0
        mock_celery.send_task.assert_not_called()


class TestDiscoverTargetsSync:
    """Tests for the sync discover_targets wrapper task."""

    def test_discover_targets_wrapper_calls_async(self) -> None:
        """
        The sync discover_targets task should call _discover_targets_async
        and return its result.
        """
        from worker.tasks.heartbeat import discover_targets

        with patch(
            "worker.tasks.heartbeat._discover_targets_async",
            new_callable=AsyncMock,
        ) as mock_async:
            mock_async.return_value = {"discovered": 3, "enqueued": 3}

            result = discover_targets()

        assert result["discovered"] == 3
        assert result["enqueued"] == 3

    def test_discover_targets_error_handling(self) -> None:
        """
        When the async function raises, discover_targets should catch it
        and return an error dict.
        """
        from worker.tasks.heartbeat import discover_targets

        with patch(
            "worker.tasks.heartbeat._discover_targets_async",
            new_callable=AsyncMock,
        ) as mock_async:
            mock_async.side_effect = Exception("Test error")

            result = discover_targets()

        assert result["status"] == "error"
