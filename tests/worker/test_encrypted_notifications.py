"""Worker notification delivery tests with encrypted tokens stored at rest."""

from __future__ import annotations

import datetime as dt
import sqlite3
import uuid
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from cryptography.fernet import Fernet

from camply.db.config import DatabaseConfig
from camply.db.encryption import ENCRYPTED_PREFIX
from camply.db.models import (
    Base,
    Campground,
    NotificationOutbox,
    Provider,
    UniqueTarget,
    User,
    UserScan,
)
from camply.worker.engine.notifications import send_notification
from camply.worker.outbox import deliver_next


@pytest.mark.asyncio
async def test_worker_send_notification_decrypts_pushover_and_ntfy_tokens(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Shared worker notification engine reads encrypted rows and delivers plaintext secrets."""
    monkeypatch.setenv("CAMPLY_ENCRYPTION_KEY", Fernet.generate_key().decode())
    db_file = tmp_path / "worker_enc.db"
    database = DatabaseConfig(HOST=str(db_file))
    database.open()
    try:
        engine = database.get_session_maker().kw["bind"]
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        async with database.get_session() as session:
            po_user = User(
                email="po-worker@example.test",
                pushover_token="worker-pushover-secret",
                notification_provider="pushover",
                is_invited=True,
            )
            ntfy_user = User(
                email="ntfy-worker@example.test",
                ntfy_access_token="worker-ntfy-secret",
                notification_provider="ntfy",
                is_invited=True,
            )
            session.add_all([po_user, ntfy_user])
            await session.commit()
            po_id = str(po_user.id)
            ntfy_id = str(ntfy_user.id)

        with sqlite3.connect(db_file) as raw_conn:
            raw_po = raw_conn.execute(
                "SELECT pushover_token FROM users WHERE email = 'po-worker@example.test'"
            ).fetchone()[0]
            raw_ntfy = raw_conn.execute(
                "SELECT ntfy_access_token FROM users WHERE email = 'ntfy-worker@example.test'"
            ).fetchone()[0]
        assert raw_po.startswith(ENCRYPTED_PREFIX)
        assert raw_ntfy.startswith(ENCRYPTED_PREFIX)

        payload = {
            "title": "Site Open",
            "message": "Campsite available",
            "booking_url": "https://example.test/book",
            "park_name": "Yosemite",
            "campsite_name": "Site 1",
            "start_date": "2027-07-01",
            "end_date": "2027-07-03",
        }

        mock_pushover = MagicMock()
        mock_pushover.send_alert = AsyncMock()
        po_result = await send_notification(
            user_id=po_id,
            notification=payload,
            sessions=database.get_session,
            channel="pushover",
            provider_factory=lambda: mock_pushover,
        )
        assert po_result["status"] == "success"
        assert (
            mock_pushover.send_alert.await_args.kwargs["user_config"]["user_key"]
            == "worker-pushover-secret"
        )

        with patch(
            "camply.worker.engine.notifications.NtfyProvider.send_alert",
            new_callable=AsyncMock,
        ) as mock_ntfy_send:
            ntfy_result = await send_notification(
                user_id=ntfy_id,
                notification=payload,
                sessions=database.get_session,
                channel="ntfy",
            )
            assert ntfy_result["status"] == "success"
            assert (
                mock_ntfy_send.await_args.kwargs["user_config"]["access_token"]
                == "worker-ntfy-secret"
            )
    finally:
        await database.close()


@pytest.mark.asyncio
async def test_standalone_outbox_deliver_next_decrypts_tokens(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Standalone outbox delivery decrypts encrypted tokens on delivery."""
    monkeypatch.delenv("CAMPLY_ENCRYPTION_KEY", raising=False)
    db_file = tmp_path / "outbox_enc.db"
    database = DatabaseConfig(HOST=str(db_file))
    database.open()
    try:
        engine = database.get_session_maker().kw["bind"]
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        today = dt.datetime.now(dt.timezone.utc).date()
        async with database.get_session() as session:
            session.add(Provider(id=1, name="Synthetic", url="https://example.test"))
            await session.flush()
            session.add(Campground(id="cg1", provider_id=1, name="Synthetic Park"))
            user = User(
                email="outbox@example.test",
                notification_provider="pushover",
                pushover_token="outbox-secret-key",
                is_invited=True,
            )
            session.add(user)
            await session.flush()
            target = UniqueTarget(
                provider_id=1,
                campground_id="cg1",
                start_date=today,
                end_date=today + dt.timedelta(days=2),
            )
            session.add(target)
            await session.flush()
            scan = UserScan(
                user_id=user.id,
                target_id=target.id,
                min_stay_length=1,
            )
            session.add(scan)
            await session.flush()
            session.add(
                NotificationOutbox(
                    detection_id=uuid.uuid4(),
                    user_id=user.id,
                    scan_id=scan.id,
                    target_id=target.id,
                    channel="pushover",
                    delivery_key="site-1",
                    payload={
                        "title": "Site Open",
                        "message": "Available",
                        "booking_url": "https://example.test/book",
                        "park_name": "Synthetic Park",
                        "campsite_name": "Site 1",
                        "start_date": today.isoformat(),
                        "end_date": (today + dt.timedelta(days=1)).isoformat(),
                        "metadata": {
                            "campsite_id": "site-1",
                            "available_dates": [today.isoformat()],
                        },
                    },
                    status="pending",
                    attempt_count=0,
                    created_at=dt.datetime.now(dt.timezone.utc),
                    next_attempt_at=dt.datetime.now(dt.timezone.utc)
                    - dt.timedelta(seconds=5),
                )
            )
            await session.commit()

        delivered_tokens: list[str] = []

        async def _capture_send(token: str, _payload: object) -> bool:
            delivered_tokens.append(token)
            return True

        outcome = await deliver_next(database, send=_capture_send)
        assert outcome is not None
        assert outcome["outcome"] == "success"
        assert delivered_tokens == ["outbox-secret-key"]
    finally:
        await database.close()
