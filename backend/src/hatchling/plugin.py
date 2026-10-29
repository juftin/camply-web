"""
Hatchling build hook to compile and bundle the React frontend into wheels.
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

from hatchling.builders.hooks.plugin.interface import (
    BuildHookInterface,  # type: ignore[import-untyped]
)

logger = logging.getLogger(__name__)


class FrontendBuildHook(BuildHookInterface):
    """
    Build the frontend assets and stage them into the camply distribution.

    When building a wheel from the monorepo checkout, this hook invokes
    pnpm to build the static React assets and stages them into
    camply/server/static so they are included in the packaged wheel.
    When building from a source distribution without frontend source files,
    or in an environment lacking pnpm, the hook safely skips the build.
    """

    PLUGIN_NAME = "custom"

    def initialize(self, version: str, build_data: dict[str, Any]) -> None:
        """
        Execute the frontend build if building a wheel from repository sources.

        Parameters
        ----------
        version : str
            The project version string being built.
        build_data : dict[str, Any]
            The build data dictionary passed to the target builder.
        """
        if self.target_name != "wheel" or version != "standard":
            return

        backend_root = Path(self.root).resolve()
        frontend_dir = backend_root.parent / "frontend"
        package_json = frontend_dir / "package.json"
        node_modules = frontend_dir / "node_modules"

        pnpm = shutil.which("pnpm")
        npm = shutil.which("npm")
        if not package_json.is_file():
            logger.info(
                "Frontend package.json not found at %s; skipping frontend build",
                package_json,
            )
            self.app.display_info(
                "Frontend package.json not found; skipping frontend build."
            )
            return

        if not node_modules.is_dir():
            logger.info(
                "Frontend node_modules not found at %s; skipping frontend build",
                node_modules,
            )
            self.app.display_info(
                "Frontend node_modules not found; skipping frontend build."
            )
            return

        if pnpm:
            build_cmd = [pnpm, "run", "build"]
            runner = "pnpm"
        elif npm:
            build_cmd = [npm, "run", "build"]
            runner = "npm"
        else:
            logger.warning(
                "Neither pnpm nor npm found in PATH; skipping frontend build"
            )
            self.app.display_warning(
                "Neither pnpm nor npm found in PATH; skipping frontend build."
            )
            return

        self.app.display_waiting(f"Building React frontend with {runner}...")
        logger.info("Building React frontend at %s using %s", frontend_dir, runner)

        build_env = {
            **os.environ,
            "CAMPLY_STANDALONE_BUILD": "1",
            "VITE_API_URL": "/api",
        }
        subprocess.run(
            build_cmd,
            cwd=frontend_dir,
            env=build_env,
            check=True,
        )

        dist_dir = frontend_dir / "dist"
        if not (dist_dir / "index.html").is_file():
            msg = "Frontend build did not produce dist/index.html"
            logger.error(msg)
            raise RuntimeError(msg)

        static_dest = backend_root / "src" / "camply" / "server" / "static"
        relative_dest = static_dest.relative_to(backend_root)
        self.app.display_info(f"Staging built frontend assets into {relative_dest}")
        logger.info(
            "Staging built frontend assets from %s to %s", dist_dir, static_dest
        )

        if static_dest.exists():
            shutil.rmtree(static_dest)
        shutil.copytree(dist_dir, static_dest)
        self.app.display_success("Frontend build and staging complete.")

    def clean(self, versions: list[str]) -> None:
        """
        Remove staged static files when cleaning build targets.

        Parameters
        ----------
        versions : list[str]
            The list of versions being cleaned.
        """
        backend_root = Path(self.root).resolve()
        static_dest = backend_root / "src" / "camply" / "server" / "static"
        if static_dest.exists():
            relative_dest = static_dest.relative_to(backend_root)
            self.app.display_info(f"Removing staged frontend assets at {relative_dest}")
            logger.info("Removing staged frontend static assets at %s", static_dest)
            shutil.rmtree(static_dest)
