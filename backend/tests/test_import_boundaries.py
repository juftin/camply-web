"""Exercise architecture contracts against safe copies with deliberate violations."""

import os
import shutil
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

import pytest


@pytest.fixture
def lint_copy(
    tmp_path: Path,
) -> Callable[[dict[str, str]], subprocess.CompletedProcess[str]]:
    """Run real Import Linter contracts without modifying or importing the application."""
    project = Path(__file__).resolve().parents[1]
    shutil.copytree(
        project / "src/camply",
        tmp_path / "camply",
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
    )

    def run(changes: dict[str, str]) -> subprocess.CompletedProcess[str]:
        """Inject synthetic imports and check the actual project configuration."""
        for name, source in changes.items():
            path = tmp_path / "camply" / name
            path.write_text(f'"""Synthetic architecture probe."""\n{source}\n')
        return subprocess.run(
            [
                str(Path(sys.executable).with_name("lint-imports")),
                "--config",
                str(project / "pyproject.toml"),
                "--no-cache",
            ],
            cwd=tmp_path,
            env={**os.environ, "PYTHONPATH": str(tmp_path), "NO_COLOR": "1"},
            text=True,
            capture_output=True,
            timeout=60,
            check=False,
        )

    return run


def test_current_architecture_keeps_contracts(
    lint_copy: Callable[[dict[str, str]], subprocess.CompletedProcess[str]],
) -> None:
    """Current source, including guarded integrations, satisfies every contract."""
    result = lint_copy({})
    assert result.returncode == 0, result.stdout + result.stderr


def test_source_directories_are_packages() -> None:
    """Require package markers so Import Linter does not silently skip source directories."""
    package = Path(__file__).resolve().parents[1] / "src/camply"
    for source in package.rglob("*.py"):
        assert (source.parent / "__init__.py").is_file(), source.parent


@pytest.mark.parametrize(
    ("changes", "contract"),
    [
        ({"db/probe.py": "import camply.providers.dto"}, "Component dependency layers"),
        (
            {"providers/probe.py": "import camply.server.config"},
            "Component dependency layers",
        ),
        (
            {"server/probe.py": "import camply.worker.config"},
            "Component dependency layers",
        ),
        (
            {"worker/probe.py": "import camply.server.config"},
            "Component dependency layers",
        ),
        ({"db/probe.py": "import fastapi"}, "Base dependencies stay optional-free"),
        (
            {"db/migrations/probe.py": "import fastapi"},
            "Base dependencies stay optional-free",
        ),
        (
            {"db/migrations/versions/probe.py": "import fastapi"},
            "Base dependencies stay optional-free",
        ),
        (
            {"providers/probe.py": "import celery"},
            "Base dependencies stay optional-free",
        ),
        (
            {"providers/probe.py": "import redis"},
            "Base dependencies stay optional-free",
        ),
        ({"db/probe.py": "import psycopg"}, "Base dependencies stay optional-free"),
        ({"db/probe.py": "import sentry_sdk"}, "Base dependencies stay optional-free"),
        ({"worker/probe.py": "import fastapi"}, "Workers avoid server dependencies"),
        (
            {"worker/probe.py": "import sentry_sdk"},
            "Sentry access uses runtime initialization",
        ),
        (
            {"server/probe.py": "import sentry_sdk"},
            "Sentry access uses runtime initialization",
        ),
        (
            {"server/probe.py": "import celery"},
            "Server broker access uses its guarded gateway",
        ),
        ({"__init__.py": "import camply.providers"}, "Package root stays lightweight"),
        ({"__init__.py": "import fastapi"}, "Base dependencies stay optional-free"),
        ({"probe.py": "import httpx"}, "Component dependency layers"),
    ],
)
def test_forbidden_imports_break_contracts(
    lint_copy: Callable[[dict[str, str]], subprocess.CompletedProcess[str]],
    changes: dict[str, str],
    contract: str,
) -> None:
    """Reject upward, cross-runtime, root bootstrap, and optional-dependency leaks."""
    result = lint_copy(changes)
    output = " ".join((result.stdout + result.stderr).split())
    assert result.returncode == 1, output
    assert f"{contract} BROKEN" in output, output


def test_unused_gateway_exceptions_fail(
    lint_copy: Callable[[dict[str, str]], subprocess.CompletedProcess[str]],
) -> None:
    """Fail stale exceptions instead of quietly preserving an unnecessary allowance."""
    result = lint_copy({"server/services/operations.py": ""})
    assert result.returncode == 1, result.stdout + result.stderr
    assert "No matches for ignored import" in result.stdout
