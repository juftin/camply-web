"""Serve only built frontend assets with guarded client-navigation fallback."""

from pathlib import Path

from fastapi import FastAPI
from starlette.datastructures import Headers
from starlette.exceptions import HTTPException
from starlette.responses import FileResponse, Response
from starlette.staticfiles import StaticFiles
from starlette.status import HTTP_404_NOT_FOUND
from starlette.types import Scope


class FrontendFiles(StaticFiles):
    """Preserve API/asset errors while supporting browser deep links."""

    async def get_response(self, path: str, scope: Scope) -> Response:
        """Resolve assets inside the build root and fallback only for navigation."""
        parts = Path(path).parts
        if ".." in parts or (parts and parts[0] in {"api", "metrics"}):
            raise HTTPException(status_code=404)
        try:
            response = await super().get_response(path, scope)
        except HTTPException as exc:
            navigation = "text/html" in Headers(scope=scope).get("accept", "")
            if (
                exc.status_code != HTTP_404_NOT_FOUND
                or Path(path).suffix
                or path.startswith("assets/")
                or (path not in {"", "."} and not navigation)
            ):
                raise
            response = FileResponse(Path(str(self.directory)) / "index.html")
        response.headers["Cache-Control"] = (
            "public, max-age=31536000, immutable"
            if path.startswith("assets/")
            else "no-cache"
        )
        return response


def attach_frontend(app: FastAPI, directory: Path) -> None:
    """Mount the built frontend after API routers without starting runtime work."""
    app.mount("/", FrontendFiles(directory=directory, check_dir=False), name="frontend")
