# Feature Specification: Continue destination enrichment after deployment

**Feature Branch**: `fix/enrichment-rollout`
**Created**: 2026-11-14
**Status**: Implemented and locally verified; release validation pending
**Input**: Merged and deployed enrichment shows no photos for Many Glacier on Recreation.gov.

## User Scenarios & Testing

### User Story 1 — Reach destinations beyond the initial batch (Priority: P1)

Visitors to destinations later in a provider's catalog receive available photos without an operator repeatedly syncing catalogs.

**Why this priority**: Many Glacier currently has no cached details despite having eight source photos. Only the first enrichment batch ran after deployment.

**Independent Test**: Seed more than 100 eligible synthetic destinations, run scheduled enrichment and its continuations, and verify the final destination gains details without another catalog import.

**Acceptance Scenarios**:

1. **Given** 205 eligible destinations without details, **when** background enrichment runs, **then** all destinations are attempted through bounded batches without manual intervention.
2. **Given** a completed initial catalog sync, **when** the scheduler runs again, **then** remaining details are refreshed without another full catalog download/import.
3. **Given** unsupported providers or fresh destinations, **when** enrichment runs, **then** no source HTTP requests or endless continuations occur.

### User Story 2 — Recover and remain responsive (Priority: P2)

Operators can rely on enrichment resuming after restart or temporary source failure while availability monitoring continues.

**Independent Test**: Fail one synthetic source, verify cache retention and later scheduled retry, and verify local consumers remain cancellable and other providers continue.

**Acceptance Scenarios**:

1. **Given** unavailable sources, **when** a refresh fails, **then** existing cache and cooldown behavior remain intact and an immediate failure loop does not occur.
2. **Given** a restarted scheduler, **when** it discovers existing stale records, **then** enrichment resumes automatically without a data migration or manual backfill.
3. **Given** local and distributed runtimes, **when** work remains, **then** both make automatic progress with the same provider logic.

### Edge Cases

- Concurrent refreshes retain atomic per-destination claims.
- Missing/reclassified source records enter the existing attempt cooldown rather than retrying continuously.
- Empty/fresh catalogs and unsupported adapters produce no continuation.
- One failing provider does not stop another provider or availability consumers.
- Shutdown cancels local enrichment cleanly and releases provider clients.

## Requirements

### Functional Requirements

- **FR-001**: Background enrichment MUST discover stale/missing details independently of daily catalog synchronization, at least once per configured heartbeat.
- **FR-002**: Each provider invocation MUST retain the existing maximum of 100 destinations and continue successful work while eligible destinations remain.
- **FR-003**: Continuations MUST run without repeating catalog ingestion and yield between batches.
- **FR-004**: Local and distributed runtimes MUST both resume work automatically and release HTTP clients after each batch.
- **FR-005**: Existing seven-day freshness, one-hour attempt cooldown, atomic claims, failure retention, provider/identity association, and cached-only page reads MUST be preserved.
- **FR-006**: Fresh, unsupported, or failed work MUST NOT create unbounded immediate retries; failures MUST remain observable and resume through periodic discovery.
- **FR-007**: The fix MUST require no new database migration, image hosting, public endpoint, or UI change.

### Key Entities

- **Destination snapshot**: Existing details and last-attempt fields; no schema change.
- **Enrichment batch outcome**: Provider identity, success/skip/error status, and whether more due work remains.

## Success Criteria

- **SC-001**: A synthetic 205-destination backlog completes in three successful batches without a second catalog import.
- **SC-002**: Both runtimes resume stale work after startup without operator requests.
- **SC-003**: Fresh and unsupported providers perform zero source requests; failed batches receive no immediate continuation.
- **SC-004**: Existing provider, API, migration, availability, and packaging checks continue to pass.

## Assumptions

- Observed deployment is `camply.rocks`; read-only public checks confirm the new backend and partial enrichment are deployed.
- Photos remain upstream URLs. Source availability varies, so a successful backfill does not guarantee every destination has photos.
- Worker and scheduler deployments will receive the follow-up release. No production credentials or database access are available in this workspace.
