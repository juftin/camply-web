# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0

"""
Access request router — ``/api/request-access`` endpoints.
"""

from __future__ import annotations

import structlog
from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from backend.dependencies import SessionDep
from backend.schemas import AccessRequestCreate, AccessRequestResponse
from db.models import AccessRequest as AccessRequestDB

logger = structlog.getLogger(__name__)

access_request_router = APIRouter(tags=["access"])


# ---------------------------------------------------------------------------
# POST /request-access
# ---------------------------------------------------------------------------


@access_request_router.post("/request-access", status_code=status.HTTP_201_CREATED)
async def request_access(
    body: AccessRequestCreate,
    session: SessionDep,
) -> AccessRequestResponse:
    """Submit an early access request.

    If an access request with this email already exists, return ``409 Conflict``.
    """
    result = await session.execute(
        select(AccessRequestDB).where(AccessRequestDB.email == body.email)
    )
    existing = result.scalar_one_or_none()
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An access request for this email already exists",
        )

    request = AccessRequestDB(email=body.email)
    session.add(request)
    await session.commit()
    await session.refresh(request)

    logger.info("Access request created", email=body.email)

    return AccessRequestResponse(
        id=request.id,
        email=request.email,
        created_at=request.created_at,
    )
