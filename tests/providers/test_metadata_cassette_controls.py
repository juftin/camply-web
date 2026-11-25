"""Verify metadata capture safeguards and compatibility with availability options."""

from pathlib import Path
from types import SimpleNamespace

import httpx2
import pytest
from vcr.errors import CannotOverwriteExistingCassetteException

from tests.providers.conftest import _validate_candidate
from tests.providers.metadata_cases import TARGETS
from tests.providers.metadata_replay import metadata_replay, stage_ridb


def _session(tmp_path: Path, *, module: str, keys: tuple[str, ...]):
    """Model the selected pytest nodes without collecting a nested test run."""
    return SimpleNamespace(
        config=SimpleNamespace(rootpath=tmp_path),
        items=[
            SimpleNamespace(
                path=Path(f"{module}.py"),
                callspec=SimpleNamespace(params={"case": SimpleNamespace(key=key)}),
            )
            for key in keys
        ],
    )


@pytest.mark.parametrize(
    ("family", "module", "key"),
    [
        (
            "availability",
            "test_availability_cassettes",
            "recreation-gov/jumbo-rocks-tent",
        ),
        ("metadata", "test_metadata_discovery_cassettes", "discovery/recreation-gov"),
    ],
)
def test_single_case_candidate(
    tmp_path: Path, family: str, module: str, key: str
) -> None:
    """Accept a fresh staged path for each workflow and reject the wrong case."""
    case_key = key if family == "availability" else key.split("/")[1]
    session = _session(tmp_path, module=module, keys=(case_key,))
    candidate = tmp_path / "tmp" / "candidate.yaml"
    _validate_candidate(session, family=family, record=key, candidate=candidate)
    with pytest.raises(pytest.UsageError, match="but requested"):
        _validate_candidate(session, family=family, record="other", candidate=candidate)
    with pytest.raises(pytest.UsageError, match="under tmp"):
        _validate_candidate(
            session, family=family, record=key, candidate=tmp_path / "outside.yaml"
        )
    session.items.append(session.items[0])
    with pytest.raises(pytest.UsageError, match="exactly one"):
        _validate_candidate(session, family=family, record=key, candidate=candidate)


def test_ridb_candidate_is_for_recreation_gov_replay(tmp_path: Path) -> None:
    """Limit staged archives to the catalog and enrichment consumers."""
    candidate = tmp_path / "tmp" / "candidate.zip"
    for operation in ("catalog", "enrichment"):
        session = _session(
            tmp_path,
            module=f"test_metadata_{operation}_cassettes",
            keys=("recreation-gov",),
        )
        _validate_candidate(
            session, family="metadata", record=None, candidate=candidate
        )
    session = _session(
        tmp_path, module="test_metadata_catalog_cassettes", keys=("recreation-gov",)
    )
    with pytest.raises(pytest.UsageError, match="replay"):
        _validate_candidate(
            session,
            family="metadata",
            record="catalog/recreation-gov",
            candidate=candidate,
        )
    for operation, family in (
        ("discovery", "recreation-gov"),
        ("catalog", "usedirect"),
    ):
        session = _session(
            tmp_path, module=f"test_metadata_{operation}_cassettes", keys=(family,)
        )
        with pytest.raises(pytest.UsageError, match=r"Recreation\.gov"):
            _validate_candidate(
                session, family="metadata", record=None, candidate=candidate
            )


def test_ridb_candidate_keeps_catalog_cassette_independent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Use the staged ZIP for the cache and the YAML fixture for HTTP replay."""
    candidate = tmp_path / "candidate.zip"
    candidate.write_bytes(b"staged archive")
    yaml = tmp_path / "catalog" / "recreation-gov.yaml"
    yaml.parent.mkdir()
    yaml.write_text("version: 1\ninteractions: []\n")
    monkeypatch.setattr("tests.providers.metadata_replay.ROOT", tmp_path)
    config = SimpleNamespace(
        getoption={
            "record_provider_metadata": None,
            "provider_metadata_candidate": candidate,
        }.get
    )
    stage_ridb(tmp_path, monkeypatch, config=config)
    assert (tmp_path / "RIDBFullExport_V1_JSON.zip").read_bytes() == b"staged archive"
    with metadata_replay(config, operation="catalog", case=TARGETS[0]) as cassette:
        assert Path(cassette.path) == yaml


@pytest.mark.anyio
async def test_metadata_replay_rejects_missing_or_mismatched_request(
    tmp_path: Path,
) -> None:
    """Fail locally on a missing cassette or an unrecorded request."""
    candidate = tmp_path / "candidate.yaml"
    config = SimpleNamespace(
        getoption={
            "record_provider_metadata": None,
            "provider_metadata_candidate": candidate,
        }.get
    )
    with pytest.raises(pytest.fail.Exception, match="missing metadata cassette"):
        metadata_replay(config, operation="discovery", case=TARGETS[0])
    candidate.write_text("version: 1\ninteractions: []\n")
    async with httpx2.AsyncClient() as client:
        with (
            metadata_replay(config, operation="discovery", case=TARGETS[0]),
            pytest.raises(CannotOverwriteExistingCassetteException),
        ):
            await client.get("https://example.test/changed-path")
    assert candidate.read_text() == "version: 1\ninteractions: []\n"
