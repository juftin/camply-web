"""End-to-end API tests verifying notification secrets are encrypted at rest."""

from __future__ import annotations

import sqlite3
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from camply.db.config import DatabaseConfig, DatabaseDrivers
from camply.db.encryption import ENCRYPTED_PREFIX, EncryptionKeyError
from camply.notifications.ntfy import NtfyProvider
from camply.notifications.pushover import PushoverProvider
from camply.server.app import app as real_app
from tests.server import conftest as server_conftest


def test_api_me_encrypts_tokens_at_rest_and_round_trips(
    test_client: TestClient,
) -> None:
    """``PATCH /api/me`` stores encrypted values while ``GET /api/me`` and test sends decrypt."""
    long_ntfy = "a" * 1024
    pushover_key = "po-api-secret-key"

    try:
        patch_resp = test_client.patch(
            "/api/me",
            json={
                "notification_provider": "ntfy",
                "pushover_token": pushover_key,
                "ntfy_access_token": long_ntfy,
            },
        )
        assert patch_resp.status_code == 200, patch_resp.text
        patched = patch_resp.json()
        assert patched["pushover_token"] == pushover_key
        assert patched["ntfy_access_token"] == long_ntfy

        get_resp = test_client.get("/api/me")
        assert get_resp.status_code == 200, get_resp.text
        assert get_resp.json()["pushover_token"] == pushover_key
        assert get_resp.json()["ntfy_access_token"] == long_ntfy

        with sqlite3.connect(server_conftest._db_path) as conn:
            raw_po, raw_ntfy = conn.execute(
                "SELECT pushover_token, ntfy_access_token FROM users WHERE id = ?",
                (patched["id"].replace("-", ""),),
            ).fetchone()
        assert raw_po.startswith(ENCRYPTED_PREFIX)
        assert pushover_key not in raw_po
        assert raw_ntfy.startswith(ENCRYPTED_PREFIX)
        assert long_ntfy not in raw_ntfy

        with patch.object(
            NtfyProvider, "send_accepted", new_callable=AsyncMock, return_value=True
        ) as send_ntfy:
            test_resp = test_client.post("/api/me/notifications/test", json={})
            assert test_resp.status_code == 200, test_resp.text
            assert send_ntfy.await_args is not None
            assert send_ntfy.await_args.args[0]["access_token"] == long_ntfy

        with (
            patch.object(PushoverProvider.config, "app_token", "synthetic-app-token"),
            patch.object(
                PushoverProvider,
                "send_accepted",
                new_callable=AsyncMock,
                return_value=True,
            ) as send_po,
        ):
            po_resp = test_client.post(
                "/api/me/notifications/test",
                json={"notification_provider": "pushover"},
            )
            assert po_resp.status_code == 200, po_resp.text
            assert send_po.await_args is not None
            assert send_po.await_args.args[0] == pushover_key
    finally:
        test_client.patch(
            "/api/me",
            json={
                "notification_provider": "pushover",
                "pushover_token": None,
                "ntfy_access_token": None,
            },
        )


def test_app_lifespan_fails_fast_for_postgres_without_encryption_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """FastAPI startup rejects PostgreSQL deployments missing ``CAMPLY_ENCRYPTION_KEY``."""
    monkeypatch.delenv("CAMPLY_ENCRYPTION_KEY", raising=False)
    monkeypatch.setattr(
        "camply.db.config.db",
        DatabaseConfig(DRIVERNAME=DatabaseDrivers.POSTGRES, HOST="localhost"),
    )
    with pytest.raises(EncryptionKeyError, match="CAMPLY_ENCRYPTION_KEY"):
        with TestClient(real_app):
            pass
