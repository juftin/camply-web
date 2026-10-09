"""
Tests for Admin Router endpoints (user, scan, target, overview, and audit).
"""

from __future__ import annotations

import datetime as dt
import uuid
from typing import Generator

import pytest
from conftest import maker
from fastapi.testclient import TestClient
from sqlalchemy import select

from backend.app import app
from backend.auth import CurrentUser, resolve_current_user
from db.models import (
    AdminAuditEvent,
    ScanResult,
    UniqueTarget,
    User,
    UserScan,
)


@pytest.fixture
def admin_user_data() -> dict:
    u_id = uuid.uuid4()
    return {
        "id": u_id,
        "email": f"admin_test_{u_id.hex[:6]}@camply.local",
        "is_admin": True,
        "scanning_enabled": True,
        "is_early_access_user": True,
    }


@pytest.fixture
def regular_user_data() -> dict:
    u_id = uuid.uuid4()
    return {
        "id": u_id,
        "email": f"regular_test_{u_id.hex[:6]}@camply.local",
        "is_admin": False,
        "scanning_enabled": True,
        "is_early_access_user": True,
    }


@pytest.fixture
def override_admin(admin_user_data: dict) -> Generator[CurrentUser, None, None]:
    curr = CurrentUser(
        id=admin_user_data["id"],
        email=admin_user_data["email"],
        is_early_access_user=True,
        is_admin=True,
        scanning_enabled=True,
    )
    app.dependency_overrides[resolve_current_user] = lambda: curr
    yield curr
    app.dependency_overrides.pop(resolve_current_user, None)


@pytest.fixture
def override_non_admin(regular_user_data: dict) -> Generator[CurrentUser, None, None]:
    curr = CurrentUser(
        id=regular_user_data["id"],
        email=regular_user_data["email"],
        is_early_access_user=True,
        is_admin=False,
        scanning_enabled=True,
    )
    app.dependency_overrides[resolve_current_user] = lambda: curr
    yield curr
    app.dependency_overrides.pop(resolve_current_user, None)


class TestAdminAuthorization:
    """Test that all admin endpoints reject non-admin access with 403."""

    endpoints = [
        ("GET", "/api/admin/overview", None),
        ("GET", "/api/admin/users", None),
        ("GET", f"/api/admin/users/{uuid.uuid4()}", None),
        ("PATCH", f"/api/admin/users/{uuid.uuid4()}", {"scanning_enabled": False}),
        ("GET", "/api/admin/scans", None),
        ("GET", f"/api/admin/scans/{uuid.uuid4()}", None),
        ("PATCH", f"/api/admin/scans/{uuid.uuid4()}", {"is_active": False}),
        ("GET", f"/api/admin/targets/{uuid.uuid4()}", None),
        ("GET", "/api/admin/audit", None),
    ]

    def test_non_admin_forbidden_on_all_endpoints(
        self, test_client: TestClient, override_non_admin: CurrentUser
    ) -> None:
        for method, path, json_data in self.endpoints:
            if method == "GET":
                resp = test_client.get(path)
            elif method == "PATCH":
                resp = test_client.patch(path, json=json_data)
            assert resp.status_code == 403, f"{method} {path} did not return 403"
            assert resp.json()["detail"]["error"] == "ERR_ADMIN_REQUIRED"


class TestAdminEndpoints:
    """Test functionality of all admin endpoints."""

    @pytest.mark.asyncio
    async def test_admin_overview_and_staleness(
        self, test_client: TestClient, override_admin: CurrentUser
    ) -> None:
        # Seed test data for overview
        async with maker() as session:
            admin_u = User(
                id=override_admin.id,
                email=override_admin.email,
                is_admin=True,
                scanning_enabled=True,
            )
            suspended_u = User(
                id=uuid.uuid4(),
                email="over_susp@example.com",
                is_admin=False,
                scanning_enabled=False,
            )
            active_u = User(
                id=uuid.uuid4(),
                email="over_act@example.com",
                is_admin=False,
                scanning_enabled=True,
            )
            session.add_all([admin_u, suspended_u, active_u])

            # Target 1: active and recently checked
            t1 = UniqueTarget(
                provider_id=1,
                campground_id="cg_1",
                start_date=dt.date(2026, 11, 1),
                end_date=dt.date(2026, 11, 3),
                last_checked_at=dt.datetime.now(tz=dt.timezone.utc),
            )
            # Target 2: active subscriber but never checked and old -> overdue
            t2 = UniqueTarget(
                provider_id=1,
                campground_id="cg_1",
                start_date=dt.date(2026, 11, 5),
                end_date=dt.date(2026, 11, 7),
                created_at=dt.datetime.now(tz=dt.timezone.utc)
                - dt.timedelta(seconds=500),
            )
            # Target 3: only suspended subscriber -> dormant
            t3 = UniqueTarget(
                provider_id=1,
                campground_id="cg_1",
                start_date=dt.date(2026, 11, 9),
                end_date=dt.date(2026, 11, 11),
                created_at=dt.datetime.now(tz=dt.timezone.utc)
                - dt.timedelta(seconds=500),
            )
            session.add_all([t1, t2, t3])
            await session.flush()

            # Scans
            s1 = UserScan(user_id=active_u.id, target_id=t1.id, is_active=True)
            s2 = UserScan(user_id=active_u.id, target_id=t2.id, is_active=True)
            s3 = UserScan(user_id=suspended_u.id, target_id=t3.id, is_active=True)
            session.add_all([s1, s2, s3])
            await session.commit()

        resp = test_client.get("/api/admin/overview")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_users"] >= 3
        assert data["scanning_enabled_users"] >= 2
        assert data["total_scans"] >= 3
        assert data["saved_active_scans"] >= 3
        assert data["eligible_scans"] >= 2
        assert data["eligible_targets"] >= 2
        assert data["overdue_targets"] >= 1

    @pytest.mark.asyncio
    async def test_admin_users_search_filter_redaction_and_patch(
        self, test_client: TestClient, override_admin: CurrentUser
    ) -> None:
        user_id = uuid.uuid4()
        user_email = f"searchable_{user_id.hex[:6]}@example.com"

        async with maker() as session:
            u = User(
                id=user_id,
                email=user_email,
                pushover_token="secret_token_123",
                scanning_enabled=True,
                is_early_access_user=True,
            )
            session.add(u)
            await session.commit()

        # 1. Search by email
        resp = test_client.get(f"/api/admin/users?search={user_email[:12]}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1
        matched = [x for x in data["users"] if x["id"] == str(user_id)]
        assert len(matched) == 1
        assert matched[0]["has_pushover_token"] is True
        assert "secret_token_123" not in str(resp.json())  # redaction check

        # 2. Get user detail
        detail_resp = test_client.get(f"/api/admin/users/{user_id}")
        assert detail_resp.status_code == 200
        assert detail_resp.json()["has_pushover_token"] is True
        assert "secret_token_123" not in str(detail_resp.json())

        # 3. Patch scanning_enabled and verify audit
        patch_resp = test_client.patch(
            f"/api/admin/users/{user_id}",
            json={"scanning_enabled": False},
        )
        assert patch_resp.status_code == 200
        assert patch_resp.json()["scanning_enabled"] is False

        # Verify DB and audit event
        async with maker() as session:
            u_check = (
                await session.execute(select(User).where(User.id == user_id))
            ).scalar_one()
            assert u_check.scanning_enabled is False

            audit_res = await session.execute(
                select(AdminAuditEvent).where(
                    AdminAuditEvent.subject_id == user_id,
                    AdminAuditEvent.action == "user.scanning_enabled",
                )
            )
            audit = audit_res.scalar_one()
            assert audit.actor_id == override_admin.id
            assert audit.prev_value is True
            assert audit.new_value is False

    @pytest.mark.asyncio
    async def test_admin_scans_management_and_target_detail(
        self, test_client: TestClient, override_admin: CurrentUser
    ) -> None:
        user_id = uuid.uuid4()
        target_id = uuid.uuid4()
        scan_id = uuid.uuid4()

        async with maker() as session:
            admin_u = User(
                id=override_admin.id,
                email=override_admin.email,
                is_admin=True,
                scanning_enabled=True,
            )
            u = User(
                id=user_id,
                email=f"scan_admin_{user_id.hex[:6]}@example.com",
                scanning_enabled=True,
            )
            t = UniqueTarget(
                id=target_id,
                provider_id=1,
                campground_id="cg_1",
                start_date=dt.date(2026, 12, 10),
                end_date=dt.date(2026, 12, 12),
            )
            s = UserScan(
                id=scan_id,
                user_id=u.id,
                target_id=t.id,
                is_active=True,
            )
            res = ScanResult(
                target_id=t.id,
                campsite_id="site_admin_1",
                available_dates=["2026-12-10"],
            )
            session.add_all([admin_u, u, t, s, res])
            await session.commit()

        # 1. List admin scans
        list_resp = test_client.get(f"/api/admin/scans?owner_id={user_id}")
        assert list_resp.status_code == 200
        assert list_resp.json()["total"] == 1
        item = list_resp.json()["scans"][0]
        assert item["id"] == str(scan_id)
        assert item["is_active"] is True
        assert item["is_eligible"] is True

        # 2. Get scan detail
        detail_resp = test_client.get(f"/api/admin/scans/{scan_id}")
        assert detail_resp.status_code == 200
        assert detail_resp.json()["id"] == str(scan_id)
        assert len(detail_resp.json()["results"]) == 1
        assert detail_resp.json()["results"][0]["campsite_id"] == "site_admin_1"

        # 3. Patch scan is_active=False
        pause_resp = test_client.patch(
            f"/api/admin/scans/{scan_id}",
            json={"is_active": False},
        )
        assert pause_resp.status_code == 200
        assert pause_resp.json()["is_active"] is False
        assert pause_resp.json()["is_eligible"] is False

        # 4. Suspend user then attempt to resume scan -> expect 403
        async with maker() as session:
            user_row = (
                await session.execute(select(User).where(User.id == user_id))
            ).scalar_one()
            user_row.scanning_enabled = False
            await session.commit()

        resume_forbidden = test_client.patch(
            f"/api/admin/scans/{scan_id}",
            json={"is_active": True},
        )
        assert resume_forbidden.status_code == 403
        assert resume_forbidden.json()["detail"]["error"] == "ERR_SCANNING_DISABLED"

        # 5. Target detail
        t_resp = test_client.get(f"/api/admin/targets/{target_id}")
        assert t_resp.status_code == 200
        t_data = t_resp.json()
        assert t_data["id"] == str(target_id)
        assert t_data["total_subscribers"] == 1
        assert t_data["eligible_subscribers"] == 0
        assert t_data["status"] == "dormant"
        assert len(t_data["subscribers"]) == 1

        # 6. Audit list endpoint
        audit_resp = test_client.get("/api/admin/audit")
        assert audit_resp.status_code == 200
        assert audit_resp.json()["total"] >= 1
        latest = audit_resp.json()["events"][0]
        assert latest["actor_email"] == override_admin.email
