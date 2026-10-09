# Feature Specification: Admin UI

**Status**: Planned — no application implementation yet.
**Date**: 2026-10-08

## Agreed scope

Administrators can view users and their saved campsite scans, suspend or restore a user's scanning access, and pause or resume individual scans. Administrators have read-only visibility into Celery. The frontend communicates exclusively with FastAPI; the backend queries PostgreSQL, Celery, and Valkey. Sentry is excluded from this feature.

The admin overview includes graphs for user growth, saved scan creation and activity, campground lookup request volume, and background polling outcomes. FastAPI queries the existing Prometheus service for historical aggregates; the frontend never connects directly to Prometheus.

The Admin UI replaces Grafana as the application's administration and monitoring interface. Relevant existing dashboard capabilities must be available here before removing the Grafana service and provisioning. Prometheus remains the internal history store.

Disabling a user does not block login. It suspends polling and notifications for their scans and prevents scan creation or resumption. Saved scans and their individual active/paused settings are preserved. Re-enabling restores eligibility for previously active scans. Shared polling continues for other eligible subscribers.

## User stories and acceptance scenarios

### US1 — Manage users and scanning access (P1)

- An administrator can search and paginate users and view each user's saved scans, creation date, early-access status, scanning status, and notification configuration presence.
- Disabling a user prevents new scans and resumption through both the normal API and admin API; the user can still log in, view scans, update their profile, edit scan filters, pause scans, and delete scans.
- Tasks queued before suspension check eligibility at execution and skip work for disabled users. Shared targets with another eligible subscriber continue.
- Re-enabling preserves scans paused before or during suspension.
- Non-admin users cannot read or change other users through admin endpoints.

### US2 — Inspect and manage scans (P1)

- An administrator can paginate and filter all scans by owner, provider, saved active state, effective suspended state, and stale target state.
- Scan detail includes owner, campground, dates, filters, latest cached results, last successful check, and shared target.
- Target detail shows its subscribers and eligible subscriber count. Pausing one scan does not pause other subscribers.
- UI distinguishes a scan's saved active setting from its effective eligibility.

### US3 — Observe background work (P1)

- An administrator can see responding workers, active/reserved/scheduled tasks, ready queue depth, recent task outcomes, and the last completed target-discovery run.
- Task detail shows task ID, task type, timestamps, duration, worker, retry information where available, application outcome, and safe links to related targets/users/scans.
- Returned error payloads are shown as application failures even when Celery reports success. Skipped work and retries have distinct states.
- Partial worker responses, broker failures, expired results, and missing history appear as unavailable or unknown, not zero activity or healthy status.
- No admin endpoint retries, cancels, revokes, purges, enqueues, or changes scheduling. Inspection request/reply traffic is permitted.

### US4 — Understand usage and operational trends (P1)

- Administrators can select the last 24 hours, 7 days, or 30 days and view time-series graphs for total/new users, scans created, saved active versus effectively eligible scans, and eligible shared polling targets.
- Campground lookup requests are labeled separately from saved campsite scans; request volume is not a count of unique searches or people.
- Operational graphs show executed provider checks, application outcomes, task duration, and successful notification deliveries, using correctly defined metrics.
- Charts show units, bucket size, timezone, last available sample, and accessible tabular values. Missing samples and unavailable history are distinguished from measured zero.
- Historical user/scan totals come from samples captured at the time, not reconstruction from surviving database rows. Deleted scans do not erase past sampled trends.
- Suspending users reduces effective scan activity without altering saved active scan counts. Celery monitoring remains read-only.
- Administrators can inspect API traffic/errors/latency, task throughput/outcomes/duration, discovery/enqueue rates, results/notifications, lock contention, and provider errors without opening Grafana.
- Backend/worker scrape health and actual responding Celery workers are presented as distinct signals. Ratios without observations are unavailable, not fabricated success rates.

## Proposed implementation defaults

These are design choices for the first release, rather than additional user requirements:

- Database `is_admin` flag; bootstrap the configured basic/local owner and provision Auth0 administrators explicitly by immutable user ID.
- Recent task history retained in Valkey for up to 24 hours and at most 1,000 execution records. This is bounded operational history, not a durable archive.
- At high volume the record cap shortens that window; the UI shows actual available coverage and truncation. Trends retain their separate Prometheus history.
- Admin writes recorded in a database audit table in the same transaction as the change.
- Trends use the existing Prometheus deployment and its 30-day retention; new series begin when instrumentation is deployed. No durable per-search analytics events are required.
- No role-management UI, early-access approval workflow, user impersonation, provider controls, or notification credential editing in this release.

## Success criteria

- Authorization tests reject every admin endpoint for non-admin users.
- Suspension tests cover creation, resumption, discovery, queued checks, fan-out, and queued notification delivery.
- Shared-target tests prove other subscribers continue receiving checks and alerts.
- Operations tests prove bounded responses during dependency outages and accurate distinction between Celery state and application outcome.
- Frontend tests cover user suspension/restoration, scan navigation, route protection, and partial/unavailable operations data.
- Trend tests verify metric definitions, time buckets, multi-worker aggregation, missing history, and graphs for all supported ranges.
- All 24 existing Grafana panels have a verified equivalent in the Admin UI, with duplicate panels consolidated and misleading definitions corrected; the final deployment contains no Grafana service or provisioning.
- `task lint`, `task check`, and `task test` pass before application implementation is finalized.
