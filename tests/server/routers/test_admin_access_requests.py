"""
Tests for the admin invitation request review API and user invitation toggle.
"""

from __future__ import annotations

import asyncio
import uuid
from typing import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from camply.db.models import AccessRequest, AdminAuditEvent, User
from camply.server.app import app
from camply.server.auth import CurrentUser, resolve_current_user
from camply.server.config import backend_config
from tests.server.conftest import maker


def _tag() -> str:
    """Return a short unique token so tests sharing one database stay isolated."""
    return uuid.uuid4().hex[:10]


async def _add_user(*, email: str, is_admin: bool = False, is_invited: bool) -> User:
    """Persist and return a synthetic user.

    Parameters
    ----------
    email : str
        Email address of the new user.
    is_admin : bool
        Whether the user is an administrator.
    is_invited : bool
        Initial invitation state.

    Returns
    -------
    User
        The stored user.
    """
    async with maker() as session:
        user = User(email=email, is_admin=is_admin, is_invited=is_invited)
        session.add(user)
        await session.commit()
        return user


async def _add_request(
    *, email: str, status: str = "pending", name: str | None = None
) -> AccessRequest:
    """Persist and return a synthetic access request.

    Parameters
    ----------
    email : str
        Requester email address (normalized by the model).
    status : str
        Initial review status.
    name : str | None
        Optional requester name.

    Returns
    -------
    AccessRequest
        The stored request.
    """
    async with maker() as session:
        access_request = AccessRequest(email=email, status=status, name=name)
        session.add(access_request)
        await session.commit()
        return access_request


async def _audit_actions(subject_id: uuid.UUID) -> list[AdminAuditEvent]:
    """Return audit events for a subject, oldest first.

    Parameters
    ----------
    subject_id : uuid.UUID
        Identifier of the audited user or access request.

    Returns
    -------
    list[AdminAuditEvent]
        Matching events ordered by creation time.
    """
    async with maker() as session:
        result = await session.execute(
            select(AdminAuditEvent)
            .where(AdminAuditEvent.subject_id == subject_id)
            .order_by(AdminAuditEvent.created_at, AdminAuditEvent.action)
        )
        return list(result.scalars().all())


async def _load_user(user_id: uuid.UUID) -> User:
    """Reload a user from the database.

    Parameters
    ----------
    user_id : uuid.UUID
        Identifier of the user.

    Returns
    -------
    User
        The freshly loaded user.
    """
    async with maker() as session:
        return (
            await session.execute(select(User).where(User.id == user_id))
        ).scalar_one()


@pytest.fixture
def admin(test_client: TestClient) -> Generator[User, None, None]:
    """Act as a stored administrator for the duration of a test.

    Parameters
    ----------
    test_client : TestClient
        Ensures the application and database are configured.

    Yields
    ------
    User
        The stored administrator account used as the current user.
    """
    user = asyncio.run(
        _add_user(email=f"admin-{_tag()}@example.test", is_admin=True, is_invited=True)
    )
    current = CurrentUser(
        id=user.id,
        email=user.email,
        is_invited=True,
        is_admin=True,
        scanning_enabled=True,
    )
    app.dependency_overrides[resolve_current_user] = lambda: current
    yield user
    app.dependency_overrides.pop(resolve_current_user, None)


class TestAccessRequestAuthorization:
    """Access request administration is restricted to administrators."""

    def test_non_admin_forbidden(self, test_client: TestClient) -> None:
        """Non-admin callers receive 403 on both access request endpoints."""
        current = CurrentUser(
            id=uuid.uuid4(),
            email="regular@example.test",
            is_invited=True,
            is_admin=False,
            scanning_enabled=True,
        )
        app.dependency_overrides[resolve_current_user] = lambda: current
        try:
            listing = test_client.get("/api/admin/access-requests")
            update = test_client.patch(
                f"/api/admin/access-requests/{uuid.uuid4()}",
                json={"status": "approved"},
            )
        finally:
            app.dependency_overrides.pop(resolve_current_user, None)
        for response in (listing, update):
            assert response.status_code == 403
            assert response.json()["detail"]["error"] == "ERR_ADMIN_REQUIRED"


class TestListAccessRequests:
    """GET /api/admin/access-requests pagination and filters."""

    @pytest.mark.asyncio
    async def test_filters_and_pagination(
        self, test_client: TestClient, admin: User
    ) -> None:
        """Status and search filters narrow results and pages cover every match."""
        tag = _tag()
        await _add_request(email=f"a-{tag}@example.test", name="Ada Lovelace")
        await _add_request(email=f"b-{tag}@example.test", status="approved")
        await _add_request(email=f"C-{tag}@Example.test", status="rejected")

        everything = test_client.get(f"/api/admin/access-requests?search={tag}").json()
        assert everything["total"] == 3
        assert {row["email"] for row in everything["access_requests"]} == {
            f"a-{tag}@example.test",
            f"b-{tag}@example.test",
            f"c-{tag}@example.test",
        }

        approved = test_client.get(
            f"/api/admin/access-requests?search={tag}&status=approved"
        ).json()
        assert [row["email"] for row in approved["access_requests"]] == [
            f"b-{tag}@example.test"
        ]
        assert approved["total"] == 1

        by_name = test_client.get("/api/admin/access-requests?search=lovelace").json()
        assert f"a-{tag}@example.test" in {
            row["email"] for row in by_name["access_requests"]
        }
        assert by_name["access_requests"][0]["name"] == "Ada Lovelace"

        first = test_client.get(
            f"/api/admin/access-requests?search={tag}&limit=2&offset=0"
        ).json()
        second = test_client.get(
            f"/api/admin/access-requests?search={tag}&limit=2&offset=2"
        ).json()
        assert first["total"] == second["total"] == 3
        assert len(first["access_requests"]) == 2
        assert len(second["access_requests"]) == 1
        ids = [
            row["id"] for row in first["access_requests"] + second["access_requests"]
        ]
        assert len(set(ids)) == 3

    def test_rejects_unknown_status_filter(
        self, test_client: TestClient, admin: User
    ) -> None:
        """Unsupported status filters fail validation."""
        assert (
            test_client.get("/api/admin/access-requests?status=bogus").status_code
            == 422
        )

    @pytest.mark.asyncio
    async def test_public_request_preserves_name_and_normalizes_email(
        self, test_client: TestClient, admin: User
    ) -> None:
        """The public endpoint stores the requester name and a normalized email."""
        tag = _tag()
        response = test_client.post(
            "/api/request-access",
            json={"email": f"  Mixed-{tag}@Example.TEST ", "name": "Grace Hopper"},
        )
        assert response.status_code == 201
        rows = test_client.get(f"/api/admin/access-requests?search={tag}").json()
        assert rows["access_requests"][0]["email"] == f"mixed-{tag}@example.test"
        assert rows["access_requests"][0]["name"] == "Grace Hopper"
        assert rows["access_requests"][0]["status"] == "pending"
        assert rows["access_requests"][0]["reviewed_at"] is None


class TestReviewAccessRequest:
    """PATCH /api/admin/access-requests/{id} approval, rejection, and revocation."""

    @pytest.mark.asyncio
    async def test_approve_without_user(
        self, test_client: TestClient, admin: User
    ) -> None:
        """Approval records the reviewer and leaves the request unlinked."""
        access_request = await _add_request(email=f"nobody-{_tag()}@example.test")
        response = test_client.patch(
            f"/api/admin/access-requests/{access_request.id}",
            json={"status": "approved"},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "approved"
        assert body["reviewed_by_id"] == str(admin.id)
        assert body["reviewed_at"] is not None
        assert body["user_id"] is None
        events = await _audit_actions(access_request.id)
        assert [(e.action, e.prev_value, e.new_value) for e in events] == [
            ("access_request.approve", False, True)
        ]
        assert events[0].subject_type == "access_request"
        assert events[0].actor_id == admin.id

    @pytest.mark.asyncio
    async def test_approve_with_existing_user_is_idempotent(
        self, test_client: TestClient, admin: User
    ) -> None:
        """Approval invites the matching user once; repeating it changes nothing."""
        email = f"member-{_tag()}@example.test"
        user = await _add_user(email=email.upper(), is_invited=False)
        access_request = await _add_request(email=email)
        url = f"/api/admin/access-requests/{access_request.id}"

        first = test_client.patch(url, json={"status": "approved"})
        assert first.status_code == 200
        assert first.json()["user_id"] == str(user.id)
        assert (await _load_user(user.id)).is_invited is True
        reviewed_at = first.json()["reviewed_at"]

        second = test_client.patch(url, json={"status": "approved"})
        assert second.status_code == 200
        assert second.json()["reviewed_at"] == reviewed_at

        request_events = await _audit_actions(access_request.id)
        user_events = await _audit_actions(user.id)
        assert [e.action for e in request_events] == ["access_request.approve"]
        assert [(e.action, e.prev_value, e.new_value) for e in user_events] == [
            ("user.is_invited", False, True)
        ]

    @pytest.mark.asyncio
    async def test_reject_revokes_previously_approved_user(
        self, test_client: TestClient, admin: User
    ) -> None:
        """Rejecting an approved request clears the linked user's invitation."""
        email = f"revoked-{_tag()}@example.test"
        user = await _add_user(email=email, is_invited=False)
        access_request = await _add_request(email=email)
        url = f"/api/admin/access-requests/{access_request.id}"
        test_client.patch(url, json={"status": "approved"})

        response = test_client.patch(url, json={"status": "rejected"})
        assert response.status_code == 200
        assert response.json()["status"] == "rejected"
        assert response.json()["user_id"] == str(user.id)
        assert (await _load_user(user.id)).is_invited is False
        request_events = await _audit_actions(access_request.id)
        assert sorted(
            (e.action, e.prev_value, e.new_value) for e in request_events
        ) == [
            ("access_request.approve", False, True),
            ("access_request.reject", True, False),
        ]
        user_events = await _audit_actions(user.id)
        assert sorted((e.prev_value, e.new_value) for e in user_events) == [
            (False, True),
            (True, False),
        ]

    @pytest.mark.asyncio
    async def test_reject_pending_does_not_touch_user(
        self, test_client: TestClient, admin: User
    ) -> None:
        """Rejecting a never-approved request leaves an invited user invited."""
        email = f"keep-{_tag()}@example.test"
        user = await _add_user(email=email, is_invited=True)
        access_request = await _add_request(email=email)
        url = f"/api/admin/access-requests/{access_request.id}"
        response = test_client.patch(url, json={"status": "rejected"})
        assert response.status_code == 200
        reviewed_at = response.json()["reviewed_at"]
        assert (await _load_user(user.id)).is_invited is True
        assert await _audit_actions(user.id) == []

        repeat = test_client.patch(url, json={"status": "rejected"})
        assert repeat.status_code == 200
        assert repeat.json()["reviewed_at"] == reviewed_at
        assert [e.action for e in await _audit_actions(access_request.id)] == [
            "access_request.reject"
        ]

    @pytest.mark.asyncio
    async def test_reapprove_rejected_request_invites_user(
        self, test_client: TestClient, admin: User
    ) -> None:
        """Approving a previously rejected request links and invites the matching user."""
        email = f"reapprove-{_tag()}@example.test"
        user = await _add_user(email=email, is_invited=False)
        access_request = await _add_request(email=email, status="rejected")

        response = test_client.patch(
            f"/api/admin/access-requests/{access_request.id}",
            json={"status": "approved"},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "approved"
        assert body["user_id"] == str(user.id)
        assert (await _load_user(user.id)).is_invited is True
        assert [
            (e.action, e.prev_value, e.new_value)
            for e in await _audit_actions(access_request.id)
        ] == [("access_request.approve", False, True)]
        assert [
            (e.action, e.prev_value, e.new_value) for e in await _audit_actions(user.id)
        ] == [("user.is_invited", False, True)]

    def test_unknown_request_returns_404(
        self, test_client: TestClient, admin: User
    ) -> None:
        """Unknown identifiers produce 404."""
        response = test_client.patch(
            f"/api/admin/access-requests/{uuid.uuid4()}", json={"status": "approved"}
        )
        assert response.status_code == 404

    def test_pending_is_not_a_valid_target(
        self, test_client: TestClient, admin: User
    ) -> None:
        """Requests cannot be moved back to pending through review."""
        response = test_client.patch(
            f"/api/admin/access-requests/{uuid.uuid4()}", json={"status": "pending"}
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_bootstrap_admin_cannot_be_revoked(
        self, test_client: TestClient, admin: User, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Revoking the bootstrap administrator's approved request is refused."""
        email = f"owner-{_tag()}@example.test"
        monkeypatch.setattr(backend_config, "admin_email", email)
        owner = await _add_user(email=email, is_admin=True, is_invited=True)
        access_request = await _add_request(email=email, status="approved")
        response = test_client.patch(
            f"/api/admin/access-requests/{access_request.id}",
            json={"status": "rejected"},
        )
        assert response.status_code == 400
        assert (await _load_user(owner.id)).is_invited is True
        assert await _audit_actions(access_request.id) == []
        listing = test_client.get(f"/api/admin/access-requests?search={email}").json()
        assert listing["access_requests"][0]["status"] == "approved"

    @pytest.mark.asyncio
    async def test_acting_admin_cannot_revoke_own_access(
        self, test_client: TestClient, admin: User
    ) -> None:
        """An administrator cannot revoke their own invitation through a request."""
        access_request = await _add_request(email=admin.email, status="approved")
        response = test_client.patch(
            f"/api/admin/access-requests/{access_request.id}",
            json={"status": "rejected"},
        )
        assert response.status_code == 400
        assert (await _load_user(admin.id)).is_invited is True


class TestUserInvitationToggle:
    """PATCH /api/admin/users/{id} supports ``is_invited``."""

    @pytest.mark.asyncio
    async def test_toggle_is_audited(
        self, test_client: TestClient, admin: User
    ) -> None:
        """Changing ``is_invited`` updates the user and records audit events."""
        user = await _add_user(email=f"toggle-{_tag()}@example.test", is_invited=False)
        url = f"/api/admin/users/{user.id}"

        enabled = test_client.patch(url, json={"is_invited": True})
        assert enabled.status_code == 200
        assert enabled.json()["is_invited"] is True
        disabled = test_client.patch(url, json={"is_invited": False})
        assert disabled.json()["is_invited"] is False
        unchanged = test_client.patch(url, json={"is_invited": False})
        assert unchanged.status_code == 200

        events = await _audit_actions(user.id)
        assert sorted((e.action, e.prev_value, e.new_value) for e in events) == [
            ("user.is_invited", False, True),
            ("user.is_invited", True, False),
        ]
        assert all(e.actor_id == admin.id for e in events)

    @pytest.mark.asyncio
    async def test_cannot_uninvite_self_or_bootstrap_admin(
        self, test_client: TestClient, admin: User, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The acting and bootstrap administrators keep their invitation."""
        assert (
            test_client.patch(
                f"/api/admin/users/{admin.id}", json={"is_invited": False}
            ).status_code
            == 400
        )
        email = f"owner-{_tag()}@example.test"
        monkeypatch.setattr(backend_config, "admin_email", email)
        owner = await _add_user(email=email, is_admin=True, is_invited=True)
        response = test_client.patch(
            f"/api/admin/users/{owner.id}", json={"is_invited": False}
        )
        assert response.status_code == 400
        assert (await _load_user(owner.id)).is_invited is True
        assert await _audit_actions(owner.id) == []
