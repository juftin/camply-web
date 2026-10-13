"""
Tests for backend.provision CLI script.
"""

import uuid

import pytest
from conftest import maker
from sqlalchemy import select

from backend.provision import provision_admin
from db.models import User


class TestProvisionAdmin:
    """Test provisioning administrator by UUID."""

    @pytest.mark.asyncio
    async def test_provision_admin_success(self) -> None:
        user_id = uuid.uuid4()
        async with maker() as session:
            user = User(
                id=user_id,
                email=f"provision_{user_id.hex[:6]}@example.com",
                is_admin=False,
            )
            session.add(user)
            await session.commit()

        # Run provision
        async with maker() as session:
            await provision_admin(str(user_id), session=session)

        async with maker() as session:
            result = await session.execute(select(User).where(User.id == user_id))
            updated_user = result.scalar_one()
            assert updated_user.is_admin is True

    @pytest.mark.asyncio
    async def test_provision_admin_invalid_uuid(self) -> None:
        with pytest.raises(SystemExit):
            async with maker() as session:
                await provision_admin("not-a-uuid", session=session)

    @pytest.mark.asyncio
    async def test_provision_admin_nonexistent_user(self) -> None:
        with pytest.raises(SystemExit):
            async with maker() as session:
                await provision_admin(str(uuid.uuid4()), session=session)
