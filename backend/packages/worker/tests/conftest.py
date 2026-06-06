# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0

"""
Shared test fixtures for worker tests.
"""

import datetime
from typing import Generator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

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
