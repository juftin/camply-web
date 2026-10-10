"""
Shared eligibility utilities for campsite scanning.

Effective scanning eligibility is User.scanning_enabled AND UserScan.is_active.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import and_
from sqlalchemy.sql.elements import ColumnElement

if TYPE_CHECKING:
    from db.models.user_scans import UserScan
    from db.models.users import User


def is_scan_eligible(scanning_enabled: bool, is_active: bool) -> bool:
    """Check whether a user scan is effectively eligible for scanning."""
    return bool(scanning_enabled and is_active)


def is_user_scan_eligible(user: User, scan: UserScan) -> bool:
    """Check whether a user and scan combination is effectively eligible."""
    return is_scan_eligible(user.scanning_enabled, scan.is_active)


def eligible_scan_condition() -> ColumnElement[bool]:
    """Return the SQLAlchemy expression for effective scanning eligibility."""
    from db.models.user_scans import UserScan
    from db.models.users import User

    return and_(
        User.scanning_enabled.is_(True),
        UserScan.is_active.is_(True),
    )
