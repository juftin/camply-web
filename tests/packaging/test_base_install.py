"""Verify that the base distribution supports providers and installed SQLite resources."""

from collections.abc import Callable

from .conftest import Installation


def test_base_imports_and_metadata(install: Callable[[str], Installation]) -> None:
    """Base imports neither install optional runtimes nor bootstrap their applications."""
    install("").run("""
        import importlib.metadata as metadata
        import importlib.util
        import sys
        from pathlib import Path
        import camply
        from camply import __about__
        from camply.db.config import db
        from camply.providers import PROVIDERS

        for module in ('fastapi', 'uvicorn', 'celery', 'redis', 'psycopg', 'sentry_sdk', 'pytest', 'importlinter', 'grimp'):
            assert importlib.util.find_spec(module) is None, module
        assert not any(name.startswith(('camply.server', 'camply.worker')) for name in sys.modules)
        distribution = metadata.distribution('camply')
        assert distribution.metadata['Requires-Python'] == '>=3.11'
        assert set(distribution.metadata.get_all('Provides-Extra')) == {'server', 'distributed', 'postgres', 'sentry'}
        assert __about__.__version__ == distribution.version
        assert Path(camply.__file__).with_name('py.typed').is_file()
        assert sorted(PROVIDERS) == list(range(1, 12))
        assert db.DRIVERNAME.value == 'sqlite+aiosqlite'
        scripts = {entry.name: entry.value for entry in distribution.entry_points if entry.group == 'console_scripts'}
        assert scripts['populate-database'] == 'camply.providers.cli:populate_database'
        assert scripts['camply'] == 'camply.cli.main:cli'
    """)


def test_cli_version_is_offline(install: Callable[[str], Installation]) -> None:
    """The base ``camply`` entry point reports its version without optional runtimes."""
    install("").run("""
        import importlib.metadata as metadata
        import subprocess
        import sys
        from pathlib import Path
        result = subprocess.run([str(Path(sys.executable).with_name('camply')), '--version'],
                                check=True, capture_output=True, text=True)
        assert result.stdout == f"camply, version {metadata.version('camply')}\\n"
        result = subprocess.run([sys.executable, '-c', 'import sys, camply.cli.main; print(sorted(m for m in sys.modules if m.startswith(("camply.server", "camply.worker", "camply.providers", "camply.db"))))'],
                                check=True, capture_output=True, text=True)
        assert result.stdout == '[]\\n'
    """)


def test_population_help_is_offline(install: Callable[[str], Installation]) -> None:
    """The retained population entry point lists its flags without a provider call."""
    install("").run("""
        import subprocess
        import sys
        from pathlib import Path
        result = subprocess.run([str(Path(sys.executable).with_name('populate-database')), '--help'],
                                check=True, capture_output=True, text=True)
        assert '--provider-id' in result.stdout
        assert 'all' in result.stdout
        assert 'ReserveCalifornia' in result.stdout
    """)


def test_frontend_serve_finds_assets_without_server(
    install: Callable[[str], Installation],
) -> None:
    """Base installs render Nginx configuration using their own packaged assets."""
    install("").run(
        """
        import json
        import sys
        from pathlib import Path
        from unittest.mock import patch
        import camply
        from camply.cli.main import cli
        from click.testing import CliRunner

        expected = (Path(camply.__file__).parent / 'server' / 'static').resolve()

        def execute(executable: str, args: list[str]) -> None:
            '''Check rendered configuration before replacing the process.'''
            assert executable == '/synthetic/nginx'
            config = Path(args[args.index('-c') + 1])
            server = config.with_name('server.conf').read_text()
            assert 'root ' + json.dumps(str(expected), ensure_ascii=False) + ';' in server
            assert (expected / 'index.html').is_file()
            assert (expected / 'assets').is_dir()
            assert 'try_files $uri $uri/ /index.html;' in server
            assert 'proxy_pass "http://synthetic-api.invalid:9000";' in server
            assert 'proxy_ssl_server_name on;' in server
            raise SystemExit(0)

        with patch('shutil.which', return_value='/synthetic/nginx'), patch('os.execv', side_effect=execute):
            result = CliRunner().invoke(cli, ['serve', 'frontend'])
        assert result.exit_code == 0, result.output
        assert result.output == ''
        assert not any(name.startswith(('camply.server', 'camply.worker', 'camply.providers', 'camply.db')) for name in sys.modules)
    """,
        settings={"CAMPLY_BACKEND_URL": "http://synthetic-api.invalid:9000"},
    )


def test_installed_migrations_preserve_history(
    install: Callable[[str], Installation],
) -> None:
    """Upgrade fresh and earlier-revision SQLite files using wheel-owned resources."""
    install("").run("""
        import asyncio
        from pathlib import Path
        import sqlalchemy as sa
        from alembic import command
        from alembic.script import ScriptDirectory
        from camply.db.config import DatabaseConfig
        from camply.db.migration import get_alembic_config

        for scenario in ('fresh', 'earlier'):
            path = Path.cwd() / f'{scenario}.sqlite'
            path.unlink(missing_ok=True)
            config = get_alembic_config(DatabaseConfig(HOST=f'/{path}'))
            scripts = ScriptDirectory.from_config(config)
            assert len(scripts.get_heads()) == 1
            assert Path(scripts.dir, 'env.py').is_file()
            assert Path(scripts.dir, 'script.py.mako').is_file()
            if scenario == 'earlier':
                command.upgrade(config, '067d9d721253')
                with sa.create_engine(f'sqlite:///{path}').begin() as connection:
                    connection.execute(sa.text("INSERT INTO providers (id, name, url, enabled) VALUES (9001, 'Synthetic Provider', 'https://example.invalid', 1)"))
            command.upgrade(config, 'head')
            with sa.create_engine(f'sqlite:///{path}').connect() as connection:
                assert connection.execute(sa.text('SELECT version_num FROM alembic_version')).scalar_one() == scripts.get_current_head()
                if scenario == 'earlier':
                    assert connection.execute(sa.text('SELECT name FROM providers WHERE id=9001')).scalar_one() == 'Synthetic Provider'
    """)


def test_runtime_help_and_missing_dependencies(
    install: Callable[[str], Installation],
) -> None:
    """Base installs expose launcher help and useful errors without runtime imports."""
    install("").run("""
        import os
        import sys
        from unittest.mock import patch
        from click.testing import CliRunner
        from camply.cli.main import cli

        for command, hint in (
            (['serve'], 'camply[server]'),
            (['serve', 'frontend'], 'Nginx'),
            (['serve', 'backend'], 'camply[server]'),
            (['serve', 'worker'], 'camply[distributed]'),
            (['serve', 'beat'], 'camply[distributed]'),
            (['serve', 'healthcheck', 'worker'], 'camply[distributed]'),
        ):
            help_result = CliRunner().invoke(cli, [*command, '--help'])
            assert help_result.exit_code == 0, help_result.output
            unrelated = None if command == ['serve', 'frontend'] else '/unrelated/bin/runtime'
            with patch.dict(os.environ, {'PATH': ''}), patch('shutil.which', return_value=unrelated):
                result = CliRunner().invoke(cli, command)
            assert result.exit_code == 1, result.output
            assert hint in result.stderr, result.stderr
        assert not any(name.startswith(('camply.server', 'camply.worker', 'camply.db', 'camply.providers')) for name in sys.modules)
    """)


def test_healthchecks_without_optional_runtimes(
    install: Callable[[str], Installation],
) -> None:
    """Base installs can probe HTTP and beat state without bootstrapping any service."""
    install("").run("""
        import json
        import os
        import sys
        import time
        from contextlib import nullcontext
        from pathlib import Path
        from unittest.mock import patch
        import httpx
        from click.testing import CliRunner
        from camply.cli.main import cli

        for role in ([], ['backend'], ['frontend'], ['worker'], ['beat']):
            result = CliRunner().invoke(cli, ['serve', 'healthcheck', *role, '--help'])
            assert result.exit_code == 0, result.output
        for role in ([], ['backend'], ['frontend']):
            with patch('httpx.stream', return_value=nullcontext(httpx.Response(200))):
                result = CliRunner().invoke(cli, ['serve', 'healthcheck', *role])
            assert result.exit_code == 0, result.output
        path = Path.cwd() / 'synthetic-beat.json'
        path.write_text(json.dumps({'pid': os.getpid(), 'timestamp': time.time()}))
        result = CliRunner().invoke(cli, ['serve', 'healthcheck', 'beat', '--heartbeat-file', str(path)])
        assert result.exit_code == (1 if os.name == 'nt' else 0), result.output
        path.unlink()
        assert not any(name.startswith(('camply.server', 'camply.worker', 'camply.providers', 'camply.db')) for name in sys.modules)
    """)
