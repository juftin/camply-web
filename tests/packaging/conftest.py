"""Build real artifacts and exercise installations outside the source checkout."""

from __future__ import annotations

import os
import subprocess
import sys
import tarfile
import tempfile
import textwrap
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import pytest

PROJECT = Path(__file__).resolve().parents[2]
"""Python project whose distributable artifacts are under test."""


def clean_environment() -> dict[str, str]:
    """Prevent checkout paths and operator settings from leaking into test installs."""
    return {
        key: value
        for key, value in os.environ.items()
        if key
        in {
            "PATH",
            "HOME",
            "USERPROFILE",
            "SYSTEMROOT",
            "TMPDIR",
            "TMP",
            "TEMP",
            "LANG",
            "LC_ALL",
        }
    }


def run_command(
    args: list[str], *, cwd: Path, env: dict[str, str] | None = None
) -> str:
    """Run a packaging operation with useful diagnostics and a finite deadline."""
    result = subprocess.run(
        args,
        cwd=cwd,
        env=env if env is not None else clean_environment(),
        text=True,
        capture_output=True,
        timeout=240,
        check=False,
    )
    assert result.returncode == 0, (
        f"Command failed: {args}\n{result.stdout}\n{result.stderr}"
    )
    return result.stdout


@dataclass(frozen=True)
class Installation:
    """An installed artifact with no editable source or development dependencies."""

    python: Path
    """Interpreter inside a new uv virtual environment."""
    directory: Path
    """Working directory outside the repository."""

    def run(self, script: str, *, settings: dict[str, str] | None = None) -> str:
        """Execute assertions inside this installation with synthetic settings."""
        env = clean_environment()
        env.update(
            CAMPLY_DB_HOST=f"/{self.directory / 'synthetic.sqlite'}",
            CAMPLY_AUTH_MODE="none",
            CAMPLY_METRICS_PORT="0",
        )
        env.update(settings or {})
        return run_command(
            [str(self.python), "-I", "-c", textwrap.dedent(script)],
            cwd=self.directory,
            env=env,
        )


@pytest.fixture(scope="session")
def artifacts(tmp_path_factory: pytest.TempPathFactory) -> dict[str, Path]:
    """Build a wheel/sdist pair and rebuild the sdist without repository siblings."""
    directory = tmp_path_factory.mktemp("artifacts")
    interpreter = os.environ.get("PACKAGING_PYTHON", "3.14")
    with tempfile.TemporaryDirectory(
        prefix="camply-ignored-inputs-", dir=PROJECT / "src/frontend"
    ) as ignored_directory:
        ignored = Path(ignored_directory)
        (ignored / ".DS_Store").write_text("synthetic operating-system state")
        (ignored / "build.log").write_text("synthetic build log")
        run_command(
            [
                sys.executable,
                "-m",
                "build",
                "--outdir",
                str(directory),
                str(PROJECT),
            ],
            cwd=directory,
        )
    wheels = list(directory.glob("*.whl"))
    sdists = list(directory.glob("*.tar.gz"))
    assert len(wheels) == len(sdists) == 1
    source = directory / "source"
    source.mkdir()
    with tarfile.open(sdists[0]) as archive:
        archive.extractall(source, filter="data")
    roots = list(source.iterdir())
    assert len(roots) == 1
    rebuilt = directory / "rebuilt"
    blocked_tools = directory / "blocked-javascript"
    blocked_tools.mkdir()
    for executable in ("node", "pnpm", "npm"):
        blocker = blocked_tools / executable
        blocker.write_text(
            "#!/bin/sh\necho 'JavaScript invoked during archive rebuild' >&2\nexit 99\n"
        )
        blocker.chmod(0o755)
    archive_environment = clean_environment()
    archive_environment["PATH"] = (
        str(blocked_tools) + os.pathsep + archive_environment["PATH"]
    )
    run_command(
        [
            "uv",
            "build",
            str(roots[0]),
            "--wheel",
            "--python",
            interpreter,
            "--out-dir",
            str(rebuilt),
        ],
        cwd=source,
        env=archive_environment,
    )
    rebuilt_wheels = list(rebuilt.glob("*.whl"))
    assert len(rebuilt_wheels) == 1
    direct = directory / "direct"
    run_command(
        [
            sys.executable,
            "-m",
            "build",
            "--wheel",
            "--outdir",
            str(direct),
            str(PROJECT),
        ],
        cwd=directory,
    )
    direct_wheels = list(direct.glob("*.whl"))
    assert len(direct_wheels) == 1
    return {
        "wheel": wheels[0],
        "sdist-wheel": rebuilt_wheels[0],
        "direct-wheel": direct_wheels[0],
        "sdist": sdists[0],
    }


@pytest.fixture(scope="session", params=["wheel", "sdist-wheel", "direct-wheel"])
def install(
    request: pytest.FixtureRequest,
    artifacts: dict[str, Path],
    tmp_path_factory: pytest.TempPathFactory,
) -> Callable[[str], Installation]:
    """Cache clean installs of each artifact and explicitly selected public extras."""
    cache: dict[str, Installation] = {}

    def create(extras: str = "") -> Installation:
        """Install the chosen wheel with only its declared runtime dependencies."""
        if extras not in cache:
            directory = tmp_path_factory.mktemp(f"installed-{request.param}-{extras}")
            environment = directory / "venv"
            run_command(
                [
                    "uv",
                    "venv",
                    str(environment),
                    "--python",
                    os.environ.get("PACKAGING_PYTHON", "3.14"),
                ],
                cwd=directory,
            )
            python = environment / (
                "Scripts/python.exe" if os.name == "nt" else "bin/python"
            )
            requirement = str(artifacts[request.param]) + (
                f"[{extras}]" if extras else ""
            )
            run_command(
                ["uv", "pip", "install", "--python", str(python), requirement],
                cwd=directory,
            )
            cache[extras] = Installation(python=python, directory=directory)
        return cache[extras]

    return create
