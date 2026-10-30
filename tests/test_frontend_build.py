"""Protect complete artifact builds from stale assets and missing prerequisites."""

from __future__ import annotations

import importlib.util
import json
import shutil
import subprocess
from pathlib import Path
from typing import Any
from unittest.mock import Mock

import pytest

spec = importlib.util.spec_from_file_location(
    "camply_build", Path(__file__).resolve().parents[1] / "hatch_build.py"
)
assert spec is not None and spec.loader is not None
hook_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(hook_module)


@pytest.fixture
def project(tmp_path: Path) -> Path:
    """Supply synthetic source inputs without copying dependencies or actual secrets."""
    for name in hook_module.ROOT_INPUTS:
        (tmp_path / name).write_text("synthetic input")
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "camply"\nversion = "1.2.3"\n'
    )
    (tmp_path / "package.json").write_text('{"version": "1.2.3"}')
    frontend = tmp_path / "src/frontend"
    frontend.mkdir(parents=True)
    (frontend / "main.tsx").write_text("synthetic frontend")
    return tmp_path


def build_hook(project: Path, target: str = "wheel") -> Any:
    """Create a hook independent of Hatch's unrelated metadata machinery."""
    return hook_module.FrontendBuildHook(str(project), {}, None, None, "dist", target)


def prepare(project: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Simulate compilation while exercising real manifest and archive mappings."""
    monkeypatch.setattr(hook_module.shutil, "which", lambda name: f"/synthetic/{name}")

    def compile_assets(*args: Any, **kwargs: Any) -> None:
        """Write representative build outputs during the synthetic build command."""
        assert kwargs["env"]["CAMPLY_STANDALONE_BUILD"] == "1"
        assert kwargs["env"]["VITE_API_URL"] == "/api"
        assert "VITE_UNSUPPORTED_PRIVATE" not in kwargs["env"]
        if args[0][1:] == ["install", "--frozen-lockfile"]:
            return
        assert args[0][1:] == ["run", "build"]
        if args[0][1:] == ["run", "build"]:
            assets = project / "build/frontend/assets"
            assets.mkdir(parents=True)
            (assets / "map-worker.js").write_text("synthetic worker")
            (project / "build/frontend/index.html").write_text("synthetic page")

    monkeypatch.setattr(hook_module.subprocess, "run", compile_assets)
    build_hook(project).initialize("standard", {"force_include": {}})


def test_editable_does_not_probe_javascript(
    project: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Editable installs remain usable on Python-only development environments."""
    probe = Mock(side_effect=AssertionError("JavaScript must not be inspected"))
    monkeypatch.setattr(hook_module.shutil, "which", probe)
    build_hook(project).initialize("editable", {})
    probe.assert_not_called()


def test_checkout_requires_frontend_toolchain(
    project: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A standard checkout wheel cannot silently omit the application frontend."""
    monkeypatch.setattr(hook_module.shutil, "which", lambda name: None)
    with pytest.raises(RuntimeError, match=r"Node 24.*pinned pnpm"):
        build_hook(project).initialize("standard", {"force_include": {}})


@pytest.mark.parametrize("command", ["install", "run"])
def test_frozen_install_or_compile_failure(
    project: Path, monkeypatch: pytest.MonkeyPatch, command: str
) -> None:
    """Failed dependency resolution or compilation never publishes stale resources."""
    monkeypatch.setattr(hook_module.shutil, "which", lambda name: f"/synthetic/{name}")

    def fail(args: list[str], **kwargs: Any) -> None:
        """Fail the selected frontend operation with a normal subprocess error."""
        if args[1] == command:
            raise subprocess.CalledProcessError(1, args)

    monkeypatch.setattr(hook_module.subprocess, "run", fail)
    with pytest.raises(RuntimeError, match="Frozen frontend installation/build failed"):
        build_hook(project).initialize("standard", {"force_include": {}})
    assert not (project / "build/frontend-manifest.json").exists()


def test_checkout_always_rebuilds_and_maps_without_staging(
    project: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Even prepared checkout output requires a fresh install/build on every invocation."""
    prepare(project, monkeypatch)
    stale = project / "build/frontend/assets/stale.js"
    stale.write_text("obsolete")
    prepare(project, monkeypatch)
    assert not stale.exists()
    assert not (project / "src/camply/server/static").exists()
    manifest = json.loads((project / "build/frontend-manifest.json").read_text())
    assert set(manifest["assets"]) == {"index.html", "assets/map-worker.js"}


@pytest.mark.parametrize(
    "corruption", ["none", "delete", "change", "extra", "input", "metadata", "path"]
)
def test_archive_integrity_without_javascript(
    project: Path, monkeypatch: pytest.MonkeyPatch, corruption: str
) -> None:
    """Prepared archives reuse exact inputs/assets and reject any modified inventory."""
    prepare(project, monkeypatch)
    assets = project / "src/camply/server/static"
    assets.parent.mkdir(parents=True)
    shutil.copytree(project / "build/frontend", assets)
    (project / "PKG-INFO").write_text("Name: camply\nVersion: 1.2.3\n")
    if corruption == "delete":
        (assets / "index.html").unlink()
    elif corruption == "change":
        (assets / "index.html").write_text("corrupted")
    elif corruption == "extra":
        (assets / "unexpected.js").write_text("unexpected")
    elif corruption == "input":
        (project / "src/frontend/main.tsx").write_text("changed source")
    elif corruption == "metadata":
        (project / "package.json").write_text('{"version": "9.9.9"}')
    elif corruption == "path":
        path = project / "build/frontend-manifest.json"
        manifest = json.loads(path.read_text())
        manifest["assets"]["../escape"] = "invalid"
        path.write_text(json.dumps(manifest))
    monkeypatch.setattr(
        hook_module.shutil,
        "which",
        Mock(side_effect=AssertionError("Archive must not probe Node")),
    )
    mapping: dict[str, Any] = {"force_include": {}}
    if corruption == "none":
        build_hook(project).initialize("standard", mapping)
        assert mapping["force_include"][str(assets)] == "camply/server/static"
    else:
        with pytest.raises(RuntimeError, match="fresh sdist"):
            build_hook(project).initialize("standard", mapping)
        assert not mapping["force_include"]


def test_manifest_records_only_supported_public_settings(
    project: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Public build options affect freshness without serializing unrelated environment."""
    monkeypatch.setenv(
        "VITE_MAP_TILE_URL", "https://tiles.example.invalid/{z}/{x}/{y}.png"
    )
    monkeypatch.setenv("VITE_UNSUPPORTED_PRIVATE", "synthetic-private-option")
    monkeypatch.setenv("VITE_API_URL", "https://wrong.example.invalid/api")
    prepare(project, monkeypatch)
    manifest = json.loads((project / "build/frontend-manifest.json").read_text())
    assert manifest["settings"] == {
        "VITE_MAP_TILE_URL": "https://tiles.example.invalid/{z}/{x}/{y}.png"
    }
    assert "synthetic-private-option" not in json.dumps(manifest)
    assert "wrong.example.invalid" not in json.dumps(manifest)


def test_ignored_frontend_files_do_not_change_archive_inputs(project: Path) -> None:
    """Digest exactly the source set Hatch includes rather than ignored machine output."""
    (project / ".gitignore").write_text(".DS_Store\n*.log\ntmp/\n")
    before = hook_module.input_digest(project, {})
    for name in (".DS_Store", "debug.log", "tmp/ignored.ts"):
        path = project / "src/frontend" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("synthetic ignored output")
    assert hook_module.input_digest(project, {}) == before


@pytest.mark.parametrize("name", [".env", ".env.production", ".dev.vars.local"])
def test_environment_files_rejected_before_frontend_build(
    project: Path, monkeypatch: pytest.MonkeyPatch, name: str
) -> None:
    """Vite public copying cannot put environment files into published assets."""
    public = project / "src/frontend/public"
    public.mkdir()
    (public / name).write_text("synthetic environment fixture")
    runner = Mock(side_effect=AssertionError("Build must not start"))
    monkeypatch.setattr(hook_module.subprocess, "run", runner)
    with pytest.raises(RuntimeError, match="public assets contain an environment file"):
        build_hook(project).initialize("standard", {"force_include": {}})
    runner.assert_not_called()


def test_inventory_rejects_emitted_environment_files(
    project: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Prepared output validation rejects environment files before hashing their bytes."""
    prepare(project, monkeypatch)
    assets = project / "build/frontend"
    (assets / ".env").write_text("synthetic emitted fixture")
    with pytest.raises(RuntimeError, match="must not contain environment files"):
        hook_module.inventory(assets)
