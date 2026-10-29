"""
Health Check API
"""

import datetime
from functools import partial

from fastapi import APIRouter, Response
from pydantic import BaseModel, Field
from sqlalchemy import text

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
async def healthcheck(response: Response) -> ApiStatus:
    """
    API Health Check
    """
    if backend_config.runtime_mode == RuntimeMode.STANDALONE:
        from camply.server.services.local_operations import runner

        try:
            async with db.get_session() as session:
                await session.execute(text("SELECT 1"))
            if runner is None or not runner.healthy:
                response.status_code = 503
        except Exception:
            response.status_code = 503
        return ApiStatus(status=response.status_code or 200)
    return ApiStatus(status=200)
