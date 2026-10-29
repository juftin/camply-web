"""Exercise independently installed runtime extras without brokers or live services."""

from collections.abc import Callable

import pytest

from .conftest import Installation


def test_server_only_routes_and_operations(
    install: Callable[[str], Installation],
) -> None:
    """Serve SQLite routes and preserve authorization when distributed support is absent."""
    install("server").run('''
        import asyncio
        import importlib.util
        import socket
        import sys
        from unittest.mock import patch
        import httpx
        from camply.db.config import db
        from camply.db.models import Base

        assert all(importlib.util.find_spec(name) is None for name in ('celery', 'redis', 'psycopg', 'sentry_sdk', 'pytest'))

        async def exercise():
            engine = db.create_async_engine()
            async with engine.begin() as connection:
                await connection.run_sync(Base.metadata.create_all)
            from camply.server.app import app
            from camply.server.auth import resolve_current_user
            from fastapi import HTTPException
            assert '/api/admin/operations' in app.openapi()['paths']
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://test') as client:
                assert (await client.get('/api/ping')).status_code == 200
                assert (await client.get('/api/providers')).status_code == 200
                overview = await client.get('/api/admin/operations')
                assert overview.status_code == 200, overview.text
                assert overview.json()['inspection_available'] is False
                assert overview.json()['broker_connected'] is False
                tasks = await client.get('/api/admin/operations/tasks')
                assert tasks.status_code == 200 and tasks.json()['available'] is False
                for method, path in (('GET', '/api/admin/operations/tasks/synthetic-task'), ('POST', '/api/admin/operations/sync-providers')):
                    response = await client.request(method, path)
                    assert response.status_code == 503, response.text
                    assert 'camply[distributed]' in response.text

                def unauthorized():
                    """Reject authentication before optional operations are inspected."""
                    raise HTTPException(status_code=401, detail='Synthetic unauthenticated request')

                app.dependency_overrides[resolve_current_user] = unauthorized
                assert (await client.get('/api/admin/operations/tasks/synthetic-task')).status_code == 401
                assert (await client.post('/api/admin/operations/sync-providers')).status_code == 401
                app.dependency_overrides.clear()
            await engine.dispose()

        with patch.object(socket.socket, 'connect', side_effect=AssertionError('Unexpected network connection')):
            asyncio.run(exercise())
        assert not any(name.startswith('camply.worker') for name in sys.modules)
    ''')


def test_worker_only_registration(install: Callable[[str], Installation]) -> None:
    """Load the exact task registry without importing server code or connecting a broker."""
    install("distributed").run("""
        import importlib.util
        import socket
        import sys
        from unittest.mock import patch

        assert all(importlib.util.find_spec(name) is None for name in ('fastapi', 'uvicorn', 'psycopg', 'sentry_sdk', 'pytest'))
        with patch.object(socket.socket, 'connect', side_effect=AssertionError('Unexpected broker connection')):
            from camply.worker.celery_app import celery_app
            celery_app.loader.import_default_modules()
            tasks = {name for name in celery_app.tasks if name.startswith('camply.')}
            assert tasks == {
                'camply.search.schedule_checks',
                'camply.search.check_campsite_availability',
                'camply.catalog.sync_all_providers',
                'camply.catalog.sync_provider_catalog',
                'camply.notifications.send_pushover_notification',
            }
            assert celery_app.conf.beat_schedule['schedule-availability-checks']['task'] == 'camply.search.schedule_checks'
            assert celery_app.conf.beat_schedule['sync-provider-catalogs-daily']['task'] == 'camply.catalog.sync_all_providers'
        assert not any(name.startswith('camply.server') for name in sys.modules)
    """)


def test_missing_optional_entrypoints(install: Callable[[str], Installation]) -> None:
    """Base users receive actionable hints when selecting optional runtime capabilities."""
    install("").run("""
        import importlib
        from camply.db.config import DatabaseConfig, DatabaseDrivers

        for module, extra in (('camply.server.app', 'server'), ('camply.worker.celery_app', 'distributed')):
            try:
                importlib.import_module(module)
            except RuntimeError as error:
                assert f'camply[{extra}]' in str(error), str(error)
            else:
                raise AssertionError(f'{module} unexpectedly imported without {extra}')
        try:
            DatabaseConfig(DRIVERNAME=DatabaseDrivers.POSTGRES, HOST='localhost').create_async_engine()
        except RuntimeError as error:
            assert 'camply[postgres]' in str(error), str(error)
        else:
            raise AssertionError('PostgreSQL did not require its extra')
    """)


def test_postgres_driver_without_other_runtimes(
    install: Callable[[str], Installation],
) -> None:
    """Construct a PostgreSQL engine without opening a database connection."""
    install("postgres").run("""
        import asyncio
        import importlib.util
        import socket
        from unittest.mock import patch
        from camply.db.config import DatabaseConfig, DatabaseDrivers

        assert all(importlib.util.find_spec(name) is None for name in ('fastapi', 'celery', 'sentry_sdk'))
        with patch.object(socket.socket, 'connect', side_effect=AssertionError('Unexpected database connection')):
            engine = DatabaseConfig(DRIVERNAME=DatabaseDrivers.POSTGRES, HOST='localhost').create_async_engine()
            assert engine.dialect.driver == 'psycopg'
            asyncio.run(engine.dispose())
    """)


@pytest.mark.parametrize("runtime", ["server", "distributed"])
def test_configured_sentry_requires_extra(
    install: Callable[[str], Installation], runtime: str
) -> None:
    """Only configured error reporting requires the independently selected Sentry SDK."""
    module = "camply.server.app" if runtime == "server" else "camply.worker.celery_app"
    install(runtime).run(
        f"""
        import importlib
        try:
            importlib.import_module({module!r})
        except RuntimeError as error:
            assert 'camply[sentry]' in str(error), str(error)
        else:
            raise AssertionError('Configured Sentry did not require its extra')
        """,
        settings={"CAMPLY_SENTRY_DSN": "https://synthetic@example.invalid/1"},
    )


@pytest.mark.parametrize("runtime", ["server", "distributed"])
def test_sentry_initialization_is_independent(
    install: Callable[[str], Installation], runtime: str
) -> None:
    """Each runtime initializes its own Sentry integration using a mocked SDK transport."""
    module = "camply.server.app" if runtime == "server" else "camply.worker.celery_app"
    integration = "FastApiIntegration" if runtime == "server" else "CeleryIntegration"
    opposing = "celery" if runtime == "server" else "fastapi"
    install(f"{runtime},sentry").run(
        f"""
        import importlib
        import importlib.util
        from unittest.mock import patch
        assert importlib.util.find_spec({opposing!r}) is None
        with patch('sentry_sdk.init') as initialize:
            importlib.import_module({module!r})
        initialize.assert_called_once()
        assert any(type(value).__name__ == {integration!r} for value in initialize.call_args.kwargs['integrations'])
        assert initialize.call_args.kwargs['dsn'] == 'https://synthetic@example.invalid/1'
        """,
        settings={"CAMPLY_SENTRY_DSN": "https://synthetic@example.invalid/1"},
    )
