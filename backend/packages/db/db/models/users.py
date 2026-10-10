"""
User Model
"""

import datetime
import uuid
from functools import partial
from typing import TYPE_CHECKING, Any

from sqlalchemy import Boolean, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.models.base import Base

if TYPE_CHECKING:
    from db.models.admin_audit import AdminAuditEvent
    from db.models.user_scans import UserScan


class User(Base):
    """
    User Model
    """

    __tablename__ = "users"

    def __init__(self, **kwargs: Any) -> None:
        """Initialize invitation and scanning flags before persistence."""
        kwargs.setdefault("is_admin", False)
        kwargs.setdefault("scanning_enabled", True)
        kwargs.setdefault("is_invited", False)
        super().__init__(**kwargs)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    auth0_id: Mapped[str | None] = mapped_column(String(255), unique=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    is_invited: Mapped[bool] = mapped_column(
        "is_early_access_user", Boolean, default=False
    )
    """Invitation eligibility, backed by the existing access column."""
    pushover_token: Mapped[str | None] = mapped_column(String(255))
    is_admin: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=func.false()
    )
    scanning_enabled: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default=func.true()
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        default=partial(datetime.datetime.now, tz=datetime.timezone.utc),
        server_default=func.CURRENT_TIMESTAMP(),
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        default=partial(datetime.datetime.now, tz=datetime.timezone.utc),
        server_default=func.CURRENT_TIMESTAMP(),
        onupdate=func.CURRENT_TIMESTAMP(),
    )

    user_scans: Mapped[list["UserScan"]] = relationship(
        back_populates="user",
    )
    audit_events: Mapped[list["AdminAuditEvent"]] = relationship(
        back_populates="actor",
        foreign_keys="AdminAuditEvent.actor_id",
    )
