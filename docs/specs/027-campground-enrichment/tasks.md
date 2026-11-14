# Enrichment delivery backlog

**Status**: Implementation and local verification complete 2026-11-14. See [validation](validation.md) for exact results and outstanding macOS/live-PostgreSQL release checks. `[P]` marks independently executable work.

## Completed research

- [x] T001 Audit existing descriptions, provider ingestion, destination models, API responses, and rendering.
- [x] T002 Verify Recreation.gov export members and sampled detail/media schemas with public read-only requests.
- [x] T003 Verify California catalog/park-information routes and record access/evidence limits for other providers.
- [x] T004 Write proposed behavior, implementation sequence, and validation gates.
- [x] T017 Probe all ten UseDirect deployments: park details, dated-search narratives, public park/facility image paths, placeholder URLs, missing assets, and source scope. Record the [provider matrix](provider-matrix.md).
- [x] T018 Verify ReserveAmerica facility details for three contracts, original-photo loading for two destinations, valid empty galleries, and alternate-rendition/path behavior.
- [x] T019 Verify the official Washington park-gallery fallback, one image response, and an explicit native booking-ID link; keep native media support unverified.

## Phase 1: Design and shared foundations

- [x] T020 Complete clarification, UI/UX, schema, API contract, and validation artifacts in this feature directory; record reviewer checklist without claiming user approval.
- [x] T021 Add failing shared DTO/persistence regressions in `tests/providers/test_destination_details.py` and migration tests in `tests/db/test_destination_details.py`.
- [x] T022 Implement `src/camply/providers/details.py`, nullable model fields in `src/camply/db/models/{campgrounds,recreation_area}.py`, and a forward migration under `src/camply/db/migrations/versions/`.
- [x] T023 Implement bounded/freshness-aware cached refresh helpers in `src/camply/providers/enrichment.py`, provider extension in `base.py`, and post-catalog calls in `src/camply/cli/db.py` and `src/camply/worker/engine/catalog.py`; test failure retention and workflow dispatch.

## Phase 2: US1 — Recreation.gov photos and practical details

- [x] T005 Verify archive destination discriminators and member semantics against public source data; document evidence and coverage limits in `research.md`.
- [x] T006 Measure bounded `ijson` parsing memory/runtime and record the result in `research.md`; manage dependency through root `pyproject.toml`/`uv.lock` via uv.
- [x] T007 Add failing synthetic archive regressions in `tests/providers/test_recreation_gov_enrichment.py` for collisions, ordering/cap, missing members, malformed/empty snapshots, and failures.
- [x] T008 Verify ordinary catalog merge preservation and SQLite/PostgreSQL migration compatibility in shared foundation tests.
- [x] T009 Implement cached-export enrichment in `src/camply/providers/recreation_gov/enrichment.py` and its provider extension; retain narrative fields, media, links, activities, and successful freshness.
- [x] T010 Add `CampgroundDetail` and area details in `src/camply/server/{models/campgrounds,routers/campgrounds,routers/recreation_areas}.py`, focused API regressions, and regenerate `src/frontend/lib/api/generated/schema.ts` through `task api:generate`.

## Phase 3: US1 — Destination UI [P]

- [x] T011 [P] Write failing gallery/detail tests then implement `src/frontend/components/DestinationDetails.tsx`, typed structs/API returns, and integration in `pages/{Campground,RecreationArea}.tsx`, following `ui-ux.md`.
- [x] T024 [P] Verify keyboard/focus, safe narrative/link rendering, captions/provenance, broken/all-broken media, own-versus-parent association, and enriched desktop/mobile themes with synthetic frontend fixtures.

## Phase 4: US3 — Additional verified providers [P]

- [x] T013 [P] Add failing synthetic tests then implement `src/camply/providers/usedirect/enrichment.py` and provider extension for all ten deployments. Skip placeholder limits/URLs and dated narrative searches; validate static image content and exact entity identity.
- [x] T014 Discover actual UseDirect destination photo requests and associations: park images across all ten deployments and facility images in five deployment samples. This verifies image paths, not universal coverage or multi-photo galleries.
- [x] T015 [P] Add failing tests then implement `src/camply/providers/reserve_america/enrichment.py` and provider extension using existing session handling. Cover escaped paths, distance-qualified amenities, schema completeness, valid empty galleries, and failure retention.
- [x] T016 Record native GoingToCamp/official-site integration as explicitly deferred scope in `spec.md` and `provider-matrix.md`; no unverified scraping is required by this release.

## Phase 5: Verification and convergence

- [x] T012 Run project quality/docs/test/migration/visual gates, record actual outcomes and limitations, and update `docs/CHECKLIST.md` plus current architecture/operations guides.
- [x] T025 Run `/speckit-converge` against all implemented requirements and tasks, append/fix any gaps, and repeat until Converged for feature scope; record environment-dependent release checks separately in `validation.md`.

## Dependencies and independent checks

T020 precedes all code. T021 must fail before T022; T022 precedes T023. After that contract, Recreation.gov, the frontend, and the other provider adapters can run independently in their separate files. T007 precedes T009; T010 depends on T022, and UI integration depends on T010's agreed contract. Each provider's synthetic HTTP tests precede its adapter. Final checks and convergence follow all release implementation tasks. Reviewer-owned `checklists/ux.md` stays unchecked for user review; the user has already instructed this complete process to proceed through implementation.
