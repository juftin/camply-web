"""Regression tests for owner-selected cookie sessions and automatic login."""

import asyncio
import datetime
import uuid
from collections.abc import Iterator
from unittest.mock import patch

import jwt
import pytest
from fastapi.testclient import TestClient
from httpx2 import URL
from sqlalchemy import select

from camply.db.models import User, UserSession
from camply.server.app import app
from camply.server.auth import hash_password, session_signing_key
from camply.server.config import AuthMode, BackendConfig, backend_config
from tests.server.conftest import maker


@pytest.fixture
def session_mode(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Configure synthetic shared credentials and an HTTP test session."""
    monkeypatch.setattr(backend_config, "auth_mode", AuthMode.SESSION)
    monkeypatch.setattr(backend_config, "login_username", "test-admin")
    monkeypatch.setattr(backend_config, "login_password", "synthetic-test-password")
    monkeypatch.setattr(
        backend_config, "session_secret", "synthetic-session-secret-with-32-characters"
    )
    monkeypatch.setattr(backend_config, "session_cookie_secure", False)
    yield


def _login(client: TestClient) -> None:
    """Sign in through JSON credentials and set the session's CSRF header."""
    response = client.post(
        "/api/login",
        json={"username": "test-admin", "password": "synthetic-test-password"},
    )
    assert response.status_code == 200
    client.headers["X-CSRF-Token"] = client.cookies["camply_csrf"]


def test_session_login_logout(session_mode: None, test_client: TestClient) -> None:
    """The in-app login persists across requests and logout clears both cookies."""
    assert test_client.get("/api/me").status_code == 401
    _login(test_client)
    assert test_client.get("/api/me").status_code == 200
    response = test_client.post("/api/logout")
    assert response.status_code == 204
    assert test_client.get("/api/me").status_code == 401


@pytest.mark.parametrize("origin", ["https://localhost", "capacitor://localhost"])
def test_native_password_session_can_rotate_and_revoke(
    session_mode: None,
    test_client: TestClient,
    origin: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Native password sessions use bearer credentials through rotation and revocation."""
    monkeypatch.setattr(
        backend_config, "admin_email", f"native-{uuid.uuid4().hex}@example.com"
    )
    credentials = {"username": "test-admin", "password": "synthetic-test-password"}
    preflight = test_client.options(
        "/api/login",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type,x-camply-session-transport",
        },
    )
    assert preflight.status_code == 200
    assert preflight.headers["Access-Control-Allow-Origin"] == origin
    response = test_client.post(
        "/api/login",
        headers={"Origin": origin, "X-Camply-Session-Transport": "bearer"},
        json=credentials,
    )
    assert response.status_code == 200
    assert response.headers["Cache-Control"] == "no-store"
    assert (
        "x-camply-session-token"
        in response.headers["Access-Control-Expose-Headers"].lower()
    )
    assert "set-cookie" not in response.headers
    token = response.headers["X-Camply-Session-Token"]
    bearer = {"Authorization": f"Bearer {token}"}

    assert test_client.get("/api/me", headers=bearer).status_code == 200
    assert len(test_client.get("/api/me/sessions", headers=bearer).json()["items"]) == 1
    test_client.cookies.set("camply_session", token)
    assert test_client.get("/api/me").status_code == 401
    test_client.cookies.clear()

    rotation = test_client.post(
        "/api/change-password",
        headers=bearer,
        json={
            "current_password": credentials["password"],
            "new_password": "Synthetic-Rotated-Password123",
        },
    )
    assert rotation.status_code == 200
    assert "set-cookie" not in rotation.headers
    new_token = rotation.headers["X-Camply-Session-Token"]
    assert test_client.get("/api/me", headers=bearer).status_code == 401

    new_bearer = {"Authorization": f"Bearer {new_token}"}
    assert test_client.get("/api/me", headers=new_bearer).status_code == 200
    assert test_client.post("/api/logout", headers=new_bearer).status_code == 204
    assert test_client.get("/api/me", headers=new_bearer).status_code == 401


def test_browser_cookie_is_rejected_as_bearer(
    session_mode: None, test_client: TestClient
) -> None:
    """A web session cookie cannot be presented as a bearer to skip its CSRF proof."""
    _login(test_client)
    token = test_client.cookies["camply_session"]
    test_client.cookies.clear()
    assert (
        test_client.post(
            "/api/logout", headers={"Authorization": f"Bearer {token}"}
        ).status_code
        == 401
    )


def test_web_origin_cannot_request_native_token(
    session_mode: None, test_client: TestClient
) -> None:
    """Ordinary web origins never receive the native response token."""
    response = test_client.post(
        "/api/login",
        headers={
            "Origin": "https://camply.rocks",
            "X-Camply-Session-Transport": "bearer",
        },
        json={"username": "test-admin", "password": "synthetic-test-password"},
    )
    assert response.status_code == 403
    assert "x-camply-session-token" not in response.headers


@pytest.mark.parametrize("scheme", ["http", "https"])
def test_session_scan_requests(
    session_mode: None,
    test_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    scheme: str,
) -> None:
    """Login cookies authenticate scan operations over HTTP and secure HTTPS."""
    test_client.base_url = URL(f"{scheme}://testserver")
    monkeypatch.setattr(backend_config, "session_cookie_secure", scheme == "https")
    assert test_client.get("/api/scans").status_code == 401
    _login(test_client)
    response = test_client.post(
        "/api/scans",
        json={
            "provider_id": 1,
            "campground_id": "cg_1",
            "start_date": "2027-07-01",
            "end_date": "2027-07-05",
        },
    )
    assert response.status_code == 201
    scan_id = response.json()["id"]
    assert test_client.get("/api/scans").status_code == 200
    assert test_client.get(f"/api/scans/{scan_id}").status_code == 200
    assert (
        test_client.patch(
            f"/api/scans/{scan_id}", json={"is_active": False}
        ).status_code
        == 200
    )
    assert test_client.delete(f"/api/scans/{scan_id}").status_code == 204
    assert test_client.post("/api/logout").status_code == 204
    assert test_client.get("/api/scans").status_code == 401


def test_session_rejects_invalid_credentials(
    session_mode: None, test_client: TestClient
) -> None:
    """Invalid credentials return an app error with no Basic challenge or cookie."""
    response = test_client.post(
        "/api/login", json={"username": "test-admin", "password": "wrong"}
    )
    assert response.status_code == 401
    assert "www-authenticate" not in response.headers
    assert "camply_session" not in test_client.cookies


def test_session_cookie_flags(
    session_mode: None, test_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The session cookie is HTTP-only, same-site, bounded, and secure when configured."""
    monkeypatch.setattr(backend_config, "session_cookie_secure", True)
    response = test_client.post(
        "/api/login",
        json={"username": "test-admin", "password": "synthetic-test-password"},
    )
    cookie = response.headers.get_list("set-cookie")[0].lower()
    assert "httponly" in cookie
    assert "samesite=strict" in cookie
    assert "secure" in cookie
    assert "max-age=" in cookie


def test_session_requires_csrf_for_mutations(
    session_mode: None, test_client: TestClient
) -> None:
    """Cookie-authenticated mutations require the CSRF token from the signed session."""
    _login(test_client)
    del test_client.headers["X-CSRF-Token"]
    assert (
        test_client.patch(
            "/api/me", json={"pushover_token": "synthetic-key"}
        ).status_code
        == 403
    )
    assert (
        test_client.post(
            "/api/me/notifications/test", json={"notification_provider": "ntfy"}
        ).status_code
        == 403
    )
    test_client.headers["X-CSRF-Token"] = "wrong-token"
    assert test_client.post("/api/logout").status_code == 403
    assert (
        test_client.post(
            "/api/me/notifications/test", json={"notification_provider": "ntfy"}
        ).status_code
        == 403
    )
    test_client.headers["X-CSRF-Token"] = test_client.cookies["camply_csrf"]
    assert (
        test_client.patch(
            "/api/me", json={"pushover_token": "synthetic-key"}
        ).status_code
        == 200
    )


def test_session_tampering_and_expiry(
    session_mode: None, test_client: TestClient
) -> None:
    """Forged and expired session cookies cannot resolve a current user."""
    test_client.cookies.set("camply_session", "forged")
    assert test_client.get("/api/me").status_code == 401
    test_client.cookies.clear()
    with patch("camply.server.routers.sessions.time.time", return_value=1):
        _login(test_client)
    assert test_client.get("/api/me").status_code == 401


def test_session_invalidates_after_password_change(
    session_mode: None, test_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Changing the configured password invalidates existing signed sessions."""
    _login(test_client)
    monkeypatch.setattr(
        backend_config, "login_password", "replacement-synthetic-password"
    )
    assert test_client.get("/api/me").status_code == 401


@pytest.mark.parametrize(
    "origin",
    [
        "https://untrusted.example.com",
        "https://other-project.pages.dev",
        "https://da37cb45.other-project.pages.dev",
        "http://da37cb45.camply-81r.pages.dev",
        "https://da37cb45.camply-81r.pages.dev.evil.example",
        "https://da37cb45.evilcamply-81r.pages.dev",
        "https://nested.da37cb45.camply-81r.pages.dev",
    ],
)
def test_login_rejects_untrusted_origin(
    session_mode: None, test_client: TestClient, origin: str
) -> None:
    """A foreign website cannot start a password session in the browser."""
    response = test_client.post(
        "/api/login",
        headers={"Origin": origin},
        json={"username": "test-admin", "password": "synthetic-test-password"},
    )
    assert response.status_code == 403


@pytest.mark.parametrize(
    "origin",
    [
        "http://localhost:5173",
        "http://100.85.12.34:5173",
        "https://camply.ts.net",
        "https://camply-81r.pages.dev",
        "https://da37cb45.camply-81r.pages.dev",
        "https://feature-branch.camply-81r.pages.dev",
    ],
)
def test_login_accepts_cors_origins(
    session_mode: None, test_client: TestClient, origin: str
) -> None:
    """Password login accepts the same explicit and regex origins as CORS."""
    response = test_client.post(
        "/api/login",
        headers={"Origin": origin},
        json={"username": "test-admin", "password": "synthetic-test-password"},
    )
    assert response.status_code == 200


@pytest.mark.parametrize("environment", ["local", "production"])
def test_explicit_auto_login_ignores_environment(
    test_client: TestClient, monkeypatch: pytest.MonkeyPatch, environment: str
) -> None:
    """The selected auth mode, rather than environment, controls automatic login."""
    monkeypatch.setattr(backend_config, "environment", environment)
    monkeypatch.setattr(backend_config, "auth_mode", AuthMode.NONE)
    assert test_client.get("/api/me").status_code == 200


def test_auth0_in_local_environment_still_requires_login(
    test_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Choosing Auth0 is honored even while running in a local environment."""
    monkeypatch.setattr(backend_config, "environment", "local")
    monkeypatch.setattr(backend_config, "auth_mode", AuthMode.AUTH0)
    assert test_client.get("/api/me").status_code == 401


@pytest.mark.parametrize(
    "missing", ["login_username", "login_password", "session_secret"]
)
def test_session_requires_complete_configuration(missing: str) -> None:
    """Session mode cannot start with missing shared credentials or signing keys."""
    from pydantic import ValidationError

    values = {
        "auth_mode": "session",
        "login_username": "test-admin",
        "login_password": "synthetic-password",
        "session_secret": "synthetic-secret-with-at-least-32-characters",
        missing: None,
    }
    with pytest.raises(ValidationError):
        BackendConfig.model_validate(values)


def test_password_login_disabled_in_other_modes(test_client: TestClient) -> None:
    """Automatic login does not expose an unused password-login flow."""
    response = test_client.post(
        "/api/login", json={"username": "test-admin", "password": "synthetic-password"}
    )
    assert response.status_code == 404


def test_admin_session_suspension_and_csrf(
    session_mode: None, test_client: TestClient
) -> None:
    """Admin sessions retain privileges and enforce CSRF during suspension."""
    assert test_client.get("/api/admin/users").status_code == 401
    _login(test_client)
    profile = test_client.get("/api/me").json()
    assert profile["is_admin"] is True
    assert profile["scanning_enabled"] is True
    assert test_client.get("/api/admin/users").status_code == 200
    endpoint = f"/api/admin/users/{profile['id']}"
    del test_client.headers["X-CSRF-Token"]
    assert (
        test_client.patch(endpoint, json={"scanning_enabled": False}).status_code == 403
    )
    test_client.headers["X-CSRF-Token"] = test_client.cookies["camply_csrf"]
    assert (
        test_client.patch(endpoint, json={"scanning_enabled": False}).status_code == 200
    )
    suspended_profile = test_client.get("/api/me").json()
    assert suspended_profile["is_admin"] is True
    assert suspended_profile["scanning_enabled"] is False
    assert test_client.get("/api/admin/users").status_code == 200
    assert (
        test_client.post(
            "/api/scans",
            json={
                "provider_id": 1,
                "campground_id": "cg_1",
                "start_date": "2027-07-01",
                "end_date": "2027-07-05",
            },
        ).status_code
        == 403
    )
    assert (
        test_client.patch(endpoint, json={"scanning_enabled": True}).status_code == 200
    )


def _decode_session_jti(client: TestClient) -> uuid.UUID:
    """Decode the active session cookie and return its ``jti`` UUID."""
    payload = jwt.decode(
        client.cookies["camply_session"],
        session_signing_key(),
        algorithms=["HS256"],
    )
    return uuid.UUID(payload["jti"])


def _create_user_with_password(
    email: str, password: str, *, must_change_password: bool = False
) -> uuid.UUID:
    """Insert a password-authenticated user for session isolation tests."""

    async def _seed() -> uuid.UUID:
        async with maker() as db_session:
            user = User(
                email=email,
                password_hash=hash_password(password),
                is_invited=True,
                is_admin=False,
                scanning_enabled=True,
                must_change_password=must_change_password,
            )
            db_session.add(user)
            await db_session.commit()
            return user.id

    return asyncio.run(_seed())


def test_logout_invalidates_captured_session_cookie_replay(
    session_mode: None, test_client: TestClient
) -> None:
    """Replaying a captured session cookie after logout returns 401."""
    _login(test_client)
    captured_cookie = test_client.cookies["camply_session"]
    jti = _decode_session_jti(test_client)

    me_resp = test_client.get("/api/me")
    assert me_resp.status_code == 200
    assert "session_id" not in me_resp.json()

    logout_resp = test_client.post("/api/logout")
    assert logout_resp.status_code == 204
    assert "camply_session" not in test_client.cookies

    replay_client = TestClient(app)
    replay_client.cookies.set("camply_session", captured_cookie)
    assert replay_client.get("/api/me").status_code == 401

    async def _check_revoked() -> None:
        async with maker() as db_session:
            row = await db_session.get(UserSession, jti)
            assert row is not None
            assert row.revoked_at is not None

    asyncio.run(_check_revoked())


def test_multi_session_listing_and_individual_revocation(
    session_mode: None,
) -> None:
    """Multiple logins issue distinct jti sessions that can be revoked independently."""
    email = f"multisess_{uuid.uuid4().hex}@example.test"
    password = "SyntheticPassword123!"
    _create_user_with_password(email, password)

    client_a = TestClient(app)
    client_b = TestClient(app)

    long_ua = "BrowserA/" + ("x" * 600)
    resp_a = client_a.post(
        "/api/login",
        headers={"User-Agent": long_ua, "X-Forwarded-For": "203.0.113.10, 10.0.0.1"},
        json={"username": email, "password": password},
    )
    assert resp_a.status_code == 200
    client_a.headers["X-CSRF-Token"] = client_a.cookies["camply_csrf"]

    resp_b = client_b.post(
        "/api/login",
        headers={"User-Agent": "BrowserB/2.0", "X-Forwarded-For": "198.51.100.42"},
        json={"username": email, "password": password},
    )
    assert resp_b.status_code == 200
    client_b.headers["X-CSRF-Token"] = client_b.cookies["camply_csrf"]

    jti_a = _decode_session_jti(client_a)
    jti_b = _decode_session_jti(client_b)
    assert jti_a != jti_b

    list_resp = client_b.get("/api/me/sessions")
    assert list_resp.status_code == 200
    items = list_resp.json()["items"]
    by_id = {item["id"]: item for item in items}
    assert str(jti_a) in by_id
    assert str(jti_b) in by_id
    assert by_id[str(jti_b)]["is_current"] is True
    assert by_id[str(jti_a)]["is_current"] is False
    assert by_id[str(jti_a)]["user_agent"] == long_ua[:512]
    assert by_id[str(jti_a)]["ip_address"] == "203.0.113.10"
    assert by_id[str(jti_b)]["user_agent"] == "BrowserB/2.0"
    assert by_id[str(jti_b)]["ip_address"] == "198.51.100.42"
    assert by_id[str(jti_b)]["created_at"].endswith("Z")
    assert by_id[str(jti_b)]["expires_at"].endswith("Z")

    # CSRF is enforced on DELETE /api/me/sessions/{id}.
    saved_csrf = client_b.headers.pop("X-CSRF-Token")
    assert client_b.delete(f"/api/me/sessions/{jti_a}").status_code == 403
    client_b.headers["X-CSRF-Token"] = saved_csrf

    # Revoke session A from session B.
    revoke_a = client_b.delete(f"/api/me/sessions/{jti_a}")
    assert revoke_a.status_code == 204
    assert client_a.get("/api/me").status_code == 401
    assert client_b.get("/api/me").status_code == 200

    # Revoked session is hidden from active session list.
    remaining_ids = {
        item["id"] for item in client_b.get("/api/me/sessions").json()["items"]
    }
    assert str(jti_a) not in remaining_ids
    assert str(jti_b) in remaining_ids

    # Revoking the current session clears cookies and invalidates the captured cookie.
    captured_b = client_b.cookies["camply_session"]
    revoke_b = client_b.delete(f"/api/me/sessions/{jti_b}")
    assert revoke_b.status_code == 204
    assert "camply_session" not in client_b.cookies
    assert "camply_csrf" not in client_b.cookies
    replay_b = TestClient(app)
    replay_b.cookies.set("camply_session", captured_b)
    assert replay_b.get("/api/me").status_code == 401


def test_session_cross_user_isolation(session_mode: None) -> None:
    """Users cannot view or revoke another user's sessions."""
    user_a_email = f"usera_{uuid.uuid4().hex}@example.test"
    user_b_email = f"userb_{uuid.uuid4().hex}@example.test"
    password = "SyntheticPassword123!"
    _create_user_with_password(user_a_email, password)
    _create_user_with_password(user_b_email, password)

    client_a = TestClient(app)
    client_b = TestClient(app)

    assert (
        client_a.post(
            "/api/login", json={"username": user_a_email, "password": password}
        ).status_code
        == 200
    )
    client_a.headers["X-CSRF-Token"] = client_a.cookies["camply_csrf"]

    assert (
        client_b.post(
            "/api/login", json={"username": user_b_email, "password": password}
        ).status_code
        == 200
    )
    client_b.headers["X-CSRF-Token"] = client_b.cookies["camply_csrf"]

    jti_b = _decode_session_jti(client_b)

    sessions_a = client_a.get("/api/me/sessions").json()["items"]
    assert all(item["id"] != str(jti_b) for item in sessions_a)

    # User A attempting to revoke User B's session gets 404; User B remains valid.
    assert client_a.delete(f"/api/me/sessions/{jti_b}").status_code == 404
    assert client_a.delete(f"/api/me/sessions/{uuid.uuid4()}").status_code == 404
    assert client_b.get("/api/me").status_code == 200


@pytest.mark.parametrize("jti_mode", ["missing", "malformed", "unknown"])
def test_session_rejects_missing_malformed_or_unknown_jti(
    session_mode: None, test_client: TestClient, jti_mode: str
) -> None:
    """Signed cookies lacking a valid server-side session ``jti`` are rejected with 401."""
    _login(test_client)
    payload = jwt.decode(
        test_client.cookies["camply_session"],
        session_signing_key(),
        algorithms=["HS256"],
    )
    if jti_mode == "missing":
        payload.pop("jti")
    elif jti_mode == "malformed":
        payload["jti"] = "not-a-uuid"
    else:
        payload["jti"] = str(uuid.uuid4())

    test_client.cookies.clear()
    test_client.cookies.set(
        "camply_session",
        jwt.encode(payload, session_signing_key(), algorithm="HS256"),
    )
    assert test_client.get("/api/me").status_code == 401


def test_session_rejects_expired_database_session(
    session_mode: None, test_client: TestClient
) -> None:
    """A session expired in the database is rejected and hidden even if JWT exp is valid."""
    email = f"dbexp_{uuid.uuid4().hex}@example.test"
    password = "SyntheticPassword123!"
    _create_user_with_password(email, password)

    client_1 = TestClient(app)
    client_2 = TestClient(app)
    assert (
        client_1.post(
            "/api/login", json={"username": email, "password": password}
        ).status_code
        == 200
    )
    assert (
        client_2.post(
            "/api/login", json={"username": email, "password": password}
        ).status_code
        == 200
    )
    jti_1 = _decode_session_jti(client_1)
    jti_2 = _decode_session_jti(client_2)

    async def _expire_session() -> None:
        async with maker() as db_session:
            row = await db_session.get(UserSession, jti_1)
            assert row is not None
            row.expires_at = datetime.datetime.now(
                tz=datetime.timezone.utc
            ) - datetime.timedelta(minutes=1)
            await db_session.commit()

    asyncio.run(_expire_session())

    assert client_1.get("/api/me").status_code == 401
    listed = client_2.get("/api/me/sessions").json()["items"]
    listed_ids = {item["id"] for item in listed}
    assert str(jti_1) not in listed_ids
    assert str(jti_2) in listed_ids


def test_login_prunes_old_expired_sessions_for_user(session_mode: None) -> None:
    """Logging in prunes expired sessions older than 7 days for that user only."""
    email = f"prune_{uuid.uuid4().hex}@example.test"
    other_email = f"prune_other_{uuid.uuid4().hex}@example.test"
    password = "SyntheticPassword123!"
    user_id = _create_user_with_password(email, password)
    other_id = _create_user_with_password(other_email, password)

    now = datetime.datetime.now(tz=datetime.timezone.utc)
    stale_id = uuid.uuid4()
    recent_expired_id = uuid.uuid4()
    other_stale_id = uuid.uuid4()

    async def _seed_sessions() -> None:
        async with maker() as db_session:
            db_session.add_all(
                [
                    UserSession(
                        id=stale_id,
                        user_id=user_id,
                        expires_at=now - datetime.timedelta(days=8),
                    ),
                    UserSession(
                        id=recent_expired_id,
                        user_id=user_id,
                        expires_at=now - datetime.timedelta(days=2),
                    ),
                    UserSession(
                        id=other_stale_id,
                        user_id=other_id,
                        expires_at=now - datetime.timedelta(days=10),
                    ),
                ]
            )
            await db_session.commit()

    asyncio.run(_seed_sessions())

    client = TestClient(app)
    assert (
        client.post(
            "/api/login", json={"username": email, "password": password}
        ).status_code
        == 200
    )

    async def _verify_pruned() -> None:
        async with maker() as db_session:
            assert await db_session.get(UserSession, stale_id) is None
            assert await db_session.get(UserSession, recent_expired_id) is not None
            assert await db_session.get(UserSession, other_stale_id) is not None
            active = (
                (
                    await db_session.execute(
                        select(UserSession).where(
                            UserSession.user_id == user_id,
                            UserSession.revoked_at.is_(None),
                            UserSession.expires_at > now,
                        )
                    )
                )
                .scalars()
                .all()
            )
            assert len(active) == 1

    asyncio.run(_verify_pruned())


@pytest.mark.parametrize("auth_mode", [AuthMode.NONE, AuthMode.AUTH0])
def test_session_management_endpoints_disabled_outside_session_mode(
    test_client: TestClient, monkeypatch: pytest.MonkeyPatch, auth_mode: AuthMode
) -> None:
    """Session listing and revocation endpoints return 404 outside session auth mode."""
    monkeypatch.setattr(backend_config, "auth_mode", auth_mode)
    assert test_client.get("/api/me/sessions").status_code == 404
    assert test_client.delete(f"/api/me/sessions/{uuid.uuid4()}").status_code == 404
