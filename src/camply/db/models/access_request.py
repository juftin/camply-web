"""
Access Request Model
"""

import datetime
import enum
import uuid
from functools import partial

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, validates

from camply.db.models.base import Base


class AccessRequestStatus(str, enum.Enum):
    """Access request status."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class AccessRequest(Base):
    """Early-access request from a user's email."""

    __tablename__ = "access_requests"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    """Optional requester name supplied with the request."""
    status: Mapped[str] = mapped_column(
        String(20), default=AccessRequestStatus.PENDING.value
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        default=partial(datetime.datetime.now, tz=datetime.timezone.utc),
        server_default=func.CURRENT_TIMESTAMP(),
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        default=partial(datetime.datetime.now, tz=datetime.timezone.utc),
        server_default=func.CURRENT_TIMESTAMP(),
        onupdate=partial(datetime.datetime.now, tz=datetime.timezone.utc),
    )
    reviewed_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    """When an administrator last approved or rejected the request."""
    reviewed_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    """Administrator who last reviewed the request."""
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    """User account this request was matched to, once one exists."""

    @validates("email")
    def _normalize_email(self, key: str, value: str) -> str:
        """Store emails stripped and lowercased so lookups are case-insensitive."""
        return value.strip().lower()
