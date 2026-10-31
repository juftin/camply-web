"""Exercise independently installed runtime extras without brokers or live services."""

import sys
from collections.abc import Callable

import pytest

from .conftest import Installation


@pytest.mark.parametrize(
    ("role", "force"),
    [
        ("standalone", False),
        pytest.param(
            "standalone",
            True,
            marks=pytest.mark.skipif(
                sys.platform == "win32", reason="SIGKILL requires Unix"
            ),
        ),
        pytest.param(
            "backend",
            False,
            marks=pytest.mark.skipif(
                sys.platform == "win32", reason="Gunicorn requires Unix"
            ),
        ),
    ],
)
def test_http_cli_serves_and_shuts_down(
    install: Callable[[str], Installation],
    role: str,
    force: bool,
) -> None:
    """HTTP runtimes handle SIGTERM cleanup and standalone receives SIGKILL directly."""
    installation = install("server")
    installation.run(
        f"        role = {role!r}; force = {force!r}\n"
        + """
        import os
        import signal
        import socket
        import sqlite3
        import subprocess
        import sys
        import tempfile
        import time
        from pathlib import Path
        import httpx

        with socket.socket() as listener:
            listener.bind(('127.0.0.1', 0))
            port = listener.getsockname()[1]
        with tempfile.TemporaryFile() as log:
            arguments = ['--port', str(port)] if role == 'standalone' else [
                'backend', '--bind', f'127.0.0.1:{port}', '--workers', '1',
            ]
            process = subprocess.Popen(
                [str(Path(sys.executable).with_name('camply')), 'serve', *arguments],
                stdout=log, stderr=subprocess.STDOUT,
                start_new_session=os.name != 'nt',
            )
            try:
                ready = False
                with httpx.Client(base_url=f'http://127.0.0.1:{port}', timeout=1) as client:
                    for attempt in range(150):
                        if process.poll() is not None:
                            break
                        try:
                            ready = client.get('/api/health').is_success
                        except httpx.TransportError:
                            pass
                        if ready:
                            break
                        time.sleep(0.1)
                    if not ready:
                        log.seek(0)
                        raise AssertionError(log.read().decode())
                    if role == 'standalone':
                        home = client.get('/')
                        assert home.is_success and 'text/html' in home.headers['content-type']
                        assert client.get('/scans/synthetic', headers={'Accept': 'text/html'}).text == home.text
                        assert client.get('/metrics').status_code == 404
                    else:
                        assert client.get('/').status_code == 404
                        assert client.get('/metrics').is_success
                    runtime = 'standalone' if role == 'standalone' else 'distributed'
                    assert client.get('/api/admin/operations').json()['runtime_mode'] == runtime
                    assert client.get('/api/nonexistent').status_code == 404
                with sqlite3.connect(os.environ['CAMPLY_DB_HOST']) as database:
                    assert database.execute('SELECT version_num FROM alembic_version').fetchone()
                health_role = [] if role == 'standalone' else ['backend']
                probe = subprocess.run(
                    [str(Path(sys.executable).with_name('camply')), 'serve', 'healthcheck',
                     *health_role, '--url', f'http://127.0.0.1:{port}/api/health'],
                    check=True, capture_output=True, text=True, timeout=10,
                )
                assert probe.stdout.strip() == 'healthy'
                if force:
                    process.kill()
                else:
                    process.terminate()
                process.wait(timeout=10)
                log.seek(0)
                output = log.read().decode()
                if role == 'standalone' and os.name != 'nt':
                    assert f'Started server process [{process.pid}]' in output, output
                if force:
                    assert process.returncode == -signal.SIGKILL, output
                else:
                    assert 'Application shutdown complete' in output, output
                    if role == 'backend':
                        assert 'Shutting down: Master' in output, output
                with sqlite3.connect(os.environ['CAMPLY_DB_HOST']) as database:
                    assert database.execute('PRAGMA integrity_check').fetchone() == ('ok',)
            finally:
                if os.name != 'nt':
                    try:
                        os.killpg(process.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                if process.poll() is None:
                    process.kill()
                    process.wait(timeout=10)
        """,
        settings={
            "CAMPLY_DB_HOST": str(installation.directory / f"{role}-cli.sqlite"),
            "CAMPLY_RUNTIME_MODE": "distributed",
        },
    )


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
            from camply.worker.scheduler import HealthScheduler
            from celery.beat import PersistentScheduler
            assert issubclass(HealthScheduler, PersistentScheduler)
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


@pytest.mark.parametrize("sync_providers", [False, True])
def test_installed_beat_provider_sync(
    install: Callable[[str], Installation], sync_providers: bool
) -> None:
    """Distributed-only artifacts enqueue the optional sync before replacing the CLI."""
    installation = install("distributed")
    installation.run(
        f"        sync_providers = {sync_providers!r}\n"
        + """
        import sys
        from unittest.mock import Mock, patch
        from click.testing import CliRunner
        from camply.cli.main import cli

        calls = Mock()
        calls.attach_mock(Mock(), 'dispatch')
        calls.attach_mock(Mock(side_effect=SystemExit(0)), 'execute')
        arguments = ['serve', 'beat', '--schedule', '/tmp/synthetic-beat']
        if sync_providers:
            arguments.append('--sync-providers')
        with patch('subprocess.run', calls.dispatch), patch('os.execv', calls.execute):
            result = CliRunner().invoke(cli, arguments)
        assert result.exit_code == 0, result.output
        assert [entry[0] for entry in calls.mock_calls] == (
            ['dispatch', 'execute'] if sync_providers else ['execute']
        )
        if sync_providers:
            calls.dispatch.assert_called_once_with(
                [sys.executable, '-m', 'celery', '-A', 'camply.worker.celery_app',
                 'call', 'camply.catalog.sync_all_providers', '--expires=600'],
                check=True,
            )
        assert calls.execute.call_args.args[0] == sys.executable
        assert calls.execute.call_args.args[1][-2:] == ['--schedule', '/tmp/synthetic-beat']
        assert '--sync-providers' not in calls.execute.call_args.args[1]
        assert not any(name.startswith('camply.server') for name in sys.modules)
        """,
        settings={
            "CAMPLY_BEAT_HEALTH_FILE": str(
                installation.directory / "synthetic-beat.json"
            )
        },
    )


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
