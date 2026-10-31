"""Verify real application resources in independently built distribution formats."""

import subprocess
import sys
import tarfile
import zipfile
from collections.abc import Callable
from pathlib import Path

import pytest

from .conftest import Installation, clean_environment


def test_complete_archive_contents(artifacts: dict[str, Path]) -> None:
    """Every wheel includes prepared UI once, while sdists retain buildable source."""
    for name in ("wheel", "sdist-wheel", "direct-wheel"):
        with zipfile.ZipFile(artifacts[name]) as wheel:
            names = wheel.namelist()
            assert len(names) == len(set(names))
            assert "camply/server/static/index.html" in names
            assert "camply/cli/nginx/nginx.conf" in names
            assert "camply/cli/nginx/server.conf" in names
            assert "camply/server/gunicorn.py" in names
            assert any(
                path.startswith("camply/server/static/assets/")
                and "worker" in path.lower()
                for path in names
            )
            assert not any(
                "node_modules" in path or "src/frontend" in path or "hatchling" in path
                for path in names
            )
    with tarfile.open(artifacts["sdist"]) as archive:
        names = [name.partition("/")[2] for name in archive.getnames()]
        for expected in (
            "src/hatchling/plugin.py",
            "package.json",
            "pnpm-lock.yaml",
            "src/frontend/main.tsx",
            "src/camply/cli/nginx/nginx.conf",
            "src/camply/cli/nginx/server.conf",
            "src/camply/server/static/index.html",
            "build/frontend-manifest.json",
        ):
            assert expected in names
        assert not any(
            "node_modules" in name
            or name.endswith((".tsbuildinfo", ".log", ".DS_Store"))
            for name in names
        )


def test_installed_frontend_and_gunicorn(
    install: Callable[[str], Installation],
) -> None:
    """Installed artifacts serve real built assets, SPA navigation and API errors."""
    install("server").run("""
        import asyncio
        import importlib.resources
        import os
        import re
        import subprocess
        import sys
        from pathlib import Path
        import httpx
        from camply.server.config import RuntimeMode, backend_config
        from camply.server.app import app
        from camply.server.static import attach_frontend

        if os.name != 'nt':
            from camply.server import gunicorn
            assert gunicorn.worker_class == 'uvicorn_worker.UvicornWorker'
            subprocess.run([str(Path(sys.executable).with_name('gunicorn')), '--check-config', '--config', 'python:camply.server.gunicorn', 'camply.server.app:app'], check=True, capture_output=True, text=True)
        static = importlib.resources.files('camply.server').joinpath('static')
        assert static.joinpath('index.html').is_file()
        backend_config.runtime_mode = RuntimeMode.STANDALONE
        attach_frontend(app, Path(str(static)))

        async def exercise():
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://test') as client:
                home = await client.get('/')
                assert home.status_code == 200
                assets = re.findall(r'(?:src|href)="(/assets/[^\"]+)"', home.text)
                assert assets, home.text
                for path in assets:
                    assert (await client.get(path)).status_code == 200, path
                workers = [path.name for path in static.joinpath('assets').iterdir() if 'worker' in path.name.lower()]
                assert workers
                for worker in workers:
                    assert (await client.get('/assets/' + worker)).status_code == 200
                assert (await client.get('/scans/synthetic', headers={'accept': 'text/html'})).text == home.text
                assert (await client.get('/api/nonexistent')).status_code == 404
        asyncio.run(exercise())
    """)


@pytest.mark.parametrize("damage", ["missing-asset", "changed-asset", "changed-input"])
def test_damaged_real_sdist_fails(
    artifacts: dict[str, Path], tmp_path: Path, damage: str
) -> None:
    """Incomplete or edited real source archives cannot produce apparently valid wheels."""
    with tarfile.open(artifacts["sdist"]) as archive:
        archive.extractall(tmp_path, filter="data")
    root = next(path for path in tmp_path.iterdir() if path.is_dir())
    if damage == "missing-asset":
        (root / "src/camply/server/static/index.html").unlink()
    elif damage == "changed-asset":
        (root / "src/camply/server/static/index.html").write_text("corrupted asset")
    else:
        (root / "src/frontend/main.tsx").write_text("changed source input")
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "build",
            "--wheel",
            "--no-isolation",
            "--outdir",
            str(tmp_path / "dist"),
            str(root),
        ],
        cwd=tmp_path,
        env=clean_environment(),
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode != 0
    assert (
        "Build a fresh sdist from a complete checkout" in result.stdout + result.stderr
    )
    assert not list((tmp_path / "dist").glob("*.whl"))
