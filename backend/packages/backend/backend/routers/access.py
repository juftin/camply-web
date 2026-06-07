"""
Access request router — ``/api/request-access`` endpoint.
"""

from __future__ import annotations

import structlog
from fastapi import APIRouter, status
from sqlalchemy.exc import IntegrityError

from backend.dependencies import SessionDep
from backend.schemas import AccessRequestCreate, AccessRequestResponse
from db.models import AccessRequest

logger = structlog.getLogger(__name__)

access_router = APIRouter(tags=["access"])


@access_router.post("/request-access", status_code=status.HTTP_201_CREATED)
async def request_access(
    body: AccessRequestCreate,
    session: SessionDep,
) -> AccessRequestResponse:
    """Submit an early-access request.

    Duplicate emails are silently accepted (idempotent).
    """
    access_req = AccessRequest(email=body.email.lower().strip())
    session.add(access_req)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        logger.info("Duplicate access request ignored", email=body.email)

    logger.info("Early access requested", email=body.email, name=body.name)
    return AccessRequestResponse(
        message="Thank you! Your early access request has been received. "
        "We'll notify you when access is granted."
    )
