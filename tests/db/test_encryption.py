"""Tests for application-level encryption of user notification secrets at rest."""

from __future__ import annotations

import io
import os
import sqlite3
import stat
import uuid
from pathlib import Path

import pytest
import sqlalchemy as sa
import yaml
from alembic import command
from click.testing import CliRunner
from cryptography.fernet import Fernet, MultiFernet
from sqlalchemy import create_engine, select, text
from sqlalchemy.dialects import postgresql, sqlite
from sqlalchemy.orm import Session

from camply.cli.main import cli
from camply.db.config import DatabaseConfig, DatabaseDrivers
from camply.db.encryption import (
    ENCRYPTED_PREFIX,
    DecryptionError,
    EncryptedString,
    EncryptionConfig,
    EncryptionKeyError,
    decrypt_value,
    encrypt_value,
    is_encrypted,
    reencrypt_user_secrets,
    sqlite_key_path,
    validate_encryption_config,
)
from camply.db.migration import get_alembic_config
from camply.db.models import Base, User


def _new_key() -> str:
    """Return a fresh URL-safe base64 Fernet key string."""
    return Fernet.generate_key().decode("ascii")


def test_config_repr_hides_encryption_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """``EncryptionConfig`` must never expose key material in ``repr()``."""
    secret_key = _new_key()
    monkeypatch.setenv("CAMPLY_ENCRYPTION_KEY", secret_key)
    config = EncryptionConfig()
    assert config.encryption_key == secret_key
    assert secret_key not in repr(config)


def test_encrypted_string_round_trip_and_raw_storage(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """ORM writes ciphertext with ``enc:v1:`` prefix and transparently decrypts on read."""
    key = _new_key()
    monkeypatch.setenv("CAMPLY_ENCRYPTION_KEY", key)

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    max_ntfy_token = "t" * 1024
    with Session(engine) as session:
        user = User(
            email="enc@example.test",
            pushover_token="pushover-secret-key",
            ntfy_access_token=max_ntfy_token,
        )
        session.add(user)
        session.commit()
        user_id = user.id

    with engine.connect() as conn:
        raw_pushover, raw_ntfy = conn.execute(
            text(
                "SELECT pushover_token, ntfy_access_token FROM users WHERE email = :email"
            ),
            {"email": "enc@example.test"},
        ).one()

    assert raw_pushover != "pushover-secret-key"
    assert raw_pushover.startswith(ENCRYPTED_PREFIX)
    assert "pushover-secret-key" not in raw_pushover
    assert raw_ntfy != max_ntfy_token
    assert raw_ntfy.startswith(ENCRYPTED_PREFIX)
    assert len(raw_ntfy) > 1024

    with Session(engine) as session:
        loaded = session.get(User, user_id)
        assert loaded is not None
        assert loaded.pushover_token == "pushover-secret-key"
        assert loaded.ntfy_access_token == max_ntfy_token


def test_none_and_empty_string_handling(monkeypatch: pytest.MonkeyPatch) -> None:
    """``None`` and empty string pass through without producing ciphertext."""
    monkeypatch.setenv("CAMPLY_ENCRYPTION_KEY", _new_key())

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        user_none = User(
            email="none@example.test",
            pushover_token=None,
            ntfy_access_token=None,
        )
        user_empty = User(
            email="empty@example.test",
            pushover_token="",
            ntfy_access_token="",
        )
        session.add_all([user_none, user_empty])
        session.commit()

    with engine.connect() as conn:
        rows = dict(
            conn.execute(text("SELECT email, pushover_token FROM users")).fetchall()
        )
        ntfy_rows = dict(
            conn.execute(text("SELECT email, ntfy_access_token FROM users")).fetchall()
        )

    assert rows["none@example.test"] is None
    assert ntfy_rows["none@example.test"] is None
    assert rows["empty@example.test"] == ""
    assert ntfy_rows["empty@example.test"] == ""

    with Session(engine) as session:
        loaded_none = session.scalar(
            select(User).where(User.email == "none@example.test")
        )
        loaded_empty = session.scalar(
            select(User).where(User.email == "empty@example.test")
        )
        assert loaded_none is not None
        assert loaded_none.pushover_token is None
        assert loaded_none.ntfy_access_token is None
        assert loaded_empty is not None
        assert loaded_empty.pushover_token == ""
        assert loaded_empty.ntfy_access_token == ""


def test_does_not_double_encrypt_prefixed_ciphertext(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Already-prefixed ``enc:v1:`` values are never encrypted a second time."""
    key = _new_key()
    monkeypatch.setenv("CAMPLY_ENCRYPTION_KEY", key)
    col_type = EncryptedString()
    dialect = sqlite.dialect()

    ciphertext = col_type.process_bind_param("my-secret", dialect)
    assert ciphertext is not None and ciphertext.startswith(ENCRYPTED_PREFIX)
    again = col_type.process_bind_param(ciphertext, dialect)
    assert again == ciphertext
    assert col_type.process_result_value(again, dialect) == "my-secret"


def test_wrong_key_decryption_fails_cleanly_without_secret_leakage(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Decrypting with the wrong key raises ``DecryptionError`` without leaking data."""
    key_a = _new_key()
    key_b = _new_key()
    plaintext = "super-sensitive-pushover-token"

    monkeypatch.setenv("CAMPLY_ENCRYPTION_KEY", key_a)
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        session.add(User(email="leak-check@example.test", pushover_token=plaintext))
        session.commit()

    with engine.connect() as conn:
        raw_ciphertext = conn.execute(
            text(
                "SELECT pushover_token FROM users WHERE email = 'leak-check@example.test'"
            )
        ).scalar_one()

    monkeypatch.setenv("CAMPLY_ENCRYPTION_KEY", key_b)
    with Session(engine) as session:
        with pytest.raises(DecryptionError) as exc_info:
            session.scalar(select(User).where(User.email == "leak-check@example.test"))

    message = str(exc_info.value)
    assert plaintext not in message
    assert raw_ciphertext not in message
    assert key_a not in message
    assert key_b not in message


@pytest.mark.parametrize("bad_key", ["not-a-valid-key", "key1,,key2", ",", "abc123"])
def test_invalid_encryption_key_fails_fast_without_echoing_value(
    monkeypatch: pytest.MonkeyPatch, bad_key: str
) -> None:
    """Malformed ``CAMPLY_ENCRYPTION_KEY`` raises ``EncryptionKeyError`` safely."""
    monkeypatch.setenv("CAMPLY_ENCRYPTION_KEY", bad_key)
    with pytest.raises(EncryptionKeyError) as exc_info:
        validate_encryption_config(DatabaseConfig(HOST=":memory:"))
    message = str(exc_info.value)
    assert "CAMPLY_ENCRYPTION_KEY" in message
    assert "Fernet.generate_key" in message
    if len(bad_key) > 3:
        assert bad_key not in message


def test_postgres_requires_explicit_encryption_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """PostgreSQL deployments fail fast when ``CAMPLY_ENCRYPTION_KEY`` is unset."""
    monkeypatch.delenv("CAMPLY_ENCRYPTION_KEY", raising=False)
    pg_config = DatabaseConfig(
        DRIVERNAME=DatabaseDrivers.POSTGRES,
        HOST="localhost",
    )
    with pytest.raises(EncryptionKeyError, match="CAMPLY_ENCRYPTION_KEY"):
        validate_encryption_config(pg_config)

    col_type = EncryptedString()
    pg_dialect = postgresql.dialect()
    with pytest.raises(EncryptionKeyError, match="CAMPLY_ENCRYPTION_KEY"):
        col_type.process_bind_param("secret", pg_dialect)

    monkeypatch.setenv("CAMPLY_ENCRYPTION_KEY", _new_key())
    validate_encryption_config(pg_config)
    encrypted = col_type.process_bind_param("secret", pg_dialect)
    assert encrypted is not None and encrypted.startswith(ENCRYPTED_PREFIX)
    assert col_type.process_result_value(encrypted, pg_dialect) == "secret"


@pytest.mark.asyncio
async def test_sqlite_auto_persisted_key_file_survives_restart(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """File-backed SQLite creates a ``0600`` sidecar key file usable across restarts."""
    monkeypatch.delenv("CAMPLY_ENCRYPTION_KEY", raising=False)
    db_file = tmp_path / "standalone.db"
    key_file = sqlite_key_path(db_file)

    first_db = DatabaseConfig(HOST=str(db_file))
    first_db.open()
    try:
        engine = first_db.get_session_maker().kw["bind"]
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        async with first_db.get_session() as session:
            user = User(
                email="restart@example.test",
                pushover_token="persisted-pushover",
                ntfy_access_token="persisted-ntfy",
            )
            session.add(user)
            await session.commit()
            user_id = user.id
    finally:
        await first_db.close()

    assert key_file.is_file()
    if os.name != "nt":
        assert stat.S_IMODE(key_file.stat().st_mode) == 0o600

    with sqlite3.connect(db_file) as raw_conn:
        raw_po, raw_ntfy = raw_conn.execute(
            "SELECT pushover_token, ntfy_access_token FROM users WHERE email = ?",
            ("restart@example.test",),
        ).fetchone()
    assert raw_po.startswith(ENCRYPTED_PREFIX)
    assert raw_ntfy.startswith(ENCRYPTED_PREFIX)

    # Simulate process restart with a brand new DatabaseConfig & engine
    restarted_db = DatabaseConfig(HOST=str(db_file))
    restarted_db.open()
    try:
        async with restarted_db.get_session() as session:
            reloaded = await session.get(User, user_id)
            assert reloaded is not None
            assert reloaded.pushover_token == "persisted-pushover"
            assert reloaded.ntfy_access_token == "persisted-ntfy"
    finally:
        await restarted_db.close()


def test_in_memory_sqlite_uses_ephemeral_key_without_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """In-memory SQLite works with no env key and writes no key files on disk."""
    monkeypatch.delenv("CAMPLY_ENCRYPTION_KEY", raising=False)
    monkeypatch.chdir(tmp_path)

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        session.add(User(email="mem@example.test", pushover_token="ephemeral-secret"))
        session.commit()
    with Session(engine) as session:
        user = session.scalar(select(User).where(User.email == "mem@example.test"))
        assert user is not None
        assert user.pushover_token == "ephemeral-secret"

    assert list(tmp_path.iterdir()) == []


@pytest.mark.asyncio
async def test_legacy_plaintext_read_and_key_rotation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Legacy plaintext rows remain readable and rotate cleanly with ``MultiFernet``."""
    key_v1, key_v2 = _new_key(), _new_key()
    db_file = tmp_path / "rotation.db"
    database = DatabaseConfig(HOST=str(db_file))

    monkeypatch.setenv("CAMPLY_ENCRYPTION_KEY", key_v1)
    database.open()
    try:
        engine = database.get_session_maker().kw["bind"]
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        async with database.get_session() as session:
            v1_user = User(
                email="v1@example.test",
                pushover_token="po-v1-secret",
                ntfy_access_token="ntfy-v1-secret",
            )
            legacy_user = User(email="legacy@example.test")
            session.add_all([v1_user, legacy_user])
            await session.commit()
            v1_id, legacy_id = v1_user.id, legacy_user.id
    finally:
        await database.close()

    with sqlite3.connect(db_file) as raw_conn:
        raw_conn.execute(
            "UPDATE users SET pushover_token = ?, ntfy_access_token = ? WHERE id = ?",
            ("legacy-plain-po", "legacy-plain-ntfy", legacy_id.hex),
        )

    database.open()
    try:
        async with database.get_session() as session:
            loaded_legacy = await session.get(User, legacy_id)
            assert loaded_legacy is not None
            assert loaded_legacy.pushover_token == "legacy-plain-po"
            assert loaded_legacy.ntfy_access_token == "legacy-plain-ntfy"
    finally:
        await database.close()

    monkeypatch.setenv("CAMPLY_ENCRYPTION_KEY", f"{key_v2},{key_v1}")
    summary = await reencrypt_user_secrets(database_config=database)
    assert (
        summary.users_updated,
        summary.values_encrypted,
        summary.values_rotated,
    ) == (
        2,
        2,
        2,
    )

    monkeypatch.setenv("CAMPLY_ENCRYPTION_KEY", key_v2)
    database.open()
    try:
        async with database.get_session() as session:
            u1 = await session.get(User, v1_id)
            u2 = await session.get(User, legacy_id)
            assert u1 is not None and u2 is not None
            assert (u1.pushover_token, u1.ntfy_access_token) == (
                "po-v1-secret",
                "ntfy-v1-secret",
            )
            assert (u2.pushover_token, u2.ntfy_access_token) == (
                "legacy-plain-po",
                "legacy-plain-ntfy",
            )
    finally:
        await database.close()


def test_cli_rotate_encryption_key_command(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``camply db rotate-encryption-key`` encrypts plaintext and rotates ciphertexts."""
    key_v1 = _new_key()
    key_v2 = _new_key()
    db_file = tmp_path / "cli_rotate.db"
    monkeypatch.setenv("CAMPLY_DB_DRIVERNAME", "sqlite+aiosqlite")
    monkeypatch.setenv("CAMPLY_DB_HOST", str(db_file))
    monkeypatch.setenv("CAMPLY_ENCRYPTION_KEY", key_v1)

    runner = CliRunner()
    assert runner.invoke(cli, ["db", "migrate"]).exit_code == 0

    with sqlite3.connect(db_file) as conn:
        u1_id = uuid.uuid4().hex
        u2_id = uuid.uuid4().hex
        cipher_v1 = MultiFernet([Fernet(key_v1.encode("ascii"))])
        enc_po = encrypt_value("po-already-enc", cipher_v1)
        conn.execute(
            "INSERT INTO users (id, email, is_early_access_user, pushover_token, ntfy_topic) VALUES (?, ?, 1, ?, ?)",
            (u1_id, "plain@example.test", "plain-po", f"camply-{u1_id[:7]}"),
        )
        conn.execute(
            "INSERT INTO users (id, email, is_early_access_user, pushover_token, ntfy_topic) VALUES (?, ?, 1, ?, ?)",
            (u2_id, "enc@example.test", enc_po, f"camply-{u2_id[:7]}"),
        )

    monkeypatch.setenv("CAMPLY_ENCRYPTION_KEY", f"{key_v2},{key_v1}")
    result = runner.invoke(cli, ["db", "rotate-encryption-key"])
    assert result.exit_code == 0, result.output
    assert "Updated 2 user(s): 1 encrypted, 1 rotated." in result.output

    with sqlite3.connect(db_file) as conn:
        raw_tokens = dict(
            conn.execute("SELECT email, pushover_token FROM users").fetchall()
        )
    assert is_encrypted(raw_tokens["plain@example.test"])
    assert is_encrypted(raw_tokens["enc@example.test"])
    cipher_v2 = MultiFernet([Fernet(key_v2.encode("ascii"))])
    assert decrypt_value(raw_tokens["plain@example.test"], cipher_v2) == "plain-po"
    assert decrypt_value(raw_tokens["enc@example.test"], cipher_v2) == "po-already-enc"


def test_alembic_encryption_migration_upgrade_and_downgrade(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Migration widens columns to Text, encrypts 1024-char tokens, and downgrades cleanly."""
    key = _new_key()
    monkeypatch.setenv("CAMPLY_ENCRYPTION_KEY", key)
    db_file = tmp_path / "encrypt_migration.db"
    config = get_alembic_config(DatabaseConfig(HOST=str(db_file)))

    command.upgrade(config, "a1c3e5f7b9d2")

    long_ntfy = "x" * 1024
    already_encrypted = (
        f"{ENCRYPTED_PREFIX}{Fernet(key.encode()).encrypt(b'kept-secret').decode()}"
    )
    with sqlite3.connect(db_file) as conn:
        conn.execute(
            "INSERT INTO users (id, email, is_early_access_user, pushover_token, ntfy_topic, ntfy_access_token) "
            "VALUES (?, ?, 1, ?, ?, ?), (?, ?, 1, ?, ?, ?), (?, ?, 1, NULL, ?, NULL)",
            (
                "1" * 32,
                "plain@example.test",
                "po-plain-token",
                "camply-1111111",
                long_ntfy,
                "2" * 32,
                "preenc@example.test",
                already_encrypted,
                "camply-2222222",
                "",
                "3" * 32,
                "empty@example.test",
                "camply-3333333",
            ),
        )

    command.upgrade(config, "b2d4f6a8c0e1")

    engine = sa.create_engine(f"sqlite:///{db_file}")
    try:
        with engine.connect() as conn:
            columns = {
                col["name"]: col for col in sa.inspect(conn).get_columns("users")
            }
            assert isinstance(columns["pushover_token"]["type"], sa.TEXT)
            assert isinstance(columns["ntfy_access_token"]["type"], sa.TEXT)
    finally:
        engine.dispose()

    with sqlite3.connect(db_file) as conn:
        rows = {
            email: (po, ntfy)
            for email, po, ntfy in conn.execute(
                "SELECT email, pushover_token, ntfy_access_token FROM users"
            ).fetchall()
        }
        assert conn.execute("PRAGMA foreign_key_check").fetchall() == []

    assert rows["plain@example.test"][0].startswith(ENCRYPTED_PREFIX)
    assert rows["plain@example.test"][1].startswith(ENCRYPTED_PREFIX)
    assert len(rows["plain@example.test"][1]) > 1024
    # Pre-encrypted value must not be double-encrypted
    assert rows["preenc@example.test"][0] == already_encrypted
    assert rows["preenc@example.test"][1] == ""
    assert rows["empty@example.test"] == (None, None)

    # Downgrade decrypts values back to plaintext and restores column types
    command.downgrade(config, "a1c3e5f7b9d2")
    with sqlite3.connect(db_file) as conn:
        down_rows = {
            email: (po, ntfy)
            for email, po, ntfy in conn.execute(
                "SELECT email, pushover_token, ntfy_access_token FROM users"
            ).fetchall()
        }
        assert conn.execute("PRAGMA foreign_key_check").fetchall() == []

    assert down_rows["plain@example.test"] == ("po-plain-token", long_ntfy)
    assert down_rows["preenc@example.test"] == ("kept-secret", "")
    assert down_rows["empty@example.test"] == (None, None)


def test_alembic_encryption_migration_compiles_for_postgresql() -> None:
    """Offline PostgreSQL SQL compilation widens and narrows both token columns."""
    config = get_alembic_config(DatabaseConfig(DRIVERNAME=DatabaseDrivers.POSTGRES))
    output = io.StringIO()
    config.output_buffer = output
    command.upgrade(config, revision="a1c3e5f7b9d2:b2d4f6a8c0e1", sql=True)
    upgrade_sql = output.getvalue()
    assert "ALTER TABLE users ALTER COLUMN pushover_token TYPE TEXT" in upgrade_sql
    assert "ALTER TABLE users ALTER COLUMN ntfy_access_token TYPE TEXT" in upgrade_sql

    output.truncate(0)
    output.seek(0)
    command.downgrade(config, revision="b2d4f6a8c0e1:a1c3e5f7b9d2", sql=True)
    downgrade_sql = output.getvalue()
    assert (
        "ALTER TABLE users ALTER COLUMN pushover_token TYPE VARCHAR(255)"
        in downgrade_sql
    )
    assert (
        "ALTER TABLE users ALTER COLUMN ntfy_access_token TYPE VARCHAR(1024)"
        in downgrade_sql
    )


def test_compose_local_default_encryption_key_is_valid_fernet() -> None:
    """Docker Compose wires a valid local-dev Fernet default to backend, worker, and beat."""
    root = Path(__file__).resolve().parents[2]
    compose = yaml.safe_load((root / "docker-compose.yaml").read_text())
    for service in ("backend", "celery-worker", "celery-beat"):
        raw = compose["services"][service]["environment"]["CAMPLY_ENCRYPTION_KEY"]
        assert raw.startswith("${CAMPLY_ENCRYPTION_KEY:-") and raw.endswith("}")
        default_key = raw.removeprefix("${CAMPLY_ENCRYPTION_KEY:-").removesuffix("}")
        Fernet(default_key.encode("ascii"))
