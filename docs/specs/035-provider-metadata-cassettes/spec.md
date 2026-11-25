# Feature Specification for Provider Metadata Cassettes

**Feature** — 035-provider-metadata-cassettes

**Created** — 2026-11-25

**Status** — Draft

**Input** — Extend recorded provider coverage to campground discovery, recreation-area expansion, enrichment, catalog sync, and campsite metadata.

## User Scenarios & Testing

### User Story 1 — Discover and resolve destinations (P1)

A maintainer can replay public responses and detect changes to campground search, exact lookup, and recreation-area membership.

**Independent test** — Run discovery replay offline for Recreation.gov, ReserveCalifornia, Washington State Parks, and ReserveAmerica.

1. Recorded search and exact campground lookup return the expected native ID, normalized name, location, and public booking URL.
2. Exact area lookup and expansion return the expected overnight campgrounds with matching parent IDs and exclude recorded ineligible destinations.
3. ReserveAmerica preserves the contract-qualified campground ID and returns a campground without a recreation-area parent.

### User Story 2 — Refresh destination enrichment (P2)

A maintainer can verify that provider photos and practical information are attributed to the correct destination and survive incomplete responses.

**Independent test** — Replay an enrichment case for each supported family into temporary storage and inspect the saved snapshot.

1. A recorded refresh associates a known photo URL and selected practical information with the expected campground or recreation area.
2. An incomplete or failed response preserves the last successful snapshot.

### User Story 3 — Verify catalog persistence and campsite attributes (P3)

A maintainer can replay a compact provider catalog and verify the records used for discovery and campsite filtering.

**Independent test** — Sync representative catalogs to temporary SQLite and replay campsite listing.

1. A successful sync stores the expected identities, parent relationships where applicable, reservability, and discovery rows.
2. An incomplete refresh preserves the previous successful catalog.
3. Listing returns independently verified equipment type, maximum vehicle length, hookups, or accessibility where supplied.

### Edge Cases

- Preserve meaningful pagination and parent relationships. Area and campground IDs can overlap in the upstream source.
- Fix a browse date where a campsite listing uses the current date.
- Verify each family's supported entity types. ReserveAmerica has no parent recreation areas. GoingToCamp has no enrichment path.

## Requirements

- **FR-001** — Replay discovery and exact campground resolution for one representative deployment per provider family with independently verified outputs.
- **FR-002** — Verify exact area lookup and eligible overnight expansion for Recreation.gov, UseDirect, and GoingToCamp, plus the unparented ReserveAmerica behavior.
- **FR-003** — Replay enrichment for Recreation.gov, UseDirect, and ReserveAmerica on their supported entity types. Verify photo attribution, practical fields, and preservation of a good snapshot on incomplete refresh.
- **FR-004** — Replay compact catalog sync per family into isolated storage. Assert identities, relationships, reservability, discovery rows, and preservation after a failed refresh.
- **FR-005** — Replay campsite listing per family. Assert the expected native ID and representative capabilities. Fix the clock for date-dependent requests.
- **FR-006** — Collect the cases in the normal backend suite and replay offline. Missing fixtures or unmatched requests fail. Keep public response data and synthetic session placeholders in fixtures, with independently maintained expectations.
- **FR-007** — Document verification sources, case IDs, inputs, fixture paths, last verified dates, and how to stage and review a single replacement while preserving the last good fixture.

## Success Criteria

- **SC-001** — Four discovery cases pass offline and three verify recreation-area expansion.
- **SC-002** — The three enrichment-capable families produce the expected snapshots. The incomplete refresh preserves prior details.
- **SC-003** — Four catalog sync and campsite listing cases verify persisted relationships and site attributes.
- **SC-004** — One metadata case can be refreshed and replayed offline while companion fixture checksums remain stable.

## Assumptions

- The first delivery uses one representative deployment per family.
- The seasonal availability backlog is tracked in [Spec 034](../034-provider-availability-cassettes/spec.md).
