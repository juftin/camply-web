"""Stage a Vite build inside the backend wheel without retaining stale assets."""

import shutil
from pathlib import Path


def main() -> None:
    """Copy only the generated frontend build into its dedicated package directory."""
    root = Path(__file__).resolve().parents[1]
    source = root / "frontend/dist"
    destination = root / "backend/packages/backend/backend/static"
    if not (source / "index.html").is_file():
        raise RuntimeError("Build the frontend before staging standalone assets")
    if destination.exists():
        shutil.rmtree(destination)
    shutil.copytree(source, destination)


if __name__ == "__main__":
    main()
