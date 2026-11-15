# Worker contract: Shared area coverage and alerts

This is a proposed internal contract shared by standalone and distributed adapters. Preserve public provider `find_availabilities(park_id=campground_id, ...)` and existing Celery campground task names.

## Coverage resolution

`camply.db.coverage` owns portable definition normalization, eligible-membership queries, scan-to-target subscriber queries and matching scope. It imports neither server nor worker. `camply.worker.engine.coverage` owns round reconciliation and progress; HTTP mutation code may call persistence helpers but never starts provider work.

1. Resolve confirmed membership by exact provider/area and enabled/reservable campground status. All mode has no result cap. Selected mode intersects the fixed IDs with eligible members; retain unavailable labels separately.
2. In a short transaction, check provider `catalog_revision` and scan `row_version`, atomically replace resolved links and advance `coverage_revision` if membership changed. Retry on concurrent publication/edit. Disabled/removed parent resolves empty coverage.
3. Reconcile on create/edit and before starting a new area round. Scan/catalog reads and delivery recheck live eligibility so newly excluded coverage cannot contribute between reconciliations. New catalog members join all mode by the next round, never selected mode.
4. One current area round captures the link set, round UUID/start/deadline and coverage revision. Reuse already successful observations within target cooldown; otherwise register shared attempts. Never force checks before cooldown solely to complete another scan's round.

## Scheduling and completion

- Due discovery uses `EXISTS` over live eligible scan links to select distinct shared targets. Preserve invite-only/date/suspension checks. Page work in both adapters (100 targets per discovery page), prevent queued/in-flight duplicates, and use existing local guards/distributed target locks.
- Dispatching retries remains one logical target check with multiple bounded attempts, not one check per subscriber. One shared attempt fans out to all registered current round members, each with its own preferences.
- Whole provider-check execution is bounded to 90 seconds; distributed lock TTL must be greater than or equal to 105 seconds. Retry delays remain 60/120/240 seconds standalone and the existing 60-second distributed delay, with at most four attempts. The distributed retry adapter must propagate retry requests rather than swallow them; round bookkeeping does not create an additional retry loop.
- A round deadline is `started_at + 2 * heartbeat_interval + 780 seconds`. It bounds abandoned queued work as well as attempts/retries. Before declaring an expired round member failed, refresh any committed outcome. Do not issue a compensating extra provider request. Fair paging and oldest-due-first ordering must let later members progress.
- Target success replaces its snapshot, records attempt completion, updates applicable round members and writes/appends area alert intents in one transaction. Empty success clears that target only. Failure records latest attempt/error and retrying/failed outcome, preserving the snapshot and last success.
- Completion updates require matching scan/coverage revision, current round UUID, and registered attempt UUID. A stale callback may update its valid shared observation but cannot complete a replacement round or enqueue intent for removed membership.
- Finish a round when each member succeeds or fails terminally/deadline-expires. Advance full-check time only for all-success current coverage. Terminal members plus pending members always account for the captured set; retrying is visible partial coverage, not a successful empty result.
- Startup recovers interrupted attempts, reconciles membership, and closes expired members without resetting valid completed observations. Replace current round state only when no round is open or its definition/coverage is superseded. Provider client cancellation/cleanup is mandatory.

## Notification aggregation and delivery

- The successful snapshot transaction considers only newly matching openings from eligible current subscriber coverage, using existing reopened/unchanged detection rules. Every candidate carries original target UUID, provider, campground, campsite, qualifying dates and attributes.
- Area summary candidates share one outbox row for `(scan ID, definition revision, channel, five-second UTC window)`; use deterministic detection identity, uniqueness and version/status/due-time compare-and-swap. No batching transaction spans provider or notification HTTP.
- Pending rows cannot accept candidates after their window end or after a delivery claim. A collision with a sealed row re-evaluates current window time and inserts/appends to the next eligible window; it never mutates a retry payload or resends an old window.
- Both runtimes poll due area delivery rows once per second independently of campground discovery. Distributed mode adds an area-outbox dispatch task on its own beat entry and atomic database claim; it does not route area summaries through legacy direct scan fan-out as well. Local mode extends the existing outbox consumer.
- At claim and immediately before send, revalidate current owner/access/channel, definition revision, date window/preferences, and every candidate's live coverage. Drop excluded/stale-definition candidates, then rebuild campground labels, distinct-site counts and the scan URL. No valid candidates means skipped delivery.
- Area direct mode retains one intent per newly matching site/detection, with real campground booking URL and qualified target validation. Legacy campground summary/direct processing and existing single-target outbox payloads keep their path.
- Area claims have a 45-second lease and delivery transport gets a 30-second budget. Only the atomic claim winner sends; retry scheduling begins after lease expiry or explicit completion. A small recovery scan handles expired area claims, never live ones. Preserve four attempts and 24-hour terminal pruning. Add no credentials or raw upstream errors to persisted payloads.
- The healthy-path target is delivery acceptance within 60 seconds of detection: up to five seconds of aggregation, one-second dispatch discovery, then existing queued delivery/transport. Synthetic timing checks isolate backlog and inject a healthy accepting sender. Outage/backlog/retry delays are reported and are not presented as meeting this objective.
- Exactly-once external receipt is not promised: a crash after provider acceptance and before acknowledgment may duplicate a delivery. Internal concurrent claims and retries preserve one logical intent.

## Observability and runtime bounds

Extend existing structured attempt/outcome reporting with destination kind, scan/target IDs, round/coverage revisions, pending/failed/complete coverage and summary-window/claim outcomes. Expose user-facing failure state from persisted data rather than process-only telemetry. Reuse existing instrumentation hooks; no new monitoring backend or unbounded metric labels are planned. Standalone queue/history bounds and optional dependency isolation remain intact.
