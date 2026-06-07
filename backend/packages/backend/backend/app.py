# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0

"""
camply-backend FastAPI Application
"""

import structlog
from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import ORJSONResponse

from backend.__about__ import __application__, __version__
from backend.config import backend_config
from backend.routers.campgrounds import campground_router
from backend.routers.health import health_router
from backend.routers.me import me_router
from backend.routers.providers import provider_router
from backend.routers.recreation_areas import recreation_area_router
from backend.routers.scans import scan_router
from backend.routers.access_request import access_request_router
from backend.routers.search import search_router

logger = structlog.getLogger(__name__)

# ---------------------------------------------------------------------------
# Sentry initialisation
# ---------------------------------------------------------------------------
if backend_config.sentry_dsn:
    import sentry_sdk
    from sentry_sdk.integrations.fastapi import FastApiIntegration
    from sentry_sdk.integrations.starlette import StarletteIntegration

    sentry_sdk.init(
        dsn=backend_config.sentry_dsn,
        traces_sample_rate=backend_config.sentry_traces_sample_rate,
        integrations=[
            StarletteIntegration(),
            FastApiIntegration(),
        ],
        environment=backend_config.environment,
    )
    logger.info("Sentry initialized for FastAPI backend")

# ---------------------------------------------------------------------------
# FastAPI application
# ---------------------------------------------------------------------------

app = FastAPI(
    title=__application__,
    version=__version__,
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
    redoc_url=None,
    default_response_class=ORJSONResponse,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "https://camply.juftin.dev",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

API_ROUTERS: list[APIRouter] = [
    health_router,
    search_router,
    campground_router,
    recreation_area_router,
    provider_router,
    scan_router,
    me_router,
    access_request_router,
]

for router in API_ROUTERS:
    app.include_router(router, prefix="/api")


def main() -> None:  # pragma: no cover
    """
    API Server Entry Point
    """
    import uvicorn

    uvicorn.run(
        app="backend.app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )


if __name__ == "__main__":
    main()
