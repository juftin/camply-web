"""
Health Check API
"""

import asyncio
import datetime
from functools import partial

from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from camply.db.config import db
from camply.server.config import RuntimeMode, backend_config

health_router = APIRouter(tags=["health"])


class ApiStatus(BaseModel):
    """
    API Status Response
    """

    status: int = Field(default=200, ge=100, le=599, description="HTTP Status Code")
    timestamp: datetime.datetime = Field(
        default_factory=partial(datetime.datetime.now, datetime.timezone.utc),
        description="Timestamp of the Health Check",
    )


@health_router.get("/ping")
def ping() -> ApiStatus:
    """
    API Ping
    """
    return ApiStatus(status=200)


@health_router.get("/health")
async def healthcheck(
    response: Response, session: AsyncSession = Depends(db.yield_session)
) -> ApiStatus:
    """Report database readiness and, in standalone mode, supervised loop health.

    Bound the database query to two seconds and return HTTP 503 on failure. Keep
    ``/api/ping`` independent of dependencies for Kubernetes liveness checks.
    """
    try:
        async with asyncio.timeout(2):
            await session.execute(text("SELECT 1"))
        if backend_config.runtime_mode == RuntimeMode.STANDALONE:
            from camply.server.services.local_operations import runner

            if runner is None or not runner.healthy:
                response.status_code = 503
    except Exception:
        response.status_code = 503
    return ApiStatus(status=response.status_code or 200)
