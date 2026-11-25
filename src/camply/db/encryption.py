"""
Application-level encryption at rest for persisted user notification secrets.

Uses authenticated symmetric encryption (``cryptography.fernet.MultiFernet``)
with a versioned ciphertext prefix (``enc:v1:``). Explicit keys are configured
via ``CAMPLY_ENCRYPTION_KEY`` (comma-separated Fernet keys for rotation, where
the first key encrypts and all keys can decrypt). File-backed SQLite databases
automatically generate and persist a ``0600`` local sidecar key file when no
environment key is supplied; PostgreSQL and other non-SQLite databases require
``CAMPLY_ENCRYPTION_KEY`` explicitly.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import TYPE_CHECKING, Any, ClassVar
from weakref import WeakKeyDictionary

import sqlalchemy as sa
from cryptography.fernet import Fernet, InvalidToken, MultiFernet
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import Connection, Text, TypeDecorator, event
from sqlalchemy.engine import Dialect, Engine

if TYPE_CHECKING:
    from camply.db.config import DatabaseConfig

ENCRYPTED_PREFIX: str = "enc:v1:"
"""Versioned marker identifying ciphertexts encrypted by this module."""

_KEY_GENERATION_HINT: str = (
    "Generate a Fernet key with: "
    "python -c 'from cryptography.fernet import Fernet; "
    "print(Fernet.generate_key().decode())'"
)
"""Actionable key-generation command included in configuration errors."""

_IN_MEMORY_SENTINEL: str = ":memory:"
"""Internal sentinel identifying an ephemeral in-memory SQLite dialect."""

_DIALECT_SQLITE_PATHS: WeakKeyDictionary[Dialect, Path | str] = WeakKeyDictionary()
"""Per-engine mapping from SQLite dialects to their resolved database file or sentinel."""

_EPHEMERAL_CIPHERS: WeakKeyDictionary[Dialect, MultiFernet] = WeakKeyDictionary()
"""Per-engine ephemeral Fernet ciphers for in-memory SQLite test databases."""

_FILE_CIPHER_CACHE: dict[Path, tuple[int, int, MultiFernet]] = {}
"""Cache of file-backed SQLite ciphers keyed by path, mtime_ns, and byte size."""


class EncryptionError(RuntimeError):
    """Base error raised for notification-secret encryption failures."""


class EncryptionKeyError(EncryptionError):
    """Raised when encryption key configuration is missing or malformed."""


class DecryptionError(EncryptionError):
    """Raised when a stored ciphertext cannot be decrypted with active keys."""


class EncryptionConfig(BaseSettings):
    """Configuration for application-level database secret encryption."""

    model_config: ClassVar[SettingsConfigDict] = SettingsConfigDict(
        env_prefix="CAMPLY_",
        case_sensitive=False,
    )

    encryption_key: str | None = Field(default=None, repr=False)
    """Comma-separated Fernet key(s); the first encrypts and all can decrypt."""


@dataclass(frozen=True)
class ReencryptionSummary:
    """Counts reported after encrypting legacy plaintext or rotating keys."""

    users_updated: int
    """Number of user rows whose encrypted secret columns were updated."""
    values_encrypted: int
    """Number of legacy plaintext token values newly encrypted."""
    values_rotated: int
    """Number of already-encrypted token values re-encrypted with the primary key."""


def is_encrypted(value: str | None) -> bool:
    """Return ``True`` when ``value`` carries the versioned ciphertext prefix."""
    return isinstance(value, str) and value.startswith(ENCRYPTED_PREFIX)


def sqlite_key_path(database_path: Path) -> Path:
    """Return the sidecar key file path adjacent to a file-backed SQLite database."""
    return database_path.with_name(f"{database_path.name}.key")


def get_configured_encryption_key() -> str | None:
    """Return the normalized ``CAMPLY_ENCRYPTION_KEY`` value, or ``None`` if unset."""
    raw = EncryptionConfig().encryption_key
    if raw is None:
        return None
    stripped = raw.strip()
    return stripped or None


@lru_cache(maxsize=16)
def _cipher_from_key_string(raw_keys: str) -> MultiFernet:
    """Parse and validate one or more comma-separated Fernet keys without leaking material."""
    parts = [part.strip() for part in raw_keys.split(",")]
    if not parts or any(not part for part in parts):
        raise EncryptionKeyError(
            "Invalid CAMPLY_ENCRYPTION_KEY: expected one or more comma-separated "
            f"Fernet keys with no empty entries. {_KEY_GENERATION_HINT}"
        )
    fernets: list[Fernet] = []
    for part in parts:
        try:
            key_bytes = part.encode("ascii")
            fernets.append(Fernet(key_bytes))
        except (ValueError, TypeError, UnicodeEncodeError):
            raise EncryptionKeyError(
                "Invalid CAMPLY_ENCRYPTION_KEY: each key must be a valid URL-safe "
                f"base64-encoded 32-byte Fernet key. {_KEY_GENERATION_HINT}"
            ) from None
    return MultiFernet(fernets)


def _read_sqlite_key_file(key_path: Path) -> MultiFernet:
    """Load and validate an existing local SQLite key file, caching by stat signature."""
    stat = key_path.stat()
    cached = _FILE_CIPHER_CACHE.get(key_path)
    if (
        cached is not None
        and cached[0] == stat.st_mtime_ns
        and cached[1] == stat.st_size
    ):
        return cached[2]
    try:
        raw = key_path.read_text(encoding="ascii").strip()
    except (OSError, UnicodeDecodeError) as exc:
        raise EncryptionKeyError(
            f"Could not read local SQLite encryption key file at {key_path}."
        ) from exc
    if not raw:
        raise EncryptionKeyError(
            f"Local SQLite encryption key file at {key_path} is empty."
        )
    try:
        cipher = _cipher_from_key_string(raw)
    except EncryptionKeyError:
        raise EncryptionKeyError(
            f"Local SQLite encryption key file at {key_path} does not contain a valid "
            f"Fernet key. {_KEY_GENERATION_HINT}"
        ) from None
    _FILE_CIPHER_CACHE[key_path] = (stat.st_mtime_ns, stat.st_size, cipher)
    return cipher


def load_or_create_sqlite_key(database_path: Path) -> MultiFernet:
    """Load an adjacent SQLite key file, or atomically generate one with ``0600`` mode."""
    resolved_db = database_path.expanduser().resolve()
    key_path = sqlite_key_path(resolved_db)
    if key_path.is_file():
        return _read_sqlite_key_file(key_path)

    key_path.parent.mkdir(parents=True, exist_ok=True)
    new_key = Fernet.generate_key()
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    try:
        fd = os.open(key_path, flags, 0o600)
    except FileExistsError:
        return _read_sqlite_key_file(key_path)

    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(new_key + b"\n")
            handle.flush()
            os.fsync(handle.fileno())
    except BaseException:
        key_path.unlink(missing_ok=True)
        raise

    if os.name != "nt":
        os.chmod(key_path, 0o600)

    return _read_sqlite_key_file(key_path)


def register_sqlite_dialect(dialect: Dialect, database_path: Path | None) -> None:
    """Associate a SQLAlchemy SQLite dialect with its file path or in-memory sentinel."""
    if database_path is None:
        _DIALECT_SQLITE_PATHS[dialect] = _IN_MEMORY_SENTINEL
    else:
        _DIALECT_SQLITE_PATHS[dialect] = database_path.expanduser().resolve()


def _sqlite_path_from_url(url: sa.engine.URL) -> Path | None:
    """Return the resolved path for a file-backed SQLite URL, or ``None`` for memory."""
    if url.get_backend_name() != "sqlite":
        return None
    database = url.database
    if not database or database == ":memory:" or url.query.get("mode") == "memory":
        return None
    return Path(database).expanduser().resolve()


@event.listens_for(Engine, "engine_connect")
def _track_sqlite_engine_dialect(connection: Connection) -> None:
    """Record each SQLite engine's file path so ``EncryptedString`` resolves its key."""
    if connection.dialect.name != "sqlite":
        return
    if connection.dialect not in _DIALECT_SQLITE_PATHS:
        register_sqlite_dialect(
            dialect=connection.dialect,
            database_path=_sqlite_path_from_url(connection.engine.url),
        )


def validate_encryption_config(
    database_config: DatabaseConfig | None = None,
) -> None:
    """Validate ``CAMPLY_ENCRYPTION_KEY`` and fail fast when required for PostgreSQL."""
    raw_key = get_configured_encryption_key()
    if raw_key is not None:
        _cipher_from_key_string(raw_key)
        return

    from camply.db.config import DatabaseConfig as _DatabaseConfig
    from camply.db.config import DatabaseDrivers

    resolved = database_config or _DatabaseConfig()
    if resolved.DRIVERNAME != DatabaseDrivers.SQLITE:
        raise EncryptionKeyError(
            "CAMPLY_ENCRYPTION_KEY is required when using PostgreSQL "
            "(non-SQLite databases cannot use a local auto-generated key file). "
            f"{_KEY_GENERATION_HINT}"
        )


def resolve_cipher_for_dialect(dialect: Dialect) -> MultiFernet:
    """Return the active ``MultiFernet`` cipher for the given SQLAlchemy dialect."""
    raw_key = get_configured_encryption_key()
    if raw_key is not None:
        return _cipher_from_key_string(raw_key)

    if dialect.name != "sqlite":
        raise EncryptionKeyError(
            f"CAMPLY_ENCRYPTION_KEY is required for '{dialect.name}' databases. "
            f"{_KEY_GENERATION_HINT}"
        )

    target = _DIALECT_SQLITE_PATHS.get(dialect)
    if isinstance(target, Path):
        return load_or_create_sqlite_key(target)

    ephemeral = _EPHEMERAL_CIPHERS.get(dialect)
    if ephemeral is None:
        ephemeral = MultiFernet([Fernet(Fernet.generate_key())])
        _EPHEMERAL_CIPHERS[dialect] = ephemeral
    return ephemeral


def resolve_cipher_for_connection(
    connection: Connection,
    *,
    allow_missing_for_non_sqlite: bool = False,
) -> MultiFernet | None:
    """Return the cipher for an active SQLAlchemy connection (e.g. during migrations)."""
    raw_key = get_configured_encryption_key()
    if raw_key is not None:
        return _cipher_from_key_string(raw_key)

    if connection.dialect.name != "sqlite":
        if allow_missing_for_non_sqlite:
            return None
        raise EncryptionKeyError(
            f"CAMPLY_ENCRYPTION_KEY is required for '{connection.dialect.name}' databases. "
            f"{_KEY_GENERATION_HINT}"
        )

    sqlite_path = _sqlite_path_from_url(connection.engine.url)
    if sqlite_path is not None:
        register_sqlite_dialect(dialect=connection.dialect, database_path=sqlite_path)
        return load_or_create_sqlite_key(sqlite_path)
    return resolve_cipher_for_dialect(connection.dialect)


def encrypt_value(value: str | None, cipher: MultiFernet) -> str | None:
    """Encrypt a plaintext string with the ``enc:v1:`` prefix without double-encrypting."""
    if value is None or value == "":
        return value
    if value.startswith(ENCRYPTED_PREFIX):
        return value
    token = cipher.encrypt(value.encode("utf-8")).decode("ascii")
    return f"{ENCRYPTED_PREFIX}{token}"


def decrypt_value(value: str | None, cipher: MultiFernet) -> str | None:
    """Decrypt an ``enc:v1:`` ciphertext, passing legacy plaintext and empty values through."""
    if value is None or value == "":
        return value
    if not value.startswith(ENCRYPTED_PREFIX):
        return value
    raw_token = value[len(ENCRYPTED_PREFIX) :]
    try:
        return cipher.decrypt(raw_token.encode("ascii")).decode("utf-8")
    except (InvalidToken, UnicodeEncodeError, UnicodeDecodeError):
        raise DecryptionError(
            "Failed to decrypt stored notification secret. Verify that "
            "CAMPLY_ENCRYPTION_KEY (or the local SQLite .key file) matches the key "
            "used to encrypt this database."
        ) from None


def rotate_value(value: str, cipher: MultiFernet) -> str:
    """Re-encrypt an encrypted secret with the primary key, or encrypt legacy plaintext."""
    if not value.startswith(ENCRYPTED_PREFIX):
        token = cipher.encrypt(value.encode("utf-8")).decode("ascii")
        return f"{ENCRYPTED_PREFIX}{token}"
    raw_token = value[len(ENCRYPTED_PREFIX) :]
    try:
        rotated = cipher.rotate(raw_token.encode("ascii")).decode("ascii")
    except (InvalidToken, UnicodeEncodeError, UnicodeDecodeError):
        raise DecryptionError(
            "Failed to rotate stored notification secret. Verify that "
            "CAMPLY_ENCRYPTION_KEY includes the key that encrypted existing records."
        ) from None
    return f"{ENCRYPTED_PREFIX}{rotated}"


class EncryptedString(TypeDecorator[str]):
    """SQLAlchemy ``Text`` column type that transparently encrypts secrets at rest."""

    impl = Text
    cache_ok = True

    def process_bind_param(self, value: str | None, dialect: Dialect) -> str | None:
        """Encrypt non-empty plaintext values before writing to the database."""
        if value is None or value == "" or value.startswith(ENCRYPTED_PREFIX):
            return value
        cipher = resolve_cipher_for_dialect(dialect)
        return encrypt_value(value=value, cipher=cipher)

    def process_result_value(self, value: str | None, dialect: Dialect) -> str | None:
        """Decrypt ``enc:v1:`` values on read while tolerating legacy plaintext rows."""
        if value is None or value == "" or not value.startswith(ENCRYPTED_PREFIX):
            return value
        cipher = resolve_cipher_for_dialect(dialect)
        return decrypt_value(value=value, cipher=cipher)


def _reencrypt_users_on_connection(connection: Connection) -> ReencryptionSummary:
    """Encrypt legacy plaintext rows and rotate existing ciphertexts on one connection."""
    cipher = resolve_cipher_for_connection(
        connection=connection,
        allow_missing_for_non_sqlite=False,
    )
    assert cipher is not None

    users = sa.table(
        "users",
        sa.column("id"),
        sa.column("pushover_token", sa.Text()),
        sa.column("ntfy_access_token", sa.Text()),
    )
    rows = connection.execute(
        sa.select(users.c.id, users.c.pushover_token, users.c.ntfy_access_token).where(
            sa.or_(
                users.c.pushover_token.is_not(None),
                users.c.ntfy_access_token.is_not(None),
            )
        )
    ).all()

    users_updated = 0
    values_encrypted = 0
    values_rotated = 0

    for user_id, pushover_raw, ntfy_raw in rows:
        updates: dict[str, Any] = {}
        for column_name, raw_value in (
            ("pushover_token", pushover_raw),
            ("ntfy_access_token", ntfy_raw),
        ):
            if not raw_value:
                continue
            was_encrypted = is_encrypted(raw_value)
            updates[column_name] = rotate_value(value=raw_value, cipher=cipher)
            if was_encrypted:
                values_rotated += 1
            else:
                values_encrypted += 1

        if updates:
            connection.execute(
                users.update().where(users.c.id == user_id).values(**updates)
            )
            users_updated += 1

    return ReencryptionSummary(
        users_updated=users_updated,
        values_encrypted=values_encrypted,
        values_rotated=values_rotated,
    )


async def reencrypt_user_secrets(
    database_config: DatabaseConfig | None = None,
) -> ReencryptionSummary:
    """Encrypt legacy plaintext tokens and rotate existing ciphertexts to the primary key."""
    from camply.db.config import DatabaseConfig as _DatabaseConfig

    resolved = database_config or _DatabaseConfig()
    validate_encryption_config(database_config=resolved)
    engine = resolved.create_async_engine()
    try:
        async with engine.begin() as connection:
            return await connection.run_sync(_reencrypt_users_on_connection)
    finally:
        await engine.dispose()
