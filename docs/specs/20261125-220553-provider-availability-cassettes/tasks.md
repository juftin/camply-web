# Tasks for Provider Availability Cassettes

**Input** — [Spec](spec.md), [plan](plan.md), [research](research.md), [test data](data-model.md), and [verification procedures](quickstart.md)

## Phase 1 — Setup

- [x] T001 Audit the three existing HTTP replays in `tests/providers/test_recreation_gov.py`, `tests/providers/test_reserve_california.py`, and `tests/providers/test_going_to_camp.py`. Run the existing cases through `task backend:test` and confirm how strict matching and recording mode work with the installed VCR integration.

## Phase 2 — Foundation

- [x] T002 Define scenario records in `tests/providers/availability_cases.py` with a unique provider-qualified key, native campground ID as an opaque string, fixed arrival and checkout, equipment inputs, and independently verified site expectations. Require checkout after arrival, at least one expected site and night, and all expected nights within `arrival <= night < checkout`.
- [x] T003 Add scoped replay and targeted capture controls in `tests/providers/conftest.py`. Default to replay-only, match the origin, method, path, query, and meaningful request body, and accept live recording only for one explicitly selected scenario. Stage candidates under `tmp/`, sanitize requests and responses, and preserve the checked-in cassette on failure. Verify ReserveAmerica session placeholders remain usable offline.

## Phase 3 — User Story 1 (P1)

**Goal** — Verify provider availability and equipment results in normal backend tests.

**Independent test** — Run the complete new suite with outbound networking disabled. Expect at least two passing positive cases per registered provider and case-specific failures for incomplete fixtures or regressions.

- [x] T004 [US1] Add the parameterized adapter and equipment assertions to `tests/providers/test_availability_cassettes.py`. Test the real transport and normalized output for a known site, name or type, and exact nights. Reject empty results and nights on or after checkout or before arrival. For equipment, pass the recorded search through camply's shared availability path with a fixed clock and assert compatible sites and exclusions based on independently observed inventory. Close the client on failure.
- [x] T005 [US1] Confirm known-open Recreation.gov searches, capture and sanitize the cassettes in `tests/providers/cassettes/availability/recreation-gov/`, and register them in `tests/providers/availability_cases.py`. Cover two equipment requests where supported. Address the vacuous positive assertion in `tests/providers/test_recreation_gov.py` once equivalent coverage is verified.
- [x] T006 [US1] Confirm and record at least two searches each for the 10 UseDirect providers in `tests/providers/cassettes/availability/usedirect/` and register them in `tests/providers/availability_cases.py`. Include tent and RV or trailer length requests where supported. Track equipment capability gaps and choose different campground or date inputs where necessary.
- [ ] T007 [US1] Confirm and record at least two searches each for the 14 GoingToCamp providers in `tests/providers/cassettes/availability/going-to-camp/` and register them in `tests/providers/availability_cases.py`. Include eligible overnight categories and supported equipment contrasts. Record any parent or resource context required to reproduce the request.
- [x] T008 [US1] Confirm and record at least two ReserveAmerica searches in `tests/providers/cassettes/availability/reserve-america/` and register them in `tests/providers/availability_cases.py`. Use contract-qualified campground IDs and include supported equipment contrasts. Confirm replay works with sanitized, synthetic session material.
- [ ] T009 [US1] Enable registry parity in `tests/providers/test_availability_cassettes.py`. Report every registered provider with fewer than two positive scenarios or missing required equipment coverage. Demonstrate a missing cassette, changed request input, incorrect site or night, and incompatible return each fail with the provider and case key. Follow the failure checks in `docs/specs/20261125-220553-provider-availability-cassettes/quickstart.md`.

## Phase 4 — User Story 2 (P2)

**Goal** — Refresh one scenario from a known-open stay and preserve other recordings.

**Independent test** — Follow the guide to replace a historical scenario with an open stay, verify the replacement offline, and replay the provider's other scenario. Confirm a failed attempt preserves the previous recording.

- [x] T010 [US2] Write `docs/development/PROVIDER_CASSETTES.md` with the single-case recording and offline verification commands, the 30-day review cadence, provider-change triggers, a year rollover example, and recovery steps for closed inventory, failed captures, and deferred refreshes. Replace the broad re-recording instruction in `docs/development/DEVELOPER_GUIDE.md` with a link.
- [x] T011 [US2] Document each scenario in `docs/development/PROVIDER_CASSETTES.md` with its provider booking URL, instructions to find open nights and replacement campgrounds, current campground name and native ID, equipment and other search options, test and cassette paths, expected-result update instructions, and last successful verification date.
- [x] T012 [US2] Demonstrate a successful and failed targeted refresh using `docs/specs/20261125-220553-provider-availability-cassettes/quickstart.md`. During the successful refresh, change the inputs, expected results, verification date, and cassette together. Confirm another case for the same provider still passes.

## Phase 5 — Final Verification

- [x] T013 Run the offline provider suite and the project's backend tests, lint, and type checks. Review every fixture diff under `tests/providers/cassettes/availability/` for sensitive data and confirm the normal CI workflow collects the new suite. Update `docs/CHECKLIST.md` with the verified coverage and refresh workflow.

## Dependencies and Execution Order

- T001 precedes T002 and T003. The suite assertions in T004 depend on the scenario and replay foundation.
- T005 exercises the complete path first. T006–T008 can locate bookable scenarios and capture into separate family directories in parallel after that checkpoint. Integrate their changes to the shared inventory sequentially before T009.
- T010 can be drafted once capture commands and staging behavior are defined. T011 can collect provider-specific notes alongside the provider captures, then publish them once scenario inputs and paths are final. T012 follows T010 and T011.
- T013 follows both stories. The first working increment is the Recreation.gov pilot. The coverage milestone requires all registered providers. The refresh demonstration completes the feature.

## Phase 6: Convergence

- [ ] T014 Capture and replay two confirmed scenarios each for Nova Scotia Parks, Manitoba Parks, Newfoundland and Labrador Parks, Long Point Region, Maitland Valley, and St. Clair Region once their nightly windows open. Use the targets and release links in `docs/development/PROVIDER_CASSETTES.md`, then remove the six expected failures from `tests/providers/test_availability_cassettes.py` and complete T007 and T009 per FR-001, FR-005, and SC-001 (partial).

### Seasonal recording TODOs

The sampled windows returned no bookable stays on November 25, 2026. Each TODO requires two positive recordings, an equipment contrast where supported, and an offline replay. Remove the provider's seasonal expected failure once both cases pass. See the [deferred booking targets](../../development/PROVIDER_CASSETTES.md#deferred-initial-recordings).

- [ ] **Maitland Valley** — Record two Falls Reserve searches after reservations reopen in early January 2027.
- [ ] **St. Clair Region** — Record two Warwick searches after reservations open January 11, 2027 at 8:30 a.m.
- [ ] **Long Point Region** — Record two Backus Heritage searches when the authority publishes and opens its 2027 nightly booking window.
- [ ] **Manitoba Parks** — Record two Birds Hill searches after the 2027 campground release. Use Kiche Manitou as a fallback if it has bookable sites.
- [ ] **Newfoundland and Labrador Parks** — Record two Butter Pot searches after ParksNL opens nightly reservations. Check the launch notice in April.
- [ ] **Nova Scotia Parks** — Record two Rissers Beach searches after bookings open in April 2027.

## Phase 7: Convergence

- [x] T015 Add a CRITICAL focused unit regression in `tests/providers/test_recreation_gov.py` that covers exclusive checkout and verifies a checkout on the first of a month does not request that month's inventory. Use synthetic provider responses and retain the cassette integration coverage per Constitution V (missing).
- [x] T016 Extend the registry check in `tests/providers/test_availability_cassettes.py` to identify providers missing required equipment contrasts or incompatible-site assertions even when two positive cases exist. Give providers with documented inventory or equipment limitations an explicit fallback and verify that removing a supported contrast fails the check per FR-005 and US1/AC4 (partial).
- [x] T017 Verify additional bookable inventory for the equipment fallbacks in `tests/providers/availability_cases.py`, starting with Northern Territory, BC Parks, and Gatineau. Add supported type or length contrasts and known incompatible-site exclusions to the scenarios and cassettes. Record the specific capability or inventory limitation for any remaining fallback in `docs/development/PROVIDER_CASSETTES.md` per FR-010 and SC-001 (partial).
- [x] T018 Demonstrate a targeted year-boundary refresh from an expired original stay, using a controlled clock if needed. Verify the candidate offline and confirm another case for the same provider still replays. Capture the procedure and outcome in `docs/specs/20261125-220553-provider-availability-cassettes/quickstart.md` per SC-003 and US2/AC1 (partial).

## Phase 8: Convergence

- [x] T019 Validate the complete scenario inventory in `tests/providers/availability_cases.py` or `tests/providers/test_availability_cassettes.py` before replay or capture. Reject duplicate provider-qualified cassette keys, missing expected campsite IDs or nights, checkout on or before arrival, and expected nights outside the arrival-to-checkout interval. Add synthetic regressions showing that these cases fail by scenario key even when the provider has two distinct searches per T002, FR-003, and FR-007 (partial).
