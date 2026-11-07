"""Publish a stable semantic chart version with its matching release image."""

import json
import os
import re
import subprocess
import tarfile
from pathlib import Path

import yaml

REGISTRY = "ghcr.io/juftin/charts/camply-web"
SOURCE = "https://github.com/juftin/camply-web"


def main() -> None:
    """Validate the publication context, package the release chart, and upload it."""
    release = os.environ.get("RELEASE_VERSION", "")
    revision = os.environ.get("GITHUB_SHA", "")
    if os.environ.get("CI") != "true":
        raise SystemExit("Chart publishing requires CI=true and a GHCR session.")
    if not re.fullmatch(r"(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)", release):
        raise SystemExit("RELEASE_VERSION must be a stable semantic version.")
    if not re.fullmatch(r"[0-9a-f]{7,40}", revision):
        raise SystemExit(
            "GITHUB_SHA must contain 7 to 40 lowercase hexadecimal characters."
        )

    version = release
    subprocess.run(["helm", "lint", "deploy/helm", "--strict"], check=True)
    destination = Path("dist/helm") / release
    destination.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            "helm",
            "package",
            "deploy/helm",
            "--destination",
            str(destination),
            "--version",
            version,
            "--app-version",
            f"v{release}",
        ],
        check=True,
    )
    archive = destination / f"camply-web-{version}.tgz"
    with tarfile.open(archive) as package:
        metadata_file = package.extractfile("camply-web/Chart.yaml")
        if metadata_file is None:
            raise SystemExit("Packaged chart metadata is missing.")
        metadata = yaml.safe_load(metadata_file)
    (destination / "config.json").write_text(json.dumps(metadata))
    subprocess.run(
        [
            "oras",
            "push",
            "--config",
            "config.json:application/vnd.cncf.helm.config.v1+json",
            "--annotation",
            f"org.opencontainers.image.source={SOURCE}",
            f"{REGISTRY}:{release}",
            f"{archive.name}:application/vnd.cncf.helm.chart.content.v1.tar+gzip",
        ],
        cwd=destination,
        check=True,
    )


if __name__ == "__main__":
    main()
