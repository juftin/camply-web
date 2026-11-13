"""Account creation recovers when a generated topic is already owned."""

import asyncio
import uuid
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from camply.db.models import AdminAuditEvent, User
from camply.server.config import AuthMode, backend_config
from camply.server.services.users import flush_new_user
from tests.server.conftest import maker


@pytest.mark.parametrize("mode", ["automatic", "auth0", "administrator"])
def test_account_creation_recovers_from_topic_collision(
    test_client: TestClient, monkeypatch: pytest.MonkeyPatch, mode: str
) -> None:
    """Every creation flow keeps IDs and existing topics when a prefix is taken."""
    new_id = uuid.uuid4()
    topic = f"camply-{str(new_id)[:7]}"
    owner_id = uuid.uuid4()
    email = f"new-{new_id.hex}@example.test"

    async def seed() -> None:
        """Claim the new account's default without relying on a random collision."""
        async with maker() as session:
            session.add(
                User(
                    id=owner_id,
                    email=f"owner-{owner_id.hex}@example.test",
                    ntfy_topic=topic,
                )
            )
            await session.commit()

    asyncio.run(seed())
    if mode == "administrator":
        test_client.get("/api/me")
        monkeypatch.setattr(backend_config, "auth_mode", AuthMode.SESSION)
        from camply.server.app import app
        from camply.server.auth import CurrentUser, resolve_current_user

        admin = CurrentUser(
            id=owner_id, email="admin@example.test", is_admin=True, is_invited=True
        )
        app.dependency_overrides[resolve_current_user] = lambda: admin
    elif mode == "automatic":
        monkeypatch.setattr(backend_config, "admin_email", email)
    else:
        monkeypatch.setattr(backend_config, "auth_mode", AuthMode.AUTH0)

    monkeypatch.setattr("camply.db.models.users.uuid.uuid4", lambda: new_id)
    try:
        if mode == "administrator":
            response = test_client.post(
                "/api/admin/users",
                json={"email": email, "password": "SyntheticPassword123!"},
            )
            assert response.status_code == 201
        else:
            with patch(
                "camply.server.auth._verify_auth0_token",
                new=AsyncMock(return_value={"sub": f"auth0|{new_id}", "email": email}),
            ):
                response = test_client.get(
                    "/api/me", headers={"Authorization": "Bearer synthetic"}
                )
            assert response.status_code == 200
        assert response.json()["id"] == str(new_id)
    finally:
        if mode == "administrator":
            app.dependency_overrides.pop(resolve_current_user, None)

    async def verify() -> None:
        """Ensure recovery preserves the prior topic and administrator audit event."""
        async with maker() as session:
            owner = await session.get(User, owner_id)
            created = await session.get(User, new_id)
            assert owner is not None and owner.ntfy_topic == topic
            assert created is not None and created.ntfy_topic.startswith(f"{topic}-")
            assert created.notification_provider == "pushover"
            if mode == "administrator":
                assert (
                    await session.scalar(
                        select(AdminAuditEvent.id).where(
                            AdminAuditEvent.subject_id == new_id
                        )
                    )
                    is not None
                )

    asyncio.run(verify())


@pytest.mark.asyncio
@pytest.mark.parametrize("conflict", ["email", "explicit_topic"])
async def test_account_insertion_does_not_rewrite_unrelated_conflicts(
    conflict: str,
) -> None:
    """Only automatically generated topic collisions are eligible for recovery."""
    owner = User(
        email=f"owner-{uuid.uuid4().hex}@example.test",
        ntfy_topic=f"chosen-{uuid.uuid4().hex}",
    )
    async with maker() as session:
        session.add(owner)
        await session.commit()
        candidate = User(
            email=owner.email
            if conflict == "email"
            else f"new-{uuid.uuid4().hex}@example.test",
            **(
                {"ntfy_topic": owner.ntfy_topic} if conflict == "explicit_topic" else {}
            ),
        )
        original_topic = candidate.ntfy_topic
        with pytest.raises(IntegrityError):
            await flush_new_user(session, candidate)
        assert candidate.ntfy_topic == original_topic
        assert await session.get(User, candidate.id) is None
