# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0

"""
Tests for Checklist Data Layer Models
"""

import datetime
import hashlib

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
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


@pytest.fixture(name="session")
def session_fixture():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


@pytest.fixture(name="provider")
def provider_fixture(session: Session):
    provider = Provider(name="recreation_dot_gov", url="https://recreation.gov")
    session.add(provider)
    session.commit()
    return provider


@pytest.fixture(name="campground")
def campground_fixture(session: Session, provider: Provider):
    campground = Campground(id="123", provider_id=provider.id, name="Test Campground")
    session.add(campground)
    session.commit()
    return campground


@pytest.fixture(name="user")
def user_fixture(session: Session):
    user = User(email="user@example.com")
    session.add(user)
    session.commit()
    return user


@pytest.fixture(name="target")
def target_fixture(session: Session, provider: Provider, campground: Campground):
    target = UniqueTarget(
        provider_id=provider.id,
        campground_id=campground.id,
        start_date=datetime.date(2026, 8, 1),
        end_date=datetime.date(2026, 8, 5),
    )
    session.add(target)
    session.commit()
    return target


def test_user_creation(session: Session):
    """
    US1: Test basic user creation and default values
    """
    user = User(email="test@example.com")
    session.add(user)
    session.commit()

    assert user.id is not None
    assert user.email == "test@example.com"
    assert user.is_early_access_user is False


def test_user_early_access(session: Session):
    """
    US1: Test setting early access flag
    """
    user = User(email="beta@example.com", is_early_access_user=True)
    session.add(user)
    session.commit()

    assert user.is_early_access_user is True


def test_user_unique_email(session: Session):
    """
    US1: Test unique email constraint
    """
    user1 = User(email="duplicate@example.com")
    session.add(user1)
    session.commit()

    user2 = User(email="duplicate@example.com")
    session.add(user2)
    with pytest.raises(IntegrityError):
        session.commit()


def test_unique_target_creation(
    session: Session, provider: Provider, campground: Campground
):
    """
    US2: Test unique target creation and hashing
    """
    start_date = datetime.date(2026, 6, 1)
    end_date = datetime.date(2026, 6, 5)

    target = UniqueTarget(
        provider_id=provider.id,
        campground_id=campground.id,
        start_date=start_date,
        end_date=end_date,
    )
    session.add(target)
    session.commit()

    assert target.id is not None
    assert target.hash is not None

    # Verify hash content
    hash_input = (
        f"{provider.id}:{campground.id}:{start_date.isoformat()}:{end_date.isoformat()}"
    )
    expected_hash = hashlib.sha256(hash_input.encode()).hexdigest()
    assert target.hash == expected_hash


def test_unique_target_de_duplication(
    session: Session, provider: Provider, campground: Campground
):
    """
    US2: Test that duplicate targets are prevented by hash constraint
    """
    start_date = datetime.date(2026, 7, 1)
    end_date = datetime.date(2026, 7, 5)

    target1 = UniqueTarget(
        provider_id=provider.id,
        campground_id=campground.id,
        start_date=start_date,
        end_date=end_date,
    )
    session.add(target1)
    session.commit()

    target2 = UniqueTarget(
        provider_id=provider.id,
        campground_id=campground.id,
        start_date=start_date,
        end_date=end_date,
    )
    session.add(target2)

    with pytest.raises(IntegrityError):
        session.commit()


def test_user_scan_creation(session: Session, user: User, target: UniqueTarget):
    """
    US3: Test user scan creation with filters
    """
    scan = UserScan(
        user_id=user.id,
        target_id=target.id,
        min_stay_length=2,
        preferred_types=["TENT", "RV"],
        require_electric=True,
    )
    session.add(scan)
    session.commit()

    assert scan.id is not None
    assert scan.user_id == user.id
    assert scan.target_id == target.id
    assert scan.min_stay_length == 2
    assert scan.preferred_types == ["TENT", "RV"]
    assert scan.require_electric is True

    # Verify relationships
    assert scan.user.email == user.email
    assert scan.target.hash == target.hash
    assert len(user.user_scans) == 1
    assert len(target.user_scans) == 1


def test_scan_result_creation(session: Session, target: UniqueTarget):
    """
    US4: Test scan result creation and JSONB storage
    """
    available_dates = ["2026-08-01", "2026-08-02"]
    result = ScanResult(
        target_id=target.id, campsite_id="site1", available_dates=available_dates
    )
    session.add(result)
    session.commit()

    assert result.id is not None
    assert result.target_id == target.id
    assert result.campsite_id == "site1"
    assert result.available_dates == available_dates
    assert result.found_at is not None

    # Verify relationship
    assert result.target.hash == target.hash
    assert len(target.scan_results) == 1
