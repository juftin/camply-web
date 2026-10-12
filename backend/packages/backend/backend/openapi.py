"""Export the application contract for offline client generation and drift checks."""

import argparse
import json
from pathlib import Path

from backend.app import app


def main() -> None:
    """Write the FastAPI OpenAPI schema to the requested build artifact."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    output: Path = parser.parse_args().output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(app.openapi(), indent=2) + "\n")


if __name__ == "__main__":
    main()
