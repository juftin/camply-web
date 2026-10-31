"""Verify independent application roles dispatched by the shared image."""

import os
import subprocess
from pathlib import Path

import pytest


@pytest.mark.parametrize(
    ("command", "skip_migrations", "migrates"),
    [
        (["nginx", "-g", "daemon off;"], False, False),
        (["camply", "serve"], False, False),
        (["camply", "serve", "--port", "9000"], False, False),
        (["camply", "serve", "frontend"], False, False),
        (["camply", "serve", "backend"], False, False),
        (["camply", "serve", "worker"], False, False),
        (["camply", "serve", "beat"], False, False),
        (["gunicorn", "camply.server.app:app"], False, True),
        (["celery", "worker"], True, False),
        (["celery", "beat"], True, False),
    ],
)
def test_role_dispatch(
    tmp_path: Path, command: list[str], skip_migrations: bool, migrates: bool
) -> None:
    """Preserve arguments and directory setup while CLI commands own their migrations."""
    entrypoint = Path(__file__).resolve().parents[1] / "deploy" / "entrypoint.sh"
    executable = tmp_path / "record"
    executable.write_text('#!/bin/sh\nprintf "%s\\n" "$0" "$@" >> "$CALL_LOG"\n')
    executable.chmod(0o755)
    for name in ("python", "nginx", "camply", "gunicorn", "celery"):
        (tmp_path / name).symlink_to(executable)
    log = tmp_path / "calls"
    result = subprocess.run(
        ["bash", str(entrypoint), *command],
        env={
            "PATH": f"{tmp_path}{os.pathsep}{os.defpath}",
            "HOME": str(tmp_path),
            "CALL_LOG": str(log),
            "SKIP_MIGRATIONS": "1" if skip_migrations else "0",
        },
        capture_output=True,
        text=True,
        check=False,
        timeout=10,
    )
    assert result.returncode == 0, result.stderr
    calls = log.read_text().splitlines()
    expected = [str(tmp_path / command[0]), *command[1:]]
    if migrates:
        expected = [str(tmp_path / "python"), "-m", "camply.db.migration", *expected]
    assert calls == expected
    if command[:2] == ["camply", "serve"] and command[2:3] != ["frontend"]:
        assert (tmp_path / ".local/share/camply").is_dir()
