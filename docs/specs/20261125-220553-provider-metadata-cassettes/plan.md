# Implementation Plan for Provider Metadata Cassettes

**Feature** — 20261125-220553-provider-metadata-cassettes

**Spec** — [Provider Metadata Cassettes](spec.md)

## Summary

Record public provider responses for discovery first, enrichment next, then catalog sync and campsite listing. Reuse the real adapter methods and the repository's pytest, AnyIO, and VCR integration.

## Technical Context

- Put scenario inputs and independently verified expectations in `tests/providers/metadata_cases.py`. Store recordings by operation and family under `tests/providers/cassettes/metadata/`.
- Build on Spec 034's strict matching, sanitization, and opt-in single-case recording. Keep fixture selection independent and preserve the existing availability commands. Stage candidates under ignored `tmp/`.
- Use `search`, `get_campground`, `get_recreation_area`, `iter_campgrounds`, `sync_metadata`, and `list_campsites` through the real adapter. Use isolated SQLite for catalog and enrichment.
- Use compact sanitized RIDB archives for Recreation.gov, preserving the upstream archive members and record envelopes the parser needs. For UseDirect image checks, keep the status and bounded image evidence the adapter consumes. Use synthetic anonymous session placeholders for ReserveAmerica.
- Use deterministic synthetic failures to prove cache and catalog preservation. Freeze the browse date when required.

## Constitution Check

Exercise production provider entry points with typed assertions. Keep fixture helpers in the test layer and storage isolated. Use existing task and uv workflows. Add focused tests for new recording controls and run strict replay in normal backend CI.

## Planned Files

- `tests/providers/test_metadata_discovery_cassettes.py` covers search and lookup.
- `tests/providers/test_metadata_enrichment_cassettes.py` covers destination details.
- `tests/providers/test_metadata_catalog_cassettes.py` covers sync and site listing.
- `tests/providers/metadata_replay.py` opens operation-scoped fixtures and stages the compact RIDB archive.
- `tests/providers/test_metadata_cassette_controls.py` covers record and replay selection errors.
- `tests/providers/conftest.py` and `tests/providers/cassette_sanitization.py` can share selection and staging logic with availability where it applies.
- `docs/development/PROVIDER_CASSETTES.md` documents metadata fixture refresh.
