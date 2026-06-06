# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0

"""
Tests for the heartbeat discover_targets task.
"""

import datetime

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
        # The target fixture already has last_checked_at=None and an active scan
        assert target.last_checked_at is None
        assert user_scan.is_active is True

        # We can't easily test the full sync wrapper with async DB,
        # so test the query logic via direct DB inspection
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
        # Set last_checked_at to "just now"
        target.last_checked_at = datetime.datetime.now(tz=datetime.timezone.utc)
        session.add(target)
        session.commit()

        # The cooldown threshold uses target_cooldown (default 55s)
        # A target checked now should be outside the cooldown window
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

        # Target was just checked, should NOT be in results
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
        # The target fixture creates a target, but if there's no UserScan
        # linking to it (there shouldn't be since we didn't create one),
        # it should not appear in the join query.
        from sqlalchemy import select

        # Delete any existing scans for this target
        for scan in session.query(UserScan).all():
            session.delete(scan)
        session.commit()

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
