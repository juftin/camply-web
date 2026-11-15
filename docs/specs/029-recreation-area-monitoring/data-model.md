# Data model: Recreation-area monitoring

All definitions below are proposed. No schema revision is generated in this planning change. Fields use existing portable SQLAlchemy UUID/date/UTC timestamp conventions; strings, JSON, and named checks replace new database-specific enum/array types.

## Saved definition: `user_scans`

Retain UUID, owner, timestamps, active preference, minimum stay, preferred types, and electric preference. Add the following:

| Field                                                         | Type and constraints                                    | Meaning                                                                                                                                |
| ------------------------------------------------------------- | ------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------- |
| `destination_type`                                            | String(24), non-null; `campground` or `recreation_area` | Explicit destination kind.                                                                                                             |
| `provider_id`                                                 | Integer, non-null, FK to providers                      | Identity scope.                                                                                                                        |
| `campground_id`                                               | String(128), nullable                                   | Nonempty only for campground destinations.                                                                                             |
| `recreation_area_id`                                          | String(128), nullable                                   | Nonempty only for area destinations.                                                                                                   |
| `destination_name`                                            | String(255), non-null                                   | Last known display name; survives unavailable metadata.                                                                                |
| `coverage_mode`                                               | String(16), nullable; `all` or `selected`               | Required for area destinations; null for campground destinations.                                                                      |
| `selected_campgrounds`                                        | JSON, non-null, default `[]`                            | Sorted unique objects containing `id` and last known `name`; fixed selection only. IDs are nonempty strings of at most 128 characters. |
| `start_date`, `end_date`                                      | Date, non-null; `end_date > start_date`                 | Scan-owned exclusive date window.                                                                                                      |
| `definition_hash`                                             | String(64), non-null                                    | SHA-256 of canonical identity below.                                                                                                   |
| `definition_revision`                                         | Integer, non-null, default 1; positive                  | Increments on saved definition, preference, or active-setting edits; invalidates queued stale user intent.                             |
| `coverage_revision`                                           | Integer, non-null, default 1; positive                  | Increments on destination/date/membership changes; guards current round callbacks.                                                     |
| `current_round_id`                                            | UUID, nullable                                          | Current area round; null for campground scans.                                                                                         |
| `round_started_at`, `round_deadline_at`, `round_completed_at` | UTC timestamps, nullable                                | One current round; no historical round table.                                                                                          |
| `last_full_checked_at`                                        | UTC timestamp, nullable                                 | Last full success for current coverage; clear when coverage identity changes.                                                          |
| `row_version`                                                 | Integer, non-null, default 1; positive                  | Compare-and-swap token for atomic edits and coverage publication.                                                                      |
| `target_id`                                                   | Existing FK to unique_targets, now nullable             | Compatibility pointer: actual target for campground scans, null for area scans.                                                        |

Named row checks enforce the destination alternatives: campground requires campground ID and target pointer, with area ID/mode absent and empty selection; area requires area ID, no campground ID/target pointer, and mode `all` or `selected`. JSON validation enforces `all` has no fixed choices and `selected` has at least one distinct ID. Date and positive-version checks are database-enforced. Matching preferences keep their existing representation and validation; no unrelated schema conversion.

Destination identifiers and selection labels are durable saved references, not cascading catalog foreign keys. This deliberately permits a removed destination to remain visible. Creation/edit validates provider-qualified membership transactionally; the resolved target's actual campground relationship retains its existing composite FK. No identifier is inferred from display name or converted to an integer.

Canonical identity is a versioned, unambiguous JSON tuple containing provider, destination type, destination ID, start/end ISO dates, mode, and sorted selected IDs (empty for campground/all). Labels and preferences are excluded. Unique `(user_id, definition_hash)` rejects duplicate definitions, including concurrent writes. Selected-all-current and dynamic-all remain distinct. Compare and deduplicate IDs after trimming surrounding whitespace; preserve case, leading zeros, compound IDs and exact native identity.

## Resolved coverage and frozen round membership: `scan_targets`

New association model in `src/camply/db/models/scan_targets.py`; all scans use it, including one link for a campground scan.

| Field                        | Type and constraints                                             | Meaning                                                                                                                                    |
| ---------------------------- | ---------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------ |
| `scan_id`, `target_id`       | UUID, composite primary key; FKs to scan/target                  | Exactly one link for each resolved campground/date target in a saved scan. Scan deletion cascades its links, never shared targets/results. |
| `coverage_revision`          | Positive integer, non-null                                       | Definition/membership version that produced this link.                                                                                     |
| `round_id`                   | UUID, nullable                                                   | Matches scan's current area round, null for campground scans.                                                                              |
| `outcome`                    | String(16), non-null; `pending`, `retrying`, `success`, `failed` | Current member outcome; failure is not an empty success.                                                                                   |
| `attempt_id`                 | UUID, nullable                                                   | Shared attempt registered for this round/link; late completions must match it.                                                             |
| `successful_at`, `failed_at` | UTC timestamps, nullable                                         | Current round member outcome time; target retains last successful snapshot independently.                                                  |
| `error_category`             | String(64), nullable                                             | Allowlisted error category, never a raw exception.                                                                                         |

Indexes cover `target_id` subscriber lookups and `(scan_id, round_id, outcome)`. The complete link set freezes membership for the current round. An edit, confirmed membership change, or parent unavailability supersedes the round and atomically replaces/clears links with a new coverage revision. Unavailable fixed choices remain in `selected_campgrounds`, not in eligible links. Membership publication checks the provider revision and scan row version in the same short transaction; if either changed, recompute rather than publish a mixture.

Read and delivery queries still intersect links with currently eligible catalog membership. Thus removed coverage stops contributing immediately even if reconciliation has not yet published its next round. A link cannot make an excluded target eligible by itself.

## Shared target attempt state: `unique_targets`

Keep existing identity/hash, campground composite FK, result rows and `last_checked_at` unchanged. Add nullable `attempt_id` UUID, `attempt_started_at`, `attempt_finished_at`, and `attempt_error_category` String(64). These describe the latest attempt only. Provider network work does not hold a write transaction. Success atomically replaces results, advances `last_checked_at`, records member outcomes and creates/appends area delivery intent. Failure records attempt/member status without deleting results or changing successful-check time. Retry registration and terminal failure use the same attempt/round guards.

A provider check that fails before reaching the provider is still a failed attempt. Interrupted attempts become visible retrying/failed coverage during recovery. Shared target rows stay dormant when no eligible links exist; removing one scan never deletes another's observations.

## Confirmed publication: `providers`

Add `catalog_revision` Integer, non-null, default 0, nonnegative. Increase only inside a successful complete metadata/search publication. Coverage writers condition their publication on the revision observed while resolving membership; catalog publication and that revision check serialize through the provider row. Reconciliation retries changed snapshots. SQLAlchemy application-level version checks alone are not a substitute for guarding bulk writes on both databases.

## Durable area intent: `notification_outbox`

Reuse the existing table, statuses, attempt budget, due/finished indexes, and pruning. Add `payload_kind` String(24), non-null default `campground`, values `campground` or `area`; nullable positive `scan_revision`; and positive `payload_version` Integer default 1. Area payloads contain only qualified target/site opening data and display metadata, never credentials. Area rows have nullable `target_id`; single-target rows retain their original guard.

For an area summary, derive `detection_id` deterministically from scan ID, definition revision, channel and five-second UTC window start; `delivery_key` is `area-summary`. Existing unique `(detection_id, scan_id, delivery_key)` gives one row per window/channel. `next_attempt_at` initially equals window end. Append unions candidates by target/site/stay identity using a version/status/due-time conditional update. A failed conditional update retries against current time and version; it never reopens a sealed payload. Claims atomically move one due row to `sending`; only the winner sends. Area direct mode uses the original detection and a provider/campground/site-qualified delivery key.

Current dates, filters, owner access, channel, definition revision and live membership are checked per candidate before delivery. Candidates from removed coverage are dropped and the summary is rebuilt. Empty summaries are skipped. Recovery must reclaim expired area delivery claims without resetting a live worker's send; persist a claim lease in the area payload and use existing finite retries. Legacy campground intents remain readable and keep their current delivery path.

## State transitions and persistence limits

- Saved coverage: valid → unavailable → valid without losing active preference or fixed selection; no availability work while unavailable.
- Round: created with frozen eligible links → pending/retrying members → complete success or complete with failures. Deadline failures close remaining pending members. New rounds replace the current header/member outcome fields; they do not accumulate history.
- Revision change: supersede old round and queued definition-specific intent. A stale callback can update its valid shared target snapshot but cannot mark a replacement round complete or notify through removed coverage.
- Round full success requires success for every captured member, using either its registered successful attempt or a still-fresh observation within existing target cooldown. Opening a round never forces an early provider check.
- Outbox: pending (appendable until window end) → sending (sealed) → sent/retry/skipped/failed. Retries preserve one logical intent identity. Terminal records retain the existing 24-hour cleanup; pending retries survive restart.

## Migration and rollback

1. Stop all runtime roles. Preflight current campground definitions for duplicates; fail before mutation with a non-sensitive diagnostic if uniqueness cannot be established. Do not delete subscriptions.
2. Add portable columns, provider revision and association table. Backfill each old scan from its existing target and campground, with `destination_type=campground`, null area/mode, empty selection, canonical hash, and one link. Preserve scan/target/result UUIDs, timestamps, preferences and outbox payloads.
3. Add named checks/unique indexes after backfill. SQLite reconstruction must preserve inbound outbox foreign keys and named checks; use the existing migration connection strategy, restore enforcement, and run foreign-key validation before startup. Test populated PostgreSQL independently.
4. Validate old responses and pending intents, then deploy matching API/worker/frontend versions together. No mixed old/new worker rollout.
5. Downgrade is lossless only when no area scans or area intents remain. Refuse otherwise before mutating schema; use a pre-upgrade backup for a full rollback that includes area state. Test campground-only downgrade/re-upgrade and refusal with area data. Packaged migrations must work outside the checkout.
