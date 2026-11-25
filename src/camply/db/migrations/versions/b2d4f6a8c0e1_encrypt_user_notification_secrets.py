"""
widen and encrypt user notification secret columns at rest

Revision ID: b2d4f6a8c0e1
Revises: a1c3e5f7b9d2
Create Date: 2026-11-25 06:30:00.000000+00:00
"""

from __future__ import annotations

import logging
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import context, op

from camply.db.encryption import (
    decrypt_value,
    encrypt_value,
    is_encrypted,
    resolve_cipher_for_connection,
)

# revision identifiers, used by Alembic.
revision: str = "b2d4f6a8c0e1"
down_revision: str | Sequence[str] | None = "a1c3e5f7b9d2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

logger = logging.getLogger(__name__)


def _users_table() -> sa.TableClause:
    """Return a minimal table handle for raw token columns during migration."""
    return sa.table(
        "users",
        sa.column("id"),
        sa.column("pushover_token", sa.Text()),
        sa.column("ntfy_access_token", sa.Text()),
    )


def upgrade() -> None:
    """
    Widen ``users.pushover_token`` and ``users.ntfy_access_token`` to ``Text``
    and encrypt any existing plaintext values when an encryption key is available.
    """
    with op.batch_alter_table("users") as batch_op:
        batch_op.alter_column(
            "pushover_token",
            existing_type=sa.String(length=255),
            type_=sa.Text(),
            existing_nullable=True,
        )
        batch_op.alter_column(
            "ntfy_access_token",
            existing_type=sa.String(length=1024),
            type_=sa.Text(),
            existing_nullable=True,
        )

    if context.is_offline_mode():
        return

    connection = op.get_bind()
    users = _users_table()
    rows = connection.execute(
        sa.select(users.c.id, users.c.pushover_token, users.c.ntfy_access_token).where(
            sa.or_(
                users.c.pushover_token.is_not(None),
                users.c.ntfy_access_token.is_not(None),
            )
        )
    ).all()

    pending_rows = [
        (user_id, pushover_raw, ntfy_raw)
        for user_id, pushover_raw, ntfy_raw in rows
        if (pushover_raw and not is_encrypted(pushover_raw))
        or (ntfy_raw and not is_encrypted(ntfy_raw))
    ]
    if not pending_rows:
        return

    cipher = resolve_cipher_for_connection(
        connection=connection,
        allow_missing_for_non_sqlite=True,
    )
    if cipher is None:
        logger.warning(
            "CAMPLY_ENCRYPTION_KEY is not set; skipping encryption of %d existing "
            "user row(s). Set CAMPLY_ENCRYPTION_KEY and run "
            "'camply db rotate-encryption-key' to encrypt legacy plaintext tokens.",
            len(pending_rows),
        )
        return

    for user_id, pushover_raw, ntfy_raw in pending_rows:
        updates: dict[str, str | None] = {}
        if pushover_raw and not is_encrypted(pushover_raw):
            updates["pushover_token"] = encrypt_value(value=pushover_raw, cipher=cipher)
        if ntfy_raw and not is_encrypted(ntfy_raw):
            updates["ntfy_access_token"] = encrypt_value(value=ntfy_raw, cipher=cipher)
        if updates:
            connection.execute(
                users.update().where(users.c.id == user_id).values(**updates)
            )


def downgrade() -> None:
    """
    Decrypt stored notification secrets back to plaintext and restore the
    previous ``String(255)`` / ``String(1024)`` column types.
    """
    if not context.is_offline_mode():
        connection = op.get_bind()
        users = _users_table()
        rows = connection.execute(
            sa.select(
                users.c.id, users.c.pushover_token, users.c.ntfy_access_token
            ).where(
                sa.or_(
                    users.c.pushover_token.is_not(None),
                    users.c.ntfy_access_token.is_not(None),
                )
            )
        ).all()

        encrypted_rows = [
            (user_id, pushover_raw, ntfy_raw)
            for user_id, pushover_raw, ntfy_raw in rows
            if is_encrypted(pushover_raw) or is_encrypted(ntfy_raw)
        ]
        if encrypted_rows:
            cipher = resolve_cipher_for_connection(
                connection=connection,
                allow_missing_for_non_sqlite=False,
            )
            assert cipher is not None
            for user_id, pushover_raw, ntfy_raw in encrypted_rows:
                updates: dict[str, str | None] = {}
                if is_encrypted(pushover_raw):
                    updates["pushover_token"] = decrypt_value(
                        value=pushover_raw, cipher=cipher
                    )
                if is_encrypted(ntfy_raw):
                    updates["ntfy_access_token"] = decrypt_value(
                        value=ntfy_raw, cipher=cipher
                    )
                if updates:
                    connection.execute(
                        users.update().where(users.c.id == user_id).values(**updates)
                    )

    with op.batch_alter_table("users") as batch_op:
        batch_op.alter_column(
            "pushover_token",
            existing_type=sa.Text(),
            type_=sa.String(length=255),
            existing_nullable=True,
        )
        batch_op.alter_column(
            "ntfy_access_token",
            existing_type=sa.Text(),
            type_=sa.String(length=1024),
            existing_nullable=True,
        )
