"""Opt-in real API/MapLibre GL JS browser verification with a synthetic isolated catalog."""

from __future__ import annotations

import asyncio
import os
import socket
import subprocess
import threading
import time
from collections.abc import AsyncIterator
from pathlib import Path

import httpx
import pytest
import uvicorn
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from backend.app import app
from backend.config import AuthMode, backend_config
from db.config import db
from db.models import Base, Campground, Provider, RecreationArea, Search

pytestmark = pytest.mark.skipif(
    os.environ.get("CAMPLY_MAPS_SMOKE") != "1", reason="Run task maps:verify"
)


async def _seed(session: AsyncSession) -> None:
    """Populate 5,000 matching places including overlaps and coordinate edge cases."""
    for provider in (1, 2):
        session.add(
            Provider(
                id=provider,
                name=f"Fixture {provider}",
                url="https://example.test",
                enabled=True,
            )
        )
        session.add(
            RecreationArea(
                id="area",
                provider_id=provider,
                name="Synthetic Area",
                latitude=0,
                longitude=0,
                enabled=True,
                reservable=True,
            )
        )
    await session.flush()
    latitude: float | None
    longitude: float | None
    for index in range(5000):
        provider = index % 2 + 1
        identifier = f"{index // 2:05}"
        latitude, longitude = (
            (1.0, 1.0)
            if index < 130
            else ((index % 150) - 75.0, (index * 1.37) % 360 - 180)
        )
        if index == 4993:
            latitude, longitude = 10, 179
        if index == 4994:
            latitude, longitude = 10, -179
        if index == 4995:
            latitude, longitude = 90, 180
        if index == 4997:
            latitude, longitude = None, None
        if index == 4998:
            latitude, longitude = 91, 0
        name = f"Synthetic Pines {index:04}"
        session.add(
            Campground(
                id=identifier,
                provider_id=provider,
                recreation_area_id="area",
                name=name,
                latitude=latitude,
                longitude=longitude,
                state="CA",
                country="US",
                enabled=True,
                reservable=True,
            )
        )
        session.add(
            Search(
                id=f"Camp/{provider}/area/{identifier}",
                entity_type="Campground",
                provider_id=provider,
                provider_name=f"Fixture {provider}",
                recreation_area_id="area",
                recreation_area_name="Synthetic Area",
                campground_id=identifier,
                campground_name=name,
                state="CA",
                country="US",
                latitude=latitude,
                longitude=longitude,
                has_electric=index % 2 == 0,
                pets_allowed=True,
                max_rv_length=30,
            )
        )
    session.add(
        Search(
            id="excluded",
            entity_type="RecreationArea",
            provider_id=1,
            provider_name="Fixture 1",
            recreation_area_id="area",
            recreation_area_name="Excluded Control",
            state="CO",
            latitude=40,
            longitude=-105,
        )
    )
    await session.commit()


def test_maps_browser(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Serve a temporary catalog and exercise real MapLibre GL JS and HTTP in Chromium."""
    root = Path(__file__).resolve().parents[5]
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'maps.db'}")
    maker = async_sessionmaker(engine, expire_on_commit=False)

    async def setup() -> None:
        """Create the fixture-only schema and catalog."""
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        async with maker() as session:
            await _seed(session)

    async def session_override() -> AsyncIterator[AsyncSession]:
        """Keep all HTTP requests isolated from any operator database."""
        async with maker() as session:
            yield session

    asyncio.run(setup())
    previous = app.dependency_overrides.get(db.yield_session)
    app.dependency_overrides[db.yield_session] = session_override
    monkeypatch.setattr(backend_config, "auth_mode", AuthMode.NONE)
    monkeypatch.setattr(backend_config, "invite_only", False)
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]
    server = uvicorn.Server(
        uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning")
    )
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    try:
        for _ in range(100):
            try:
                if httpx.get(f"http://127.0.0.1:{port}/api/health").is_success:
                    break
            except httpx.HTTPError:
                pass
            time.sleep(0.1)
        subprocess.run(
            ["pnpm", "exec", "tsx", "scripts/verify-maps.ts"],
            cwd=root / "frontend",
            env={**os.environ, "CAMPLY_API_URL": f"http://127.0.0.1:{port}"},
            check=True,
            timeout=180,
        )
    finally:
        server.should_exit = True
        thread.join(timeout=10)
        if previous is not None:
            app.dependency_overrides[db.yield_session] = previous
        else:
            app.dependency_overrides.pop(db.yield_session, None)
        asyncio.run(engine.dispose())
