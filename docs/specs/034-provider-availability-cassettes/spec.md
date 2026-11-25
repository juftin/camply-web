# Feature Specification: Provider Availability Cassettes

**Feature Branch**: `provider-cassette-spec`

**Created**: 2026-11-25

**Status**: Draft

**Input**: Add cassette-backed availability searches for every provider, including different equipment requests, verify the returned campsites, and document how to find new open dates and refresh the recordings.

## User Scenarios & Testing

### User Story 1 - Verify availability for every provider (Priority: P1)

A contributor runs the provider integration suite and sees whether camply correctly translates each booking system's responses into available campsites and nights.

**Why this priority** — An empty result or an incorrect date can silently cause camply to miss a booking opportunity.

**Independent Test**: Run the provider suite with network access disabled and confirm that every registered provider has multiple passing positive availability cases, including distinct equipment requests where supported.

**Acceptance Scenarios**

1. **Given** a cassette from a search with verified availability and fixed search inputs, **when** the normal provider availability check runs, **then** it returns a known campsite and its expected available nights.
2. **Given** a provider returns an empty result, drops the expected site or night, or includes a checkout date as an available night, **when** that case is replayed, **then** the test fails and identifies the provider and the mismatch.
3. **Given** a cassette is missing or a request differs in a way that changes which provider, campground, or date range it queries, **when** the suite runs, **then** the affected case fails without contacting the booking system.
4. **Given** a provider is added to the registry, **when** the suite checks coverage, **then** it names the provider and reports any shortfall in the required scenarios.
5. **Given** recorded availability includes sites with different equipment compatibility, **when** a maintainer replays tent and vehicle requests, **then** each request returns its expected available sites and nights and excludes any known incompatible site.

### User Story 2 - Refresh a provider's cassette (Priority: P2)

A maintainer follows a provider-specific guide to find a currently bookable stay, update the search inputs and expected results, and verify the replacement cassette offline.

**Why this priority** — Booking windows and park seasons change. A maintainer needs to be able to repeat the capture without rediscovering how the booking site works.

**Independent Test**: Using the guide, refresh one provider with an expired or closed search window. Confirm an open stay on the booking site, record the new search, then replay it offline while the provider's other scenarios continue to pass.

**Acceptance Scenarios**

1. **Given** the old stay date has passed, **when** the maintainer follows the provider's booking link and availability instructions, **then** they can locate an open stay within the current booking window and update the campground ID, check-in and checkout dates, and expected result as needed.
2. **Given** an open stay has been confirmed, **when** the maintainer records that provider's search, **then** they can review the replacement for sensitive data and replay it offline without replacing unrelated scenarios for the same or other providers.
3. **Given** the campground is closed, sold out, or the upstream service is unavailable, **when** the maintainer attempts a refresh, **then** the guide explains how to choose another viable campground or defer the refresh while preserving the last passing cassette.

### Edge Cases

- A date in the next calendar year may fall outside the provider's booking window or campground season. Check the public availability calendar before changing a year or substituting dates.
- A campground can appear bookable in the browser and sell out before recording. Confirm that the captured search still contains a known available site and night before accepting the replacement.
- Some providers require a booking category, equipment selection, parent park, or contract-qualified identifier to reproduce the search. Capture any such inputs in the provider's instructions.
- Some providers expose a single equipment category or omit equipment filters or length data. Document the supported choices and use distinct known-open searches for any remaining cases.
- Fixed fixture dates eventually become historical. Offline replay continues to verify the recorded result after the stay dates pass.

## Requirements

### Functional Requirements

- **FR-001** — Cover every registered provider with at least two distinct, successful cassette-backed campground availability searches. The starting inventory is 26 providers across Recreation.gov, UseDirect, GoingToCamp, and ReserveAmerica, including each regional variation.
- **FR-002** — Choose each scenario by confirming at least one available overnight campsite on the provider's public booking site for the same campground, dates, and applicable search options. Exercise camply's normal provider availability path and replay the provider interactions it needs to produce the result.
- **FR-003** — Require a non-empty result and assert a specific campsite identity, an expected normalized field such as campsite name or type, and that site's expected available nights within the requested interval. Verify that no returned night falls outside the interval, with checkout excluded. Assertions must be independent of the result produced by the test itself.
- **FR-004** — Run the coverage in the normal backend test suite and CI using checked-in cassettes. Replay must work without network access or provider credentials and must report missing or mismatched recordings as failures. Historical search dates must remain replayable.
- **FR-005** — Check the scenario inventory against the provider registry and report by name any provider with fewer than two positive scenarios or missing required equipment coverage.
- **FR-006** — Publish one refresh guide in the developer documentation with a provider-specific entry for every scenario. Each entry must include a direct public booking or availability URL, navigation steps to find open nights, the current campground name and native ID, equipment category and length when applicable, other required search options, where to update dates and expected results, and where to find the test and cassette. Include how to choose a replacement campground if the original is unsuitable.
- **FR-007** — Document a targeted refresh procedure covering booking-window and season checks, confirmation of an open site, updates to search inputs and expected results, recording the selected scenario, review of the fixture diff, and offline verification. Include a year rollover example that checks the new dates on the booking site before recording.
- **FR-008** — Use public inventory searches as the evidence for refreshes and synthetic data for any test identities or session values. Committed cassettes must be free of credentials, live session material, and personal information. A failed refresh must leave a passing historical cassette available for replay.
- **FR-009** — Document the existing 30-day review cadence and an additional refresh trigger when a provider changes its upstream responses or booking flow. Record the last successful verification date for each scenario and explain how to note a deferred refresh.
- **FR-010** — Use different equipment requests when supported. Include a tent request and an RV or trailer request with a specific length where those options are supported. When only one equipment category is supported, use two supported lengths if available. Exercise equipment constraints through the normal availability and matching path, whether applied by the provider or by camply using returned site data. Verify an expected compatible site and its available nights for each request. Where equipment matching is supported, verify that a site known to be available from the same or another recorded search is excluded because of its equipment type or length. Where there is no second supported equipment request, document the limitation and vary the campground or dates.

### Key Entities

- **Provider scenario** — A registered provider, campground identity, fixed arrival and checkout dates, required search options, and independently verified expected campsite fields and nights.
- **Cassette** — Replayable request and response data for one provider scenario, captured from its verified search and prepared for source control.
- **Refresh entry** — Provider booking URL, instructions for finding an available stay and updating the scenario, and the date of its last successful verification.

## Success Criteria

### Measurable Outcomes

- **SC-001** — Every registered provider has at least two passing positive scenarios and a refresh entry for each. The initial delivery covers all 26 registered providers with at least 52 scenarios and verifies compatible results and incompatible-site exclusions wherever equipment matching is supported.
- **SC-002** — All scenarios pass with network access disabled, including when replayed after their stay dates. Altering the expected site or nights, or removing a cassette, produces a failure that identifies the affected provider.
- **SC-003** — A maintainer can use the guide to replace an expired scenario across a year boundary, verify the new expected result, and pass offline replay. Demonstrate this by refreshing one scenario while another scenario for the same provider continues to replay.
- **SC-004** — Every committed scenario has a dated verification record and its cassette passes review for credentials, session material, and personal information.

## Assumptions

- A search means checking overnight campsite availability for a known campground. Destination discovery, full catalog sync, and booking completion are outside this feature's scope.
- Maintainers perform live verification and recording as an explicit maintenance step. The existing 30-day review policy supplies the schedule. Refreshes depend on a reachable provider and a publicly verifiable open stay.
- Existing replay and unit tests can contribute coverage where they meet these requirements. The feature uses a representative set of equipment requests and booking scenarios per provider.
