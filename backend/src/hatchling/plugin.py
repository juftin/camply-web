"""
Hatchling build hook to compile and bundle the React frontend into wheels.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Any

from hatchling.builders.hooks.plugin.interface import (
    BuildHookInterface,  # type: ignore[import-untyped]
)


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
        if self.target_name != "wheel":
            return

        backend_root = Path(self.root).resolve()
        frontend_dir = backend_root.parent / "frontend"
        package_json = frontend_dir / "package.json"

        pnpm = shutil.which("pnpm")
        if not package_json.is_file() or not pnpm:
            return

        subprocess.run(
            [pnpm, "run", "build"],
            cwd=frontend_dir,
            check=True,
        )

        dist_dir = frontend_dir / "dist"
        if not (dist_dir / "index.html").is_file():
            msg = "Frontend build did not produce dist/index.html"
            raise RuntimeError(msg)

        static_dest = backend_root / "src" / "camply" / "server" / "static"
        if static_dest.exists():
            shutil.rmtree(static_dest)
        shutil.copytree(dist_dir, static_dest)
