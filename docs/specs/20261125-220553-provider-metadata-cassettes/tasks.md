---
description: Implementation tasks for provider metadata cassettes
---

# Tasks for Provider Metadata Cassettes

**Design** — [Specification](spec.md), [plan](plan.md), [fixture decisions](research.md), [test data](data-model.md), and [verification](quickstart.md)

## Phase 1 — Setup

- [x] T001 Audit the public provider entry points and existing synthetic baselines in `tests/providers/test_search.py`, `tests/providers/test_enrichment_refresh.py`, and `docs/architecture/DESIGN_PROVIDERS.md`. Confirm the candidate targets and supported entity types before recording.

## Phase 2 — Foundation

- [x] T002 Define the case inventory in `tests/providers/metadata_cases.py`. Require a unique operation and provider-qualified key, public source, native campground ID, optional native area ID, and independently verified expected fields. Preserve ReserveAmerica campground IDs as opaque contract-qualified strings.
- [x] T003 Add single-case metadata staging and strict offline replay in `tests/providers/conftest.py` and `tests/providers/cassette_sanitization.py`. Keep shape, pagination, entity attribution, and necessary status information. Strip unrelated private fields and keep synthetic session placeholders. Cover missing and mismatched fixtures, rejected recording selections, and existing availability commands in `tests/providers/test_metadata_cassette_controls.py`.

## Phase 3 — User Story 1 (P1)

**Goal** — Verify destination discovery, exact identity, and recreation-area membership from recorded responses.

**Independent test** — Run `tests/providers/test_metadata_discovery_cassettes.py` offline. Expect four positive discovery and exact-lookup cases, including three area expansion cases.

- [x] T004 [US1] Add public search and exact-lookup assertions to `tests/providers/test_metadata_discovery_cassettes.py`. Assert known native IDs, names, normalized locations, public booking URLs, and applicable parent IDs. Assert the selected area's overnight membership and known ineligible exclusions.
- [x] T005 [US1] Confirm and record one Recreation.gov campground and multi-campground area under `tests/providers/cassettes/metadata/discovery/recreation-gov.yaml`. Register the case inputs and expectations in `tests/providers/metadata_cases.py` before capture. Retain search and exact-lookup responses and pages needed for verified area membership.
- [x] T006 [US1] Confirm and record one ReserveCalifornia park and its campground relationships under `tests/providers/cassettes/metadata/discovery/usedirect.yaml`. Register the case in `tests/providers/metadata_cases.py` before capture and preserve the parent park and facility IDs used by the public links.
- [x] T007 [US1] Confirm and record one Washington State Parks area under `tests/providers/cassettes/metadata/discovery/going-to-camp.yaml`. Register the case in `tests/providers/metadata_cases.py` before capture. Preserve the transaction and resource location IDs and the eligibility fields used to exclude day-use or other ineligible inventory.
- [x] T008 [US1] Confirm and record a ReserveAmerica campground under `tests/providers/cassettes/metadata/discovery/reserve-america.yaml`. Register the case in `tests/providers/metadata_cases.py` before capture. Verify exact resolution of the compound ID, public booking URL, synthetic anonymous bootstrap, and the absent recreation-area parent.
- [x] T009 [US1] Run `tests/providers/test_metadata_discovery_cassettes.py` offline with all four families collected. Test one request mismatch with a temporary input change using `docs/specs/20261125-220553-provider-metadata-cassettes/quickstart.md`.

## Phase 4 — User Story 2 (P2)

**Goal** — Verify enrichment identity, representative practical details, and preservation on incomplete refresh.

**Independent test** — Run `tests/providers/test_metadata_enrichment_cassettes.py` offline, check all supported snapshots, and inject one incomplete refresh.

- [x] T010 [US2] Add fixture-backed snapshot assertions in `tests/providers/test_metadata_enrichment_cassettes.py` using isolated SQLite. Verify known photo URLs and practical fields by entity type and native ID. Seed a good snapshot, inject an incomplete response, and verify the prior snapshot survives. Record GoingToCamp's unsupported behavior in the case documentation.
- [x] T011 [US2] Capture a compact Recreation.gov RIDB archive under `tests/providers/cassettes/metadata/ridb/joshua-tree.zip`. Register the case in `tests/providers/metadata_cases.py` before capture. Preserve relevant member names and envelopes. Assert a selected campground and its area receive their respective media and practical details.
- [x] T012 [US2] Capture Arizona State Parks information and bounded image responses under `tests/providers/cassettes/metadata/enrichment/usedirect.yaml`. Register the cases in `tests/providers/metadata_cases.py` before capture. Cover both supported entity types and verify that the campground does not inherit parent practical details.
- [x] T013 [US2] Register the ReserveAmerica enrichment case in `tests/providers/metadata_cases.py` and capture facility details under `tests/providers/cassettes/metadata/enrichment/reserve-america.yaml`. Verify a known campground photo and practical detail while retaining synthetic session data for replay.

## Phase 5 — User Story 3 (P3)

**Goal** — Verify provider catalog persistence and independently observed campsite attributes.

**Independent test** — Run `tests/providers/test_metadata_catalog_cassettes.py` offline and check that all four families produce the expected catalog rows and site attributes.

- [x] T014 [US3] Add catalog sync and campsite listing assertions to `tests/providers/test_metadata_catalog_cassettes.py`. Assert persisted native IDs, parent relationships, reservability, and search rows in temporary SQLite. Assert at least one verified site capability per selected case and freeze dates for browse endpoints. Inject an incomplete refresh and verify the previous successful catalog survives.
- [x] T015 [US3] Register the catalog and listing cases for Recreation.gov, ReserveCalifornia, Washington State Parks, and ReserveAmerica in `tests/providers/metadata_cases.py`, then capture them under `tests/providers/cassettes/metadata/catalog/`. Use the supported 14-day ReserveAmerica listing grid and cover the request in `tests/providers/test_reserve_america.py`. Reuse a compatible compact RIDB fixture where it serves both catalog and enrichment. Preserve the provider's eligibility and pagination fields.

## Phase 6 — Verification and Maintenance

- [x] T016 Add case IDs, verification sources, native IDs, capture inputs, fixture paths, last successful verification dates, and commands to stage and replay one replacement to `docs/development/PROVIDER_CASSETTES.md`. Cover archive review, bounded image responses, and recovery after a failed capture.
- [x] T017 Run the offline scenarios in `docs/specs/20261125-220553-provider-metadata-cassettes/quickstart.md`, including one staged refresh with companion checksum verification. Run normal backend tests, lint, and type checks, inspect recorded files for private data, and record the verified coverage in `docs/CHECKLIST.md`.

## Dependencies and Execution Order

- T001 precedes T002–T003. The three test modules depend on the shared metadata recording controls.
- Deliver US1 first. Its MVP covers discovery and exact lookup for all four families and area expansion for the three supporting families.
- After T003, the three story-specific test modules can be drafted independently. For example, T004 and T010 touch different files. Capture prep for T005–T008 can proceed in separate fixture directories. Merge updates to the shared inventory in sequence.
- US2 and US3 each have their own verification. If the catalog tests reuse the Recreation.gov enrichment archive, finish T011 before that part of T015.
- T016 can collect sources alongside each capture, then publish the case entries after the inputs and fixtures are final. T017 follows all three stories.

## Phase 7: Convergence

- [x] T018 [US1] Record a recreation-area discovery response containing at least one known ineligible destination alongside eligible overnight campgrounds. Assert the ineligible native ID is absent from the expanded members and the expected overnight members retain the correct parent ID. Update the case inventory and refresh guide, then run all discovery cases offline per US1/AC2, FR-002, and T004 (partial)
- [x] T019 Replay both Recreation.gov enrichment and catalog sync against the same staged RIDB ZIP before replacing the shared fixture. Keep the catalog listing cassette independent. Verify that a candidate without a required catalog member fails before promotion, and document both offline replay commands and when to replace the archive per FR-007 and T016 (partial)
