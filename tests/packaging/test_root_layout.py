"""Guard root packaging and installed runtime configuration boundaries."""

import tomllib
from pathlib import Path


def test_root_build_configuration() -> None:
    """Root metadata must own both source distributions and frontend bundling."""
    root = Path(__file__).resolve().parents[2]
    with (root / "pyproject.toml").open("rb") as stream:
        config = tomllib.load(stream)
    assert (
        config["tool"]["hatch"]["build"]["hooks"]["custom"]["path"] == "hatch_build.py"
    )
    assert (root / "src/camply/server/gunicorn.py").is_file()
