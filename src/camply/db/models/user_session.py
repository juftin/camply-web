"""
User Session Model
"""

import datetime
import uuid
from functools import partial
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from camply.db.models.base import Base

if TYPE_CHECKING:
    from camply.db.models.users import User


class UserSession(Base):
    """Server-side record for an issued password-session cookie."""

    __tablename__ = "user_sessions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    """Unique session identifier, stored as the JWT ``jti`` claim."""
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    """Owner of this password session."""
    user_agent: Mapped[str | None] = mapped_column(String(512), nullable=True)
    """Truncated User-Agent header recorded when the session was issued."""
    ip_address: Mapped[str | None] = mapped_column(String(64), nullable=True)
    """Validated client IP address recorded on login."""
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        default=partial(datetime.datetime.now, tz=datetime.timezone.utc),
        server_default=func.CURRENT_TIMESTAMP(),
        nullable=False,
    )
    """UTC timestamp when the session was created."""
    expires_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )
    """UTC expiration timestamp matching the signed cookie lifetime."""
    revoked_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    """UTC timestamp when the session was explicitly revoked, if ever."""

    user: Mapped["User"] = relationship(
        "User",
        back_populates="sessions",
    )
