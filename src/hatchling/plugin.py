"""Build complete application archives without modifying Python source resources."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import tomllib
from email.parser import Parser
from pathlib import Path
from typing import Any

from hatchling.builders.hooks.plugin.interface import BuildHookInterface
from hatchling.builders.sdist import SdistBuilder

RECIPE = "camply-frontend-v1"
"""Change this identity when the frontend build procedure changes."""
PUBLIC_SETTINGS = (
    "VITE_ENABLE_COMMUNITY_PAGES",
    "VITE_MAP_TILE_URL",
    "VITE_MAP_ATTRIBUTION_TEXT",
    "VITE_MAP_ATTRIBUTION_URL",
    "VITE_MAP_MAX_NATIVE_ZOOM",
)
"""Explicit public settings supported by application packaging."""
ROOT_INPUTS = (
    "pyproject.toml",
    "package.json",
    "pnpm-lock.yaml",
    "pnpm-workspace.yaml",
    ".node-version",
    "vite.config.ts",
    "src/frontend/tailwind.config.js",
    "src/hatchling/plugin.py",
)
"""Root configuration whose contents determine the prepared frontend."""


def digest(path: Path) -> str:
    """Hash one build input or emitted asset by its bytes."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def inventory(directory: Path) -> dict[str, str]:
    """Enumerate every emitted file, rejecting links outside the asset directory."""
    files: dict[str, str] = {}
    for path in sorted(directory.rglob("*")):
        if path.name.startswith((".env", ".dev.vars")):
            raise RuntimeError(
                f"Frontend assets must not contain environment files: {path.name}"
            )
        if path.is_symlink():
            raise RuntimeError(f"Frontend resources must not contain symlinks: {path}")
        if path.is_file():
            files[path.relative_to(directory).as_posix()] = digest(path)
    if "index.html" not in files or not any(
        name.startswith("assets/") for name in files
    ):
        raise RuntimeError("Frontend build must produce index.html and emitted assets.")
    return files


def input_digest(root: Path, settings: dict[str, str]) -> str:
    """Identify exact frontend source, package configuration and public build options."""
    paths = [root / name for name in ROOT_INPUTS]
    paths.extend(root.glob("tsconfig*.json"))
    paths.extend(
        Path(item.path)
        for item in SdistBuilder(str(root)).recurse_selected_project_files()
        if item.relative_path.startswith("src/frontend/")
        and not Path(item.relative_path).name.startswith((".env", ".dev.vars"))
    )
    inputs = {
        path.relative_to(root).as_posix(): digest(path) for path in sorted(set(paths))
    }
    return hashlib.sha256(
        json.dumps(
            {"recipe": RECIPE, "settings": settings, "inputs": inputs}, sort_keys=True
        ).encode()
    ).hexdigest()


class FrontendBuildHook(BuildHookInterface):
    """Compile checkout sources, or validate and reuse prepared source-archive assets."""

    PLUGIN_NAME = "custom"

    def initialize(self, version: str, build_data: dict[str, Any]) -> None:
        """Map complete UI resources into standard wheel and source distributions."""
        if self.target_name == "wheel" and version != "standard":
            return
        root = Path(self.root)
        manifest_path = root / "build/frontend-manifest.json"
        if (root / "PKG-INFO").is_file():
            assets = root / "src/camply/server/static"
            self.validate_archive(root, assets, manifest_path)
        else:
            assets = root / "build/frontend"
            self.build_frontend(root, assets, manifest_path)
        destination = (
            "camply/server/static"
            if self.target_name == "wheel"
            else "src/camply/server/static"
        )
        build_data["force_include"][str(assets)] = destination
        if self.target_name == "sdist":
            build_data["force_include"][str(manifest_path)] = (
                "build/frontend-manifest.json"
            )

    def package_versions(self, root: Path) -> dict[str, str]:
        """Read both version stamps used by the frontend and distribution."""
        with (root / "pyproject.toml").open("rb") as stream:
            python_version = tomllib.load(stream)["project"]["version"]
        return {
            "python": python_version,
            "frontend": json.loads((root / "package.json").read_text())["version"],
        }

    def build_frontend(self, root: Path, assets: Path, manifest_path: Path) -> None:
        """Install frozen frontend dependencies and compile a same-origin application."""
        for path in (root / "src/frontend/public").rglob("*"):
            if path.name.startswith((".env", ".dev.vars")):
                raise RuntimeError(
                    "Frontend public assets contain an environment file. Remove it before building a distribution."
                )
        pnpm = shutil.which("pnpm")
        if pnpm is None or shutil.which("node") is None:
            raise RuntimeError(
                "Complete checkout builds require Node 24 and the pinned pnpm. Install them and retry."
            )
        settings = {
            key: os.environ[key] for key in PUBLIC_SETTINGS if key in os.environ
        }
        env = {
            key: value
            for key, value in os.environ.items()
            if not key.startswith("VITE_")
        }
        env.update(settings, CAMPLY_STANDALONE_BUILD="1", VITE_API_URL="/api")
        if assets.exists():
            shutil.rmtree(assets)
        manifest_path.unlink(missing_ok=True)
        try:
            subprocess.run(
                [pnpm, "install", "--frozen-lockfile"], cwd=root, env=env, check=True
            )
            subprocess.run([pnpm, "run", "build"], cwd=root, env=env, check=True)
        except subprocess.CalledProcessError as error:
            raise RuntimeError(
                "Frozen frontend installation/build failed; fix the reported error and rebuild the complete checkout."
            ) from error
        manifest = {
            "schema": 1,
            "recipe": RECIPE,
            "versions": self.package_versions(root),
            "settings": settings,
            "inputs": input_digest(root, settings),
            "assets": inventory(assets),
        }
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text(json.dumps(manifest, sort_keys=True, indent=2) + "\n")

    def validate_archive(self, root: Path, assets: Path, manifest_path: Path) -> None:
        """Reject changed or incomplete prepared archives without invoking JavaScript."""
        try:
            manifest = json.loads(manifest_path.read_text())
            settings = manifest["settings"]
            metadata = Parser().parsestr((root / "PKG-INFO").read_text())
            versions = self.package_versions(root)
            valid = (
                metadata["Name"] == "camply"
                and metadata["Version"] == versions["python"]
                and manifest["schema"] == 1
                and manifest["recipe"] == RECIPE
                and isinstance(settings, dict)
                and set(settings) <= set(PUBLIC_SETTINGS)
                and all(isinstance(value, str) for value in settings.values())
                and manifest["versions"] == versions
                and manifest["inputs"] == input_digest(root, settings)
                and manifest["assets"] == inventory(assets)
            )
            if not valid:
                raise ValueError(
                    "Prepared frontend does not match archive inputs/assets"
                )
        except (OSError, ValueError, KeyError, TypeError, RuntimeError) as error:
            raise RuntimeError(
                "Invalid prepared frontend in source archive. Build a fresh sdist from a complete checkout with Node/pnpm."
            ) from error
