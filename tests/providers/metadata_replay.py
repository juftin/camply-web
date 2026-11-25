"""Use an isolated VCR recording for each metadata operation and provider family."""

from contextlib import AbstractContextManager
from functools import partial
from pathlib import Path
from typing import Any

import pytest
import vcr

from tests.providers.metadata_cases import MetadataTarget
from tests.providers.metadata_sanitization import sanitize_metadata_interaction

ROOT = Path(__file__).with_name("cassettes") / "metadata"
MATCHERS = ("method", "scheme", "host", "port", "path", "query", "body")


def metadata_replay(
    config: pytest.Config, *, operation: str, case: MetadataTarget
) -> AbstractContextManager[Any]:
    """Replay by default and save opt-in recordings only to the staged path."""
    key = f"{operation}/{case.key}"
    record = config.getoption("record_provider_metadata")
    candidate = config.getoption("provider_metadata_candidate")
    path = ROOT / f"{key}.yaml"
    if candidate is not None and candidate.suffix.lower() != ".zip":
        path = candidate
    if not record and not path.is_file():
        pytest.fail(f"{key}: missing metadata cassette at {path}")
    return vcr.use_cassette(
        str(path),
        record_mode="all" if record else "none",
        match_on=MATCHERS,
        allow_playback_repeats=True,
        decode_compressed_response=True,
        record_on_exception=False,
        before_save_interaction=partial(sanitize_metadata_interaction, case=case),
    )


def stage_ridb(
    cache: Path, monkeypatch: pytest.MonkeyPatch, *, config: pytest.Config
) -> None:
    """Feed a reviewed compact RIDB archive through the real export cache path."""
    from shutil import copyfile

    candidate = config.getoption("provider_metadata_candidate")
    archive = ROOT / "ridb/joshua-tree.zip"
    if candidate is not None and candidate.suffix.lower() == ".zip":
        archive = candidate
    if not archive.is_file():
        pytest.fail(f"recreation-gov: missing compact RIDB archive at {archive}")
    copyfile(archive, cache / "RIDBFullExport_V1_JSON.zip")
    monkeypatch.setattr(
        "camply.providers.recreation_gov.provider.platformdirs.user_data_dir",
        lambda **_: str(cache),
    )
