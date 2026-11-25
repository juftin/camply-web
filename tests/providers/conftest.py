"""Options for replaying and recording individual provider cases."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    from tests.providers.metadata_cases import MetadataTarget


def pytest_addoption(parser: pytest.Parser) -> None:
    """Register the single-case recording and candidate replay options."""
    group = parser.getgroup("provider cassettes")
    group.addoption("--record-provider-availability", metavar="CASE")
    group.addoption("--provider-availability-candidate", type=Path, metavar="PATH")
    group.addoption("--record-provider-metadata", metavar="CASE")
    group.addoption("--provider-metadata-candidate", type=Path, metavar="PATH")


def pytest_collection_finish(session: pytest.Session) -> None:
    """Validate the selection before a request or file write can occur."""
    for family in ("availability", "metadata"):
        record = session.config.getoption(f"record_provider_{family}")
        candidate = session.config.getoption(f"provider_{family}_candidate")
        if record is not None or candidate is not None:
            _validate_candidate(
                session, family=family, record=record, candidate=candidate
            )


def _validate_candidate(
    session: pytest.Session, *, family: str, record: str | None, candidate: Path | None
) -> None:
    """Require one matching operation and a fresh candidate inside tmp."""
    if len(session.items) != 1:
        raise pytest.UsageError(f"Select exactly one provider {family} test case")
    item = session.items[0]
    callspec = getattr(item, "callspec", None)
    case = callspec.params.get("case") if callspec is not None else None
    module = item.path.stem
    if family == "availability":
        key = case.key if module == "test_availability_cassettes" and case else None
    else:
        operation = module.removeprefix("test_metadata_").removesuffix("_cassettes")
        key = (
            f"{operation}/{case.key}"
            if module == f"test_metadata_{operation}_cassettes"
            and operation in {"discovery", "enrichment", "catalog"}
            and case
            else None
        )
    if key is None:
        raise pytest.UsageError(f"Select a provider {family} cassette test case")
    if family == "metadata":
        _validate_metadata_candidate(key=key, record=record, candidate=candidate)
    if record is not None and record != key:
        raise pytest.UsageError(f"Selected {key}, but requested {record}")
    if candidate is None:
        raise pytest.UsageError(f"Supply --provider-{family}-candidate under tmp/")
    path = candidate.resolve()
    if not path.is_relative_to(session.config.rootpath / "tmp"):
        raise pytest.UsageError("Store the candidate cassette under tmp/")
    if record is not None and path.exists():
        raise pytest.UsageError(f"Candidate already exists: {path}")


def _validate_metadata_candidate(
    *, key: str, record: str | None, candidate: Path | None
) -> None:
    """Route ZIP candidates only to the shared RIDB archive consumers."""
    if record is not None and key == "enrichment/recreation-gov":
        raise pytest.UsageError(
            "Stage a compact RIDB archive with the metadata archive tool"
        )
    if candidate is None:
        return
    if candidate.suffix.lower() == ".zip":
        if key not in {"catalog/recreation-gov", "enrichment/recreation-gov"}:
            raise pytest.UsageError(
                "A ZIP candidate requires a Recreation.gov catalog or enrichment case"
            )
        if record is not None:
            raise pytest.UsageError("ZIP candidates are for replay only")
    elif key == "enrichment/recreation-gov":
        raise pytest.UsageError("Supply a .zip candidate for Recreation.gov enrichment")


@pytest.fixture
async def metadata_database(
    monkeypatch: pytest.MonkeyPatch, case: MetadataTarget
) -> AsyncGenerator[async_sessionmaker[AsyncSession], None]:
    """Store recorded metadata in an isolated in-memory catalog."""
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    from camply.db.config import db
    from camply.db.models import Base, Provider
    from camply.providers import PROVIDERS

    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    maker = async_sessionmaker(engine, expire_on_commit=False)
    instance = PROVIDERS[case.provider_id]()
    identity = instance.provider
    await instance.async_client.aclose()
    try:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        async with maker.begin() as session:
            session.add(Provider(id=identity.id, name=identity.name, url=identity.url))
        monkeypatch.setattr(type(db), "get_session", lambda _: maker())
        yield maker
    finally:
        await engine.dispose()
