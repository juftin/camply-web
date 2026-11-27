# Research: Recreation-area monitoring

**Date**: 2026-11-15. Repository inspection and design only; no application behavior has been implemented.

## Clarification review

No critical ambiguities detected worth formal clarification. No questions were asked. The built-in specification checklist remains 16/16 passing; no checkbox state changed.

| Coverage category             | Result                                                                                 |
| ----------------------------- | -------------------------------------------------------------------------------------- |
| Functional scope and behavior | Clear: one area, all eligible members or a fixed selection.                            |
| Domain and identity           | Clear: provider-qualified destinations, fixed selections, independent site identities. |
| Interaction and lifecycle     | Clear: creation, editing, access, pause/delete, unavailable choices.                   |
| Quality attributes            | Clear at requirement level; concrete timing and concurrency decisions below.           |
| Integration and dependencies  | Clear: existing providers, catalog, notifications, both runtimes.                      |
| Failure and recovery          | Clear: preserve observations, partial coverage, membership recovery.                   |
| Constraints and tradeoffs     | Clear: retain campground scans and existing package boundaries.                        |
| Terminology                   | Clear: saved scan, eligible coverage, monitoring round, notification window.           |
| Completion signals            | Clear: SC-001–SC-007 and story acceptance scenarios.                                   |
| Placeholders                  | None.                                                                                  |

## R1. Preserve the campground target as the polling unit

**Evidence**: `src/camply/db/models/unique_targets.py` hashes provider, campground, and dates. `user_scans.py`, `worker/engine/discovery.py`, `worker/engine/scanner.py`, `worker/outbox.py`, and `server/routers/admin.py` join directly through one `UserScan.target_id`.

**Decision**: Keep existing targets, hashes, results, and provider availability calls. Add `scan_targets` for all saved scans. Store destination, dates, and fixed selections on `UserScan`; retain nullable `target_id` solely as a compatibility pointer for campground scans. Central coverage queries replace single-target subscriber joins.

**Rationale**: One target observation serves every overlapping scan. Independent scan definitions preserve unavailable selections and user identity.

**Alternatives considered**: An area target would duplicate checks already requested by campground scans. Hidden child user scans would distort counts, controls, and alert preferences. Retaining two independent polling paths would duplicate eligibility rules.

## R2. Persist only current coverage and round state

**Decision**: Store the current round header on `UserScan` and its frozen member outcomes on `scan_targets`; do not add a round-history subsystem. Use round UUIDs, definition revisions, and target attempt UUIDs to reject stale callbacks. Preserve last successful observation separately from latest attempt failure.

**Rationale**: FR-013 requires durable coverage status, not historical round browsing. A shared attempt can satisfy multiple captured rounds without another provider request. Due-target cooldown remains authoritative; a recently successful observation within cooldown may satisfy a newly opened round without a forced recheck.

**Alternatives considered**: Queue telemetry alone disappears on restart. Separate persistent round/header/member histories add storage and cleanup work without a requested user outcome.

## R3. Confirm membership through atomic catalog publication

**Evidence**: Recreation.gov's `provider.py::populate_database()` calls area and campground import helpers that each commit independently; absent records are not disabled. UseDirect and GoingToCamp already fetch before their metadata/search transaction and disable absent rows. `worker/engine/catalog.py::populate_provider()` enriches after metadata publication.

**Decision**: Parse and validate the complete Recreation.gov datasets before writing, make its import helpers participate in one caller-owned metadata/search transaction, and soft-disable absent records only after complete input validation. Preserve existing atomic publication for other providers. Treat enrichment failures independently. Serialize each provider's catalog publication with coverage reconciliation using its provider row as the publication revision guard; scan reconciliation retries if that revision changes.

**Rationale**: Reading a partially committed catalog cannot satisfy the spec's last-confirmed-membership rule. A second catalog cache is unnecessary. The provider publication revision makes concurrent scans of membership detect a changed snapshot on both databases.

**Alternatives considered**: Reconciling solely when a sync task reports success is insufficient if an earlier stage already committed. Treating a failed enrichment as failed membership would mislabel valid catalog updates.

## R4. Define bounded attempts and coverage rounds

**Evidence**: There is no universal whole-check deadline in current code. Distributed locking defaults to 120 seconds; target retries are three additional attempts with a 60-second delay. Standalone retries after 60/120/240 seconds. Neither lock expiry nor an HTTP request timeout bounds a whole logical check.

**Decision**: Plan a 90-second whole provider-check budget, excluding queue wait, with the existing maximum of four attempts and existing runtime-specific backoffs. Validate that a configured distributed lock lease exceeds the check budget by at least 15 seconds. Cancellation closes the provider client and cannot commit a partial snapshot. Record failures without advancing `last_checked_at`. A round member has an absolute deadline of round start plus two heartbeat intervals plus 780 seconds: 780 is four 90-second attempts plus the longer existing 60/120/240 retry schedule. This also bounds queue starvation; queued work beyond that deadline becomes a visible failed member, not a false empty success. A later successful shared check may satisfy a later round.

**Rationale**: Bounded attempt and round state prevent one hung request or abandoned job from leaving coverage pending forever. Existing provider pacing and transport retries fit inside the attempt budget. This is a new explicit bound, not a claim about existing behavior.

**Alternatives considered**: Waiting for all retries with no deadline can stall forever after a worker crash. Using lock TTL as a timeout permits overlapping checks after lease expiry. A new user-facing timeout control is unnecessary.

## R5. Reuse the durable outbox for bounded area summaries

**Evidence**: Standalone commits results and notification intents together. Distributed campground alerts dispatch through Celery after commit. Outbox delivery currently requires one original target and reapplies dates/preferences.

**Decision**: For area summaries only, aggregate credential-free qualified opening candidates into an outbox row keyed by scan, definition revision, selected channel, and a fixed five-second UTC window. A database uniqueness key and compare-and-swap payload version serialize concurrent appends. A row is appendable only while pending and before its window closes. Atomic delivery claims seal the payload; late detections enter the current next window. Both runtimes service due area outbox rows at least once per second independently of availability heartbeat. Keep existing campground summary/direct paths and area direct-alert semantics.

**Rationale**: Five seconds leaves scheduling/delivery budget inside the existing 60-second objective without waiting for a large area's checks. Reusing the outbox avoids an additional batching table. Network calls stay outside write transactions.

**Limits**: The 60-second target is measured with healthy scheduling and notification transport, not during outages or retry backoff. The guarantee is one logical intent per window/channel, not exactly-once external receipt after an accepted send followed by a crash. Existing four-attempt retry and 24-hour terminal retention apply. Area direct alerts use qualified original target candidates and the same delivery guards, without summary-window aggregation.

## R6. Add compatible scan contracts and complete selection discovery

**Evidence**: Existing schemas require `campground_id`. The area-child metadata endpoint returns an unpaged array, including unavailable campgrounds. `ScanForm.tsx` filters out areas; `FoundCampsites.tsx` keys/counts only by campsite ID; `ScanDetail.tsx` always fetches campground metadata.

**Decision**: Add explicit destination/coverage fields while accepting legacy campground requests. Add a separate paginated eligible-choice endpoint; do not change the existing metadata array. Persist selection labels independently from catalog foreign keys. Match per target first, then union qualified site identities. Add nullable area-compatible fields to existing scan/admin responses and regenerate types. Full details are in [scan contracts](contracts/scans.md) and [UI contracts](contracts/ui.md).

**Alternatives considered**: Empty or fabricated campground IDs hide destination type. Changing the old child endpoint shape breaks existing pages. Search-page results cannot serve as exhaustive membership.

## R7. Portable migration and concurrency

**Decision**: Use portable UUID/date/string/JSON fields, named constraints, unique normalized scan definitions, and compare-and-swap updates for definition, coverage publication, and outbox append/claim races. Backfill old scans in place. Abort before mutation if legacy duplicate definitions prevent the new unique constraint; never delete or merge them silently. Refuse downgrade while area scans remain; campground-only upgrade/downgrade/re-upgrade must preserve identities.

**Supporting primary documentation**: SQLAlchemy documents [association objects](https://docs.sqlalchemy.org/en/20/orm/basic_relationships.html#association-object) for relationships with extra state and [version counters](https://docs.sqlalchemy.org/en/20/orm/versioning.html) for stale-update detection. Alembic documents [SQLite batch migrations and referencing foreign keys](https://alembic.sqlalchemy.org/en/latest/batch.html). Explicit compare-and-swap predicates remain necessary for bulk updates; ORM versioning alone does not cover them.

**Rationale**: PostgreSQL row locks alone do not supply equivalent SQLite correctness. Alembic batch rebuilding must account for tables such as the outbox that reference user scans, restore named constraints, and validate foreign keys before reopening runtime traffic.
