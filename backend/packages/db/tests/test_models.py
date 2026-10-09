"""
Tests for Checklist Data Layer Models
"""

import datetime
import hashlib

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from db.eligibility import (
    eligible_scan_condition,
    is_scan_eligible,
    is_user_scan_eligible,
)
from db.models import (
    AdminAuditEvent,
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
    assert user.is_admin is False
    assert user.scanning_enabled is True


def test_user_admin_and_scanning_flags(session: Session):
    """
    Test setting is_admin and scanning_enabled flags on User
    """
    user = User(
        email="admin@example.com",
        is_admin=True,
        scanning_enabled=False,
    )
    session.add(user)
    session.commit()

    assert user.is_admin is True
    assert user.scanning_enabled is False


def test_admin_audit_event_creation(session: Session, user: User):
    """
    Test creating an AdminAuditEvent linked to an actor User
    """
    audit = AdminAuditEvent(
        actor_id=user.id,
        action="user.scanning_enabled",
        subject_type="user",
        subject_id=user.id,
        prev_value=True,
        new_value=False,
    )
    session.add(audit)
    session.commit()

    assert audit.id is not None
    assert audit.actor_id == user.id
    assert audit.actor.email == user.email
    assert audit.action == "user.scanning_enabled"
    assert audit.prev_value is True
    assert audit.new_value is False
    assert audit.created_at is not None
    assert len(user.audit_events) == 1


def test_eligibility_helpers(session: Session, user: User, target: UniqueTarget):
    """
    Test shared eligibility helpers: is_scan_eligible, is_user_scan_eligible, and eligible_scan_condition
    """
    scan = UserScan(
        user_id=user.id,
        target_id=target.id,
        is_active=True,
    )
    session.add(scan)
    session.commit()

    # User scanning enabled (True) + scan active (True) => eligible
    assert is_scan_eligible(user.scanning_enabled, scan.is_active) is True
    assert is_user_scan_eligible(user, scan) is True

    # User suspended (scanning_enabled=False) + scan active (True) => not eligible
    user.scanning_enabled = False
    session.commit()
    assert is_scan_eligible(user.scanning_enabled, scan.is_active) is False
    assert is_user_scan_eligible(user, scan) is False

    # User enabled + scan inactive (False) => not eligible
    user.scanning_enabled = True
    scan.is_active = False
    session.commit()
    assert is_scan_eligible(user.scanning_enabled, scan.is_active) is False
    assert is_user_scan_eligible(user, scan) is False

    # Test eligible_scan_condition query
    from sqlalchemy import select

    stmt = (
        select(UserScan)
        .join(User, User.id == UserScan.user_id)
        .where(eligible_scan_condition())
    )
    assert len(session.execute(stmt).scalars().all()) == 0

    scan.is_active = True
    session.commit()
    assert len(session.execute(stmt).scalars().all()) == 1


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
