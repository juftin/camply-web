"""
Shared test fixtures for worker tests.
"""

import datetime
from collections.abc import AsyncGenerator
from pathlib import Path
from typing import Generator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from db.config import DatabaseConfig
from db.models import (
    Base,
    Campground,
    Provider,
    ScanResult,
    UniqueTarget,
    User,
    UserScan,
)
from worker.celery_app import celery_app


@pytest.fixture
def anyio_backend() -> str:
    """Limit anyio to asyncio backend only (trio is not installed)."""
    return "asyncio"


@pytest.fixture(autouse=True)
def use_eager_mode() -> Generator[None, None, None]:
    """
    Configure Celery to run tasks synchronously (eager mode).
    This eliminates the need for a broker during testing.
    """
    celery_app.conf.task_always_eager = True
    celery_app.conf.task_eager_propagates = True
    yield
    celery_app.conf.task_always_eager = False
    celery_app.conf.task_eager_propagates = False


@pytest.fixture(name="session")
def session_fixture() -> Generator[Session, None, None]:
    """Synchronous SQLite in-memory session for tests."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


@pytest.fixture(name="provider")
def provider_fixture(session: Session) -> Provider:
    p = Provider(name="Recreation.gov", url="https://recreation.gov", id=1)
    session.add(p)
    session.commit()
    return p


@pytest.fixture(name="campground")
def campground_fixture(session: Session, provider: Provider) -> Campground:
    cg = Campground(
        id="234708", provider_id=provider.id, name="Apache Trout Campground"
    )
    session.add(cg)
    session.commit()
    return cg


@pytest.fixture(name="user")
def user_fixture(session: Session) -> User:
    u = User(
        email="test@example.com",
        pushover_token="test_pushover_token_123",
    )
    session.add(u)
    session.commit()
    return u


@pytest.fixture(name="target")
def target_fixture(
    session: Session, provider: Provider, campground: Campground
) -> UniqueTarget:
    t = UniqueTarget(
        provider_id=provider.id,
        campground_id=campground.id,
        start_date=datetime.date(2026, 9, 1),
        end_date=datetime.date(2026, 9, 3),
    )
    session.add(t)
    session.commit()
    return t


@pytest.fixture(name="user_scan")
def user_scan_fixture(session: Session, user: User, target: UniqueTarget) -> UserScan:
    scan = UserScan(
        user_id=user.id,
        target_id=target.id,
        is_active=True,
        min_stay_length=1,
        preferred_types=["TENT", "RV"],
        require_electric=False,
    )
    session.add(scan)
    session.commit()
    return scan


@pytest.fixture(name="scan_result")
def scan_result_fixture(session: Session, target: UniqueTarget) -> ScanResult:
    sr = ScanResult(
        target_id=target.id,
        campsite_id="site_1",
        available_dates=["2026-09-01"],
    )
    session.add(sr)
    session.commit()
    return sr


@pytest.fixture
async def local_data(
    tmp_path: Path,
) -> AsyncGenerator[tuple[DatabaseConfig, UniqueTarget, UserScan], None]:
    """Seed synthetic linked records with real SQLite foreign-key enforcement."""
    database = DatabaseConfig(HOST=str(tmp_path / "state.db"))
    database.open()
    engine = database.get_session_maker().kw["bind"]
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    today = datetime.datetime.now(datetime.timezone.utc).date()
    async with database.get_session() as session:
        session.add(Provider(id=1, name="Synthetic", url="https://example.test"))
        await session.flush()
        session.add(Campground(id="park", provider_id=1, name="Synthetic park"))
        user = User(
            email="synthetic@example.test", pushover_token="synthetic", is_invited=True
        )
        session.add(user)
        await session.flush()
        target = UniqueTarget(
            provider_id=1,
            campground_id="park",
            start_date=today - datetime.timedelta(days=1),
            end_date=today + datetime.timedelta(days=3),
        )
        session.add(target)
        await session.flush()
        scan = UserScan(user_id=user.id, target_id=target.id, min_stay_length=2)
        session.add(scan)
        await session.commit()
    yield database, target, scan
    await database.close()
