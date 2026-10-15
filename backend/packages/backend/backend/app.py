"""
camply-backend FastAPI Application
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import structlog
from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import Response

from backend.__about__ import __application__, __version__
from backend.config import RuntimeMode, backend_config
from backend.routers.access import access_router
from backend.routers.admin import admin_router
from backend.routers.auth_config import auth_config_router
from backend.routers.campgrounds import campground_router
from backend.routers.health import health_router
from backend.routers.me import me_router
from backend.routers.providers import provider_router
from backend.routers.recreation_areas import recreation_area_router
from backend.routers.scans import scan_router
from backend.routers.search import search_router
from backend.routers.sessions import session_router

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


@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncIterator[None]:
    """Own standalone resources and supervised tasks only while the app is serving."""
    if backend_config.runtime_mode != RuntimeMode.STANDALONE:
        yield
        return
    from backend.services import local_operations
    from backend.standalone import validate_standalone
    from db.config import db
    from worker.runtime import LocalRunner

    validate_standalone(backend_config, db)
    db.open()
    local = LocalRunner(
        db,
        heartbeat=backend_config.heartbeat_interval,
        cooldown=backend_config.target_cooldown,
        invite_only=backend_config.invite_only,
    )
    local_operations.runner = local
    try:
        await local.start()
        yield
    finally:
        await local.close()
        local_operations.runner = None
        await db.close()


app = FastAPI(
    lifespan=lifespan,
    title=__application__,
    version=__version__,
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
    redoc_url=None,
)

app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=backend_config.cors_origins,
    allow_origin_regex=backend_config.cors_origin_regex,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if backend_config.runtime_mode == RuntimeMode.DISTRIBUTED:
    from backend.metrics import (
        PrometheusMiddleware,
        get_metrics_response,
        refresh_db_gauges,
    )

    app.add_middleware(PrometheusMiddleware)

    @app.get("/metrics")
    async def metrics_endpoint() -> Response:
        """Export real monitoring instruments only in distributed mode."""
        await refresh_db_gauges()
        return get_metrics_response()


API_ROUTERS: list[APIRouter] = [
    health_router,
    auth_config_router,
    session_router,
    access_router,
    search_router,
    campground_router,
    recreation_area_router,
    provider_router,
    scan_router,
    me_router,
    admin_router,
]

for router in API_ROUTERS:
    app.include_router(router, prefix="/api")


if backend_config.runtime_mode == RuntimeMode.STANDALONE:
    from pathlib import Path

    from backend.static import attach_frontend

    attach_frontend(
        app, backend_config.frontend_dir or Path(__file__).resolve().parent / "static"
    )


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
