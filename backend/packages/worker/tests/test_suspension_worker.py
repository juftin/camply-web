"""
Worker tests for user suspension, shared-target behavior, and eligibility enforcement.
"""

import datetime
import uuid as uuid_mod
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.orm import Session

from db.models import Campground, Provider, UniqueTarget, User, UserScan
from worker.tasks.notifications import (
    _send_pushover_notification_async,
)
from worker.tasks.scanner import _check_target_availability_async


@pytest.fixture(name="two_users_shared_target")
def two_users_shared_target_fixture(
    session: Session,
) -> tuple[User, User, UniqueTarget, UserScan, UserScan]:
    provider = Provider(name="Recreation.gov", url="https://recreation.gov", id=1)
    session.add(provider)
    session.commit()

    campground = Campground(id="cg_test", provider_id=1, name="Shared CG")
    session.add(campground)
    session.commit()

    user_a = User(
        email="user_a@example.com",
        pushover_token="token_a",
        scanning_enabled=True,
    )
    user_b = User(
        email="user_b@example.com",
        pushover_token="token_b",
        scanning_enabled=True,
    )
    session.add_all([user_a, user_b])
    session.commit()

    target = UniqueTarget(
        provider_id=1,
        campground_id="cg_test",
        start_date=datetime.date(2026, 9, 10),
        end_date=datetime.date(2026, 9, 12),
    )
    session.add(target)
    session.commit()

    scan_a = UserScan(user_id=user_a.id, target_id=target.id, is_active=True)
    scan_b = UserScan(user_id=user_b.id, target_id=target.id, is_active=True)
    session.add_all([scan_a, scan_b])
    session.commit()

    return user_a, user_b, target, scan_a, scan_b


class TestSuspensionWorker:
    """Test worker behavior when users are suspended."""

    def test_heartbeat_discovery_skips_target_when_all_subscribers_suspended(
        self, session: Session, two_users_shared_target: tuple
    ) -> None:
        """When all subscribers are suspended, target is not discovered."""
        user_a, user_b, target, scan_a, scan_b = two_users_shared_target

        user_a.scanning_enabled = False
        user_b.scanning_enabled = False
        session.commit()

        from sqlalchemy import select

        from db.eligibility import eligible_scan_condition

        stmt = (
            select(UniqueTarget)
            .join(UserScan, UserScan.target_id == UniqueTarget.id)
            .join(User, User.id == UserScan.user_id)
            .where(eligible_scan_condition())
            .distinct()
        )
        targets = session.execute(stmt).scalars().all()
        assert len(targets) == 0

    def test_heartbeat_discovery_continues_when_one_subscriber_eligible(
        self, session: Session, two_users_shared_target: tuple
    ) -> None:
        """Shared target continues being discovered if at least one subscriber is eligible."""
        user_a, user_b, target, scan_a, scan_b = two_users_shared_target

        user_a.scanning_enabled = False
        user_b.scanning_enabled = True
        session.commit()

        from sqlalchemy import select

        from db.eligibility import eligible_scan_condition

        stmt = (
            select(UniqueTarget)
            .join(UserScan, UserScan.target_id == UniqueTarget.id)
            .join(User, User.id == UserScan.user_id)
            .where(eligible_scan_condition())
            .distinct()
        )
        targets = session.execute(stmt).scalars().all()
        assert len(targets) == 1
        assert targets[0].id == target.id

    @pytest.mark.anyio
    async def test_scanner_skips_when_no_eligible_subscribers(self) -> None:
        """Scanner skips target before provider call if no eligible subscribers remain."""
        target_id = str(uuid_mod.uuid4())
        mock_self = MagicMock()
        mock_lock = AsyncMock()
        mock_lock.acquire = AsyncMock(return_value=True)
        mock_lock.release = AsyncMock(return_value=True)
        mock_lock.close = AsyncMock()

        mock_target = MagicMock()
        mock_target.id = uuid_mod.UUID(target_id)
        mock_target.provider_id = 1
        mock_target.campground_id = "cg_1"

        mock_campground = MagicMock()
        mock_campground.id = "cg_1"
        mock_campground.name = "Test CG"

        mock_session = MagicMock()
        mock_session.execute = AsyncMock()
        # 1: target, 2: campground, 3: subscriber count = 0
        mock_session.execute.side_effect = [
            MagicMock(scalar_one_or_none=MagicMock(return_value=mock_target)),
            MagicMock(scalar_one_or_none=MagicMock(return_value=mock_campground)),
            MagicMock(scalar=MagicMock(return_value=0)),
        ]

        mock_ctx = MagicMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=mock_session)
        mock_ctx.__aexit__ = AsyncMock(return_value=None)
        mock_db = MagicMock(get_session=MagicMock(return_value=mock_ctx))

        with patch("worker.tasks.scanner.ValkeyLock", return_value=mock_lock):
            with patch("worker.tasks.scanner.db", mock_db):
                result = await _check_target_availability_async(mock_self, target_id)

        assert result == {"status": "skipped", "reason": "no_eligible_subscribers"}

    @pytest.mark.anyio
    async def test_notification_delivery_suspension_checks(self) -> None:
        """Notification delivery enforces user suspension and scan inactive status."""
        user_id = str(uuid_mod.uuid4())
        scan_id = str(uuid_mod.uuid4())
        mock_self = MagicMock()

        notification = {
            "title": "Available",
            "message": "Camp available",
            "park_name": "Test Park",
            "campsite_name": "Site 1",
            "start_date": "2026-09-01",
            "end_date": "2026-09-03",
        }

        # Case 1: user is suspended
        suspended_user = User(
            id=uuid_mod.UUID(user_id),
            email="susp@example.com",
            pushover_token="tok",
            scanning_enabled=False,
        )
        mock_session = MagicMock()
        mock_session.execute = AsyncMock(
            return_value=MagicMock(
                scalar_one_or_none=MagicMock(return_value=suspended_user)
            )
        )
        mock_ctx = MagicMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=mock_session)
        mock_ctx.__aexit__ = AsyncMock(return_value=None)
        mock_db = MagicMock(get_session=MagicMock(return_value=mock_ctx))

        with patch("worker.tasks.notifications.db", mock_db):
            res = await _send_pushover_notification_async(
                mock_self, user_id, notification, scan_id=scan_id
            )
        assert res == {"status": "skipped", "reason": "user_suspended"}

        # Case 2: user enabled, but scan is paused (is_active=False)
        active_user = User(
            id=uuid_mod.UUID(user_id),
            email="act@example.com",
            pushover_token="tok",
            scanning_enabled=True,
        )
        paused_scan = UserScan(
            id=uuid_mod.UUID(scan_id),
            user_id=uuid_mod.UUID(user_id),
            target_id=uuid_mod.uuid4(),
            is_active=False,
        )
        mock_session.execute = AsyncMock(
            side_effect=[
                MagicMock(scalar_one_or_none=MagicMock(return_value=active_user)),
                MagicMock(scalar_one_or_none=MagicMock(return_value=paused_scan)),
            ]
        )
        with patch("worker.tasks.notifications.db", mock_db):
            res = await _send_pushover_notification_async(
                mock_self, user_id, notification, scan_id=scan_id
            )
        assert res == {"status": "skipped", "reason": "scan_inactive"}

        # Case 3: old queued message without scan_id, user suspended
        mock_session.execute = AsyncMock(
            return_value=MagicMock(
                scalar_one_or_none=MagicMock(return_value=suspended_user)
            )
        )
        with patch("worker.tasks.notifications.db", mock_db):
            res = await _send_pushover_notification_async(
                mock_self, user_id, notification, scan_id=None
            )
        assert res == {"status": "skipped", "reason": "user_suspended"}
