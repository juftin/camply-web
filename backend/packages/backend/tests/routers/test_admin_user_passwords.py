"""Tests for admin user creation, password assignment, and forced password change."""

from __future__ import annotations

import uuid
from typing import Generator

import jwt
import pytest
from conftest import maker
from fastapi.testclient import TestClient
from sqlalchemy import select

from backend.app import app
from backend.auth import CurrentUser, resolve_current_user, session_signing_key
from backend.config import AuthMode, backend_config
from db.models import AdminAuditEvent, User


@pytest.fixture
def session_mode(monkeypatch: pytest.MonkeyPatch) -> Generator[None, None, None]:
    """Configure synthetic shared credentials and cookie session mode."""
    monkeypatch.setattr(backend_config, "auth_mode", AuthMode.SESSION)
    monkeypatch.setattr(
        backend_config, "admin_email", f"admin_{uuid.uuid4().hex}@camply.local"
    )
    monkeypatch.setattr(backend_config, "login_username", "test-admin")
    monkeypatch.setattr(backend_config, "login_password", "synthetic-test-password")
    monkeypatch.setattr(
        backend_config, "session_secret", "synthetic-session-secret-with-32-characters"
    )
    monkeypatch.setattr(backend_config, "session_cookie_secure", False)
    yield


@pytest.fixture
def override_admin_user() -> Generator[CurrentUser, None, None]:
    """Provide an authenticated administrator context."""
    u_id = uuid.uuid4()
    curr = CurrentUser(
        id=u_id,
        email=f"admin_{u_id.hex[:6]}@camply.local",
        is_invited=True,
        is_admin=True,
        scanning_enabled=True,
        must_change_password=False,
    )
    app.dependency_overrides[resolve_current_user] = lambda: curr
    yield curr
    app.dependency_overrides.pop(resolve_current_user, None)


def _login(client: TestClient, username: str, password: str) -> None:
    """Sign in and set the CSRF header on the client."""
    response = client.post(
        "/api/login",
        json={"username": username, "password": password},
    )
    assert response.status_code == 200
    client.headers["X-CSRF-Token"] = client.cookies["camply_csrf"]


def test_admin_create_user_in_session_mode(
    session_mode: None, test_client: TestClient, override_admin_user: CurrentUser
) -> None:
    """An admin can create a user with an assigned password and force password change."""
    test_email = f"newuser_{uuid.uuid4().hex[:6]}@example.com"
    payload = {
        "email": test_email,
        "password": "InitialTempPassword123!",
        "is_admin": False,
        "must_change_password": True,
        "scanning_enabled": True,
    }
    response = test_client.post("/api/admin/users", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == test_email
    assert data["is_admin"] is False
    assert data["must_change_password"] is True
    assert data["scanning_enabled"] is True
    assert "id" in data


def test_admin_create_user_conflict(
    session_mode: None, test_client: TestClient, override_admin_user: CurrentUser
) -> None:
    """Attempting to create a user with an existing email returns 409 Conflict."""
    test_email = f"duplicate_{uuid.uuid4().hex[:6]}@example.com"
    payload = {
        "email": test_email,
        "password": "Password123!",
        "must_change_password": False,
    }
    res1 = test_client.post("/api/admin/users", json=payload)
    assert res1.status_code == 201

    res2 = test_client.post("/api/admin/users", json=payload)
    assert res2.status_code == 409
    assert "already exists" in res2.json()["detail"]


def test_admin_create_user_rejects_non_session_mode(
    test_client: TestClient,
    override_admin_user: CurrentUser,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Creating a user with a password is only permitted in session auth mode."""
    monkeypatch.setattr(backend_config, "auth_mode", AuthMode.NONE)
    response = test_client.post(
        "/api/admin/users",
        json={"email": "test@example.com", "password": "Password123!"},
    )
    assert response.status_code == 400
    assert "session auth mode" in response.json()["detail"]


@pytest.mark.asyncio
async def test_admin_create_user_records_audit_event(
    session_mode: None, test_client: TestClient, override_admin_user: CurrentUser
) -> None:
    """Admin user creation records an audit event."""
    test_email = f"audit_{uuid.uuid4().hex[:6]}@example.com"
    response = test_client.post(
        "/api/admin/users",
        json={
            "email": test_email,
            "password": "Password123!",
            "must_change_password": True,
        },
    )
    assert response.status_code == 201
    user_id = uuid.UUID(response.json()["id"])

    async with maker() as session:
        stmt = select(AdminAuditEvent).where(
            AdminAuditEvent.subject_id == user_id,
            AdminAuditEvent.action == "user.create",
        )
        audit = (await session.execute(stmt)).scalar_one_or_none()
        assert audit is not None
        assert audit.actor_id == override_admin_user.id


def test_user_login_and_forced_password_change_workflow(
    session_mode: None, test_client: TestClient, override_admin_user: CurrentUser
) -> None:
    """End-to-end workflow: creation with forced change, restricted access, password update, and unlock."""
    test_email = f"flow_{uuid.uuid4().hex[:6]}@example.com"
    temp_password = "TemporaryPassword123!"
    new_password = "NewPermanentPassword456!"

    # 1. Admin creates user with must_change_password=True
    create_resp = test_client.post(
        "/api/admin/users",
        json={
            "email": test_email,
            "password": temp_password,
            "must_change_password": True,
        },
    )
    assert create_resp.status_code == 201

    # Remove admin override so we authenticate normally as the new user
    app.dependency_overrides.pop(resolve_current_user, None)

    # 2. User signs in with initial password
    login_resp = test_client.post(
        "/api/login", json={"username": test_email, "password": temp_password}
    )
    assert login_resp.status_code == 200
    profile = login_resp.json()
    assert profile["email"] == test_email
    assert profile["must_change_password"] is True
    test_client.headers["X-CSRF-Token"] = test_client.cookies["camply_csrf"]

    # 3. GET /me works and reflects must_change_password=True
    me_resp = test_client.get("/api/me")
    assert me_resp.status_code == 200
    assert me_resp.json()["must_change_password"] is True

    # 4. Mutations on /api/me and scan operations are blocked by require_password_not_expired
    patch_me = test_client.patch("/api/me", json={"pushover_token": "token123"})
    assert patch_me.status_code == 403
    assert patch_me.json()["detail"]["error"] == "ERR_PASSWORD_CHANGE_REQUIRED"

    scan_resp = test_client.post(
        "/api/scans",
        json={
            "provider_id": 1,
            "campground_id": "cg_1",
            "start_date": "2027-08-01",
            "end_date": "2027-08-05",
        },
    )
    assert scan_resp.status_code == 403
    assert scan_resp.json()["detail"]["error"] == "ERR_PASSWORD_CHANGE_REQUIRED"

    # 5. Attempt password change with incorrect current password
    fail_change = test_client.post(
        "/api/change-password",
        json={
            "current_password": "WrongPassword!",
            "new_password": new_password,
        },
    )
    assert fail_change.status_code == 400
    assert "incorrect" in fail_change.json()["detail"].lower()

    # 6. Change password successfully
    success_change = test_client.post(
        "/api/change-password",
        json={
            "current_password": temp_password,
            "new_password": new_password,
        },
    )
    assert success_change.status_code == 200
    assert success_change.json()["must_change_password"] is False

    # 7. GET /me now shows must_change_password=False
    me_after = test_client.get("/api/me")
    assert me_after.status_code == 200
    assert me_after.json()["must_change_password"] is False

    # 8. Profile update and scan operations now succeed!
    patch_me_after = test_client.patch("/api/me", json={"pushover_token": "token123"})
    assert patch_me_after.status_code == 200

    create_scan_after = test_client.post(
        "/api/scans",
        json={
            "provider_id": 1,
            "campground_id": "cg_1",
            "start_date": "2027-08-01",
            "end_date": "2027-08-05",
        },
    )
    assert create_scan_after.status_code == 201

    # 9. Sign out and verify login with old vs new password
    test_client.post("/api/logout")

    old_login = test_client.post(
        "/api/login", json={"username": test_email, "password": temp_password}
    )
    assert old_login.status_code == 401

    new_login = test_client.post(
        "/api/login", json={"username": test_email, "password": new_password}
    )
    assert new_login.status_code == 200
    assert new_login.json()["must_change_password"] is False


def test_admin_patch_user_password_and_flag(
    session_mode: None, test_client: TestClient, override_admin_user: CurrentUser
) -> None:
    """Admin can reset a user's password and toggle must_change_password via PATCH."""
    test_email = f"patch_{uuid.uuid4().hex[:6]}@example.com"
    create_resp = test_client.post(
        "/api/admin/users",
        json={
            "email": test_email,
            "password": "Password123!",
            "must_change_password": False,
        },
    )
    assert create_resp.status_code == 201
    user_id = create_resp.json()["id"]

    patch_resp = test_client.patch(
        f"/api/admin/users/{user_id}",
        json={
            "must_change_password": True,
            "password": "ResetPassword456!",
        },
    )
    assert patch_resp.status_code == 200
    data = patch_resp.json()
    assert data["must_change_password"] is True

    # User can now login with reset password
    app.dependency_overrides.pop(resolve_current_user, None)
    login_resp = test_client.post(
        "/api/login", json={"username": test_email, "password": "ResetPassword456!"}
    )
    assert login_resp.status_code == 200
    assert login_resp.json()["must_change_password"] is True


def test_admin_reset_password_defaults_to_must_change(
    session_mode: None, test_client: TestClient, override_admin_user: CurrentUser
) -> None:
    """Resetting a password automatically forces must_change_password=True on subsequent login."""
    test_email = f"auto_mcp_{uuid.uuid4().hex[:6]}@example.com"
    create_resp = test_client.post(
        "/api/admin/users",
        json={
            "email": test_email,
            "password": "InitialPass123!",
            "must_change_password": False,
        },
    )
    assert create_resp.status_code == 201
    user_id = create_resp.json()["id"]

    # Reset password only (without specifying must_change_password)
    patch_resp = test_client.patch(
        f"/api/admin/users/{user_id}",
        json={"password": "NewTemporaryPass789!"},
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["must_change_password"] is True

    # User subsequent login reflects must_change_password=True
    app.dependency_overrides.pop(resolve_current_user, None)
    login_resp = test_client.post(
        "/api/login", json={"username": test_email, "password": "NewTemporaryPass789!"}
    )
    assert login_resp.status_code == 200
    assert login_resp.json()["must_change_password"] is True


@pytest.mark.asyncio
async def test_admin_promote_and_demote_user(
    session_mode: None, test_client: TestClient, override_admin_user: CurrentUser
) -> None:
    """An administrator can promote and demote other users with audit events."""
    test_email = f"promote_{uuid.uuid4().hex[:6]}@example.com"
    create_resp = test_client.post(
        "/api/admin/users",
        json={
            "email": test_email,
            "password": "Password123!",
            "is_admin": False,
        },
    )
    assert create_resp.status_code == 201
    user_id = create_resp.json()["id"]

    # Promote to admin
    patch_resp = test_client.patch(
        f"/api/admin/users/{user_id}",
        json={"is_admin": True},
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["is_admin"] is True

    # Verify audit event for promotion
    async with maker() as db_session:
        stmt = select(AdminAuditEvent).where(
            AdminAuditEvent.subject_id == uuid.UUID(user_id),
            AdminAuditEvent.action == "user.is_admin",
        )
        events = (await db_session.execute(stmt)).scalars().all()
        assert len(events) == 1
        assert events[0].prev_value is False
        assert events[0].new_value is True

    # Demote back to user
    demote_resp = test_client.patch(
        f"/api/admin/users/{user_id}",
        json={"is_admin": False},
    )
    assert demote_resp.status_code == 200
    assert demote_resp.json()["is_admin"] is False


@pytest.mark.asyncio
async def test_admin_cannot_demote_self(
    session_mode: None, test_client: TestClient
) -> None:
    """An administrator cannot remove their own administrator privileges."""
    admin_id = uuid.uuid4()
    admin_user = CurrentUser(
        id=admin_id,
        email="selfadmin@example.com",
        is_invited=True,
        is_admin=True,
        scanning_enabled=True,
        must_change_password=False,
    )
    async with maker() as db_session:
        db_session.add(
            User(
                id=admin_id,
                email="selfadmin@example.com",
                is_admin=True,
                is_invited=True,
                scanning_enabled=True,
            )
        )
        await db_session.commit()

    app.dependency_overrides[resolve_current_user] = lambda: admin_user
    try:
        resp = test_client.patch(
            f"/api/admin/users/{admin_id}",
            json={"is_admin": False},
        )
        assert resp.status_code == 400
        assert (
            "cannot remove your own administrator privileges"
            in resp.json()["detail"].lower()
        )
    finally:
        app.dependency_overrides.pop(resolve_current_user, None)


@pytest.mark.parametrize("force_change", [True, False])
def test_password_reset_revokes_existing_sessions(
    session_mode: None, test_client: TestClient, force_change: bool
) -> None:
    """A reset revokes old cookies permanently, including after forced rotation."""
    _login(test_client, username="test-admin", password="synthetic-test-password")
    email = f"reset_sessions_{uuid.uuid4().hex}@example.com"
    created = test_client.post(
        "/api/admin/users", json={"email": email, "password": "InitialPassword123!"}
    )
    assert created.status_code == 201
    old_client = TestClient(app)
    _login(old_client, username=email, password="InitialPassword123!")

    reset = test_client.patch(
        f"/api/admin/users/{created.json()['id']}",
        json={
            "password": "TemporaryPassword456!",
            "must_change_password": force_change,
        },
    )
    assert reset.status_code == 200
    assert test_client.get("/api/admin/users").status_code == 200
    assert old_client.get("/api/me").status_code == 401
    assert old_client.get("/api/scans").status_code == 401

    new_client = TestClient(app)
    _login(new_client, username=email, password="TemporaryPassword456!")
    changed = new_client.post(
        "/api/change-password",
        json={
            "current_password": "TemporaryPassword456!",
            "new_password": "FinalPassword789!",
        },
    )
    assert changed.status_code == 200
    assert new_client.get("/api/scans").status_code == 200
    assert old_client.get("/api/scans").status_code == 401


@pytest.mark.parametrize("new_password", ["InitialPassword123!", "NewPassword456!"])
def test_password_change_revokes_other_sessions(
    session_mode: None, test_client: TestClient, new_password: str
) -> None:
    """Changing even to the same password revokes other cookies and refreshes this browser."""
    _login(test_client, username="test-admin", password="synthetic-test-password")
    email = f"change_sessions_{uuid.uuid4().hex}@example.com"
    created = test_client.post(
        "/api/admin/users", json={"email": email, "password": "InitialPassword123!"}
    )
    assert created.status_code == 201
    old_client = TestClient(app)
    _login(old_client, username=email, password="InitialPassword123!")
    _login(test_client, username=email, password="InitialPassword123!")
    previous_cookie = test_client.cookies["camply_session"]

    changed = test_client.post(
        "/api/change-password",
        json={"current_password": "InitialPassword123!", "new_password": new_password},
    )
    assert changed.status_code == 200
    assert test_client.cookies["camply_session"] != previous_cookie
    assert test_client.get("/api/scans").status_code == 200
    assert (
        test_client.patch(
            "/api/me", json={"pushover_token": "synthetic-token"}
        ).status_code
        == 200
    )
    assert old_client.get("/api/me").status_code == 401


@pytest.mark.parametrize("operation", ["reset", "change"])
@pytest.mark.parametrize("login_by_email", [True, False])
def test_bootstrap_password_rotation_replaces_configured_password(
    session_mode: None, test_client: TestClient, operation: str, login_by_email: bool
) -> None:
    """Bootstrap password rotations replace configured credentials and retain the username alias."""
    _login(test_client, username="test-admin", password="synthetic-test-password")
    old_client = TestClient(app)
    _login(old_client, username="test-admin", password="synthetic-test-password")
    user_id = test_client.get("/api/me").json()["id"]

    if operation == "reset":
        rotated = test_client.patch(
            f"/api/admin/users/{user_id}", json={"password": "RotatedPassword123!"}
        )
    else:
        rotated = test_client.post(
            "/api/change-password",
            json={
                "current_password": "synthetic-test-password",
                "new_password": "RotatedPassword123!",
            },
        )
    assert rotated.status_code == 200
    assert old_client.get("/api/me").status_code == 401
    rejected = old_client.post(
        "/api/login",
        json={"username": "test-admin", "password": "synthetic-test-password"},
    )
    assert rejected.status_code == 401

    username = backend_config.admin_email if login_by_email else "test-admin"
    _login(test_client, username=username, password="RotatedPassword123!")
    if operation == "reset":
        changed = test_client.post(
            "/api/change-password",
            json={
                "current_password": "RotatedPassword123!",
                "new_password": "PermanentPassword456!",
            },
        )
        assert changed.status_code == 200
    assert test_client.get("/api/admin/users").status_code == 200
    assert old_client.get("/api/me").status_code == 401
    assert (
        old_client.post(
            "/api/login",
            json={"username": "test-admin", "password": "synthetic-test-password"},
        ).status_code
        == 401
    )


def test_bootstrap_demotion_persists_across_requests_and_login(
    session_mode: None, test_client: TestClient
) -> None:
    """Another admin can demote the bootstrap account without its resolver restoring privileges."""
    _login(test_client, username="test-admin", password="synthetic-test-password")
    bootstrap_id = test_client.get("/api/me").json()["id"]
    email = f"other_admin_{uuid.uuid4().hex}@example.com"
    created = test_client.post(
        "/api/admin/users",
        json={"email": email, "password": "AdminPassword123!", "is_admin": True},
    )
    assert created.status_code == 201
    other_admin = TestClient(app)
    _login(other_admin, username=email, password="AdminPassword123!")
    demoted = other_admin.patch(
        f"/api/admin/users/{bootstrap_id}", json={"is_admin": False}
    )
    assert demoted.status_code == 200
    assert test_client.get("/api/me").json()["is_admin"] is False
    assert test_client.get("/api/admin/users").status_code == 403
    _login(test_client, username="test-admin", password="synthetic-test-password")
    assert test_client.get("/api/me").json()["is_admin"] is False
    assert test_client.get("/api/admin/users").status_code == 403


@pytest.mark.parametrize("auth_mode", [AuthMode.NONE, AuthMode.AUTH0])
@pytest.mark.parametrize("force_change", [True, False])
def test_password_change_flag_rejected_outside_session_mode(
    session_mode: None,
    test_client: TestClient,
    override_admin_user: CurrentUser,
    monkeypatch: pytest.MonkeyPatch,
    auth_mode: AuthMode,
    force_change: bool,
) -> None:
    """Neither setting nor clearing password flags is allowed for other authentication modes."""
    created = test_client.post(
        "/api/admin/users",
        json={
            "email": f"mode_{uuid.uuid4().hex}@example.com",
            "password": "Password123!",
        },
    )
    assert created.status_code == 201
    monkeypatch.setattr(backend_config, "auth_mode", auth_mode)
    rejected = test_client.patch(
        f"/api/admin/users/{created.json()['id']}",
        json={"must_change_password": force_change, "scanning_enabled": False},
    )
    assert rejected.status_code == 400
    detail = test_client.get(f"/api/admin/users/{created.json()['id']}").json()
    assert detail["must_change_password"] is False
    assert detail["scanning_enabled"] is True


def test_automatic_login_ignores_session_password_change_flag(
    session_mode: None, test_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Switching to automatic login does not require an unavailable password-change flow."""
    _login(test_client, username="test-admin", password="synthetic-test-password")
    user_id = test_client.get("/api/me").json()["id"]
    assert (
        test_client.patch(
            f"/api/admin/users/{user_id}", json={"must_change_password": True}
        ).status_code
        == 200
    )
    monkeypatch.setattr(backend_config, "auth_mode", AuthMode.NONE)
    assert test_client.get("/api/me").json()["must_change_password"] is False
    assert test_client.get("/api/admin/users").status_code == 200


@pytest.mark.parametrize("credential_version", [None, "outdated"])
def test_session_rejects_missing_or_invalid_credential_version(
    session_mode: None, test_client: TestClient, credential_version: str | None
) -> None:
    """Legacy or outdated signed cookies require a fresh login."""
    _login(test_client, username="test-admin", password="synthetic-test-password")
    payload = jwt.decode(
        test_client.cookies["camply_session"],
        session_signing_key(),
        algorithms=["HS256"],
    )
    if credential_version is None:
        payload.pop("credentials")
    else:
        payload["credentials"] = credential_version
    test_client.cookies.clear()
    test_client.cookies.set(
        "camply_session", jwt.encode(payload, session_signing_key(), algorithm="HS256")
    )
    assert test_client.get("/api/me").status_code == 401


@pytest.mark.asyncio
async def test_auth0_ignores_session_password_change_flag(
    test_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Auth0 profiles do not trigger a session-only password-change screen."""
    auth0_id = f"auth0|{uuid.uuid4().hex}"
    async with maker() as session:
        session.add(
            User(
                email=f"auth0_{uuid.uuid4().hex}@example.com",
                auth0_id=auth0_id,
                must_change_password=True,
            )
        )
        await session.commit()

    async def verify_token(token: str) -> dict[str, str]:
        """Supply synthetic verified claims without an external identity provider."""
        return {"sub": auth0_id}

    monkeypatch.setattr(backend_config, "auth_mode", AuthMode.AUTH0)
    monkeypatch.setattr("backend.auth._verify_auth0_token", verify_token)
    response = test_client.get(
        "/api/me", headers={"Authorization": "Bearer synthetic-token"}
    )
    assert response.status_code == 200
    assert response.json()["must_change_password"] is False
