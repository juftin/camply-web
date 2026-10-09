"""
Regression tests for administrator authorization, user suspension, and preserved scan state.
"""

from __future__ import annotations

import uuid

import pytest
from conftest import maker
from fastapi.testclient import TestClient

from backend.app import app
from backend.auth import AdminUserDep, CurrentUserDep
from db.models import UniqueTarget, User, UserScan


# Dummy endpoint to test require_admin / AdminUserDep
@app.get("/api/test-admin-gate")
def _test_admin_gate(admin: AdminUserDep) -> dict:
    return {"status": "ok", "admin_id": str(admin.id), "is_admin": admin.is_admin}


@app.get("/api/test-user-gate")
def _test_user_gate(user: CurrentUserDep) -> dict:
    return {
        "status": "ok",
        "user_id": str(user.id),
        "scanning_enabled": user.scanning_enabled,
    }


class TestSuspensionAndAdminAuth:
    """Test administrator authorization and user suspension end-to-end."""

    @pytest.mark.asyncio
    async def test_require_admin_allows_admin_rejects_non_admin(
        self, test_client: TestClient
    ) -> None:
        """Admin guard allows users with is_admin=True and returns 403 for is_admin=False."""
        admin_email = "superadmin@example.com"
        regular_email = "regular@example.com"

        async with maker() as session:
            admin_user = User(
                email=admin_email,
                is_admin=True,
                is_early_access_user=True,
            )
            regular_user = User(
                email=regular_email,
                is_admin=False,
                is_early_access_user=True,
            )
            session.add_all([admin_user, regular_user])
            await session.commit()

        # In basic mode with default credentials, user is the admin_email.
        # Let's test with custom app dependency override for CurrentUserDep
        from backend.auth import CurrentUser, resolve_current_user

        # Non-admin override
        app.dependency_overrides[resolve_current_user] = lambda: CurrentUser(
            id=regular_user.id,
            email=regular_email,
            is_early_access_user=True,
            is_admin=False,
            scanning_enabled=True,
        )

        resp = test_client.get("/api/test-admin-gate")
        assert resp.status_code == 403
        assert resp.json()["detail"]["error"] == "ERR_ADMIN_REQUIRED"

        # Admin override
        app.dependency_overrides[resolve_current_user] = lambda: CurrentUser(
            id=admin_user.id,
            email=admin_email,
            is_early_access_user=True,
            is_admin=True,
            scanning_enabled=True,
        )

        resp = test_client.get("/api/test-admin-gate")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"
        assert resp.json()["is_admin"] is True

        # Clean up override
        app.dependency_overrides.pop(resolve_current_user, None)

    @pytest.mark.asyncio
    async def test_suspended_user_cannot_create_or_resume_scan(
        self, test_client: TestClient
    ) -> None:
        """A suspended user (scanning_enabled=False) cannot create new scans or resume scans."""
        user_id = uuid.uuid4()
        user_email = f"suspended_{user_id.hex[:6]}@example.com"

        async with maker() as session:
            user = User(
                id=user_id,
                email=user_email,
                is_admin=False,
                scanning_enabled=False,
                is_early_access_user=True,
            )
            session.add(user)

            import datetime as dt

            # Add target and scan
            target = UniqueTarget(
                provider_id=1,
                campground_id="cg_1",
                start_date=dt.date(2026, 10, 15),
                end_date=dt.date(2026, 10, 17),
            )
            session.add(target)
            await session.flush()

            scan = UserScan(
                user_id=user.id,
                target_id=target.id,
                is_active=False,
            )
            session.add(scan)
            await session.commit()
            scan_id = scan.id

        from backend.auth import CurrentUser, resolve_current_user

        app.dependency_overrides[resolve_current_user] = lambda: CurrentUser(
            id=user_id,
            email=user_email,
            is_early_access_user=True,
            is_admin=False,
            scanning_enabled=False,
        )

        try:
            # 1. Suspended user can still get /api/me
            me_resp = test_client.get("/api/me")
            assert me_resp.status_code == 200
            assert me_resp.json()["scanning_enabled"] is False

            # 2. Suspended user cannot create scan
            create_resp = test_client.post(
                "/api/scans",
                json={
                    "provider_id": 1,
                    "campground_id": "cg_1",
                    "start_date": "2026-11-01",
                    "end_date": "2026-11-03",
                },
            )
            assert create_resp.status_code == 403
            assert create_resp.json()["detail"]["error"] == "ERR_SCANNING_DISABLED"

            # 3. Suspended user cannot resume scan (set is_active=True)
            resume_resp = test_client.patch(
                f"/api/scans/{scan_id}",
                json={"is_active": True},
            )
            assert resume_resp.status_code == 403
            assert resume_resp.json()["detail"]["error"] == "ERR_SCANNING_DISABLED"

            # 4. Suspended user CAN update filters without activating
            filter_resp = test_client.patch(
                f"/api/scans/{scan_id}",
                json={"min_stay_length": 3},
            )
            assert filter_resp.status_code == 200
            assert filter_resp.json()["min_stay_length"] == 3

            # 5. Suspended user CAN pause already active scans (set is_active=False)
            pause_resp = test_client.patch(
                f"/api/scans/{scan_id}",
                json={"is_active": False},
            )
            assert pause_resp.status_code == 200
            assert pause_resp.json()["is_active"] is False

            # 6. Suspended user CAN view scans
            list_resp = test_client.get("/api/scans")
            assert list_resp.status_code == 200
            assert len(list_resp.json()["scans"]) >= 1

            # 7. Suspended user CAN delete scan
            del_resp = test_client.delete(f"/api/scans/{scan_id}")
            assert del_resp.status_code == 204

        finally:
            app.dependency_overrides.pop(resolve_current_user, None)

    @pytest.mark.asyncio
    async def test_re_enabling_restores_eligibility_and_preserves_paused_state(
        self, test_client: TestClient
    ) -> None:
        """Re-enabling scanning restores resumption and preserves individual paused scans."""
        user_id = uuid.uuid4()
        user_email = f"restored_{user_id.hex[:6]}@example.com"

        async with maker() as session:
            user = User(
                id=user_id,
                email=user_email,
                is_admin=False,
                scanning_enabled=True,
                is_early_access_user=True,
            )
            session.add(user)

            import datetime as dt

            target1 = UniqueTarget(
                provider_id=1,
                campground_id="cg_1",
                start_date=dt.date(2026, 12, 1),
                end_date=dt.date(2026, 12, 3),
            )
            target2 = UniqueTarget(
                provider_id=1,
                campground_id="cg_1",
                start_date=dt.date(2026, 12, 5),
                end_date=dt.date(2026, 12, 7),
            )
            session.add_all([target1, target2])
            await session.flush()

            # Scan 1 was active, Scan 2 was paused by user
            scan1 = UserScan(user_id=user.id, target_id=target1.id, is_active=True)
            scan2 = UserScan(user_id=user.id, target_id=target2.id, is_active=False)
            session.add_all([scan1, scan2])
            await session.commit()

            # Suspend user
            user.scanning_enabled = False
            await session.commit()

            # Verify that suspension did NOT rewrite is_active in the database
            await session.refresh(scan1)
            await session.refresh(scan2)
            assert scan1.is_active is True
            assert scan2.is_active is False

            # Restore user
            user.scanning_enabled = True
            await session.commit()

            await session.refresh(scan1)
            await session.refresh(scan2)
            assert scan1.is_active is True
            assert scan2.is_active is False
