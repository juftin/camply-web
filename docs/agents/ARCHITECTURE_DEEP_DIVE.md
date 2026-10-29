# ARCHITECTURE_DEEP_DIVE: The Smart De-duplicated Poller

This document explains the technical implementation and reasoning behind the core scanning engine of `camply`.

## Python package boundaries

The Python backend is one `camply` distribution with internal
`camply.providers`, `camply.db`, `camply.server`, and `camply.worker`
subpackages. Base includes providers and SQLite; `server`, `distributed`,
`postgres`, and `sentry` independently add runtime dependencies. Server and
worker application bootstrap must remain independent. Existing
Celery JSON task names, beat schedule names, and database revisions are
preserved through the module migration.

## Optional local execution

`camply.worker.engine` contains shared asynchronous discovery, scanning/filtering, catalog, and notification functions. Distributed Celery adapters keep locks, retries, and metrics; `camply.worker.runtime` runs the same engine in the API lifespan for standalone. Discovery begins immediately, pages 100 targets, honors subscriber eligibility and cooldown, and excludes queued/running/deferred targets. One scan consumer retries exceptions after 60/120/240 seconds, then records a failure and waits for the next heartbeat cycle. Separate consumers handle catalog work and durable delivery without creating one task per target.

Manual catalog sync coalesces under one job ID; daily refresh runs at midnight UTC. Each provider has an independent outcome, and later providers run after a failure. Recreation.gov archive parsing is offloaded from the event loop. Existing provider commit boundaries are preserved. Shutdown stops discovery, allows up to five seconds to drain scan/catalog queues, then cancels and reaps remaining loops. Any unexpectedly terminated supervised loop makes readiness unhealthy.

Standalone result replacement, successful-check time, and matching notification intents commit in one transaction. The delivery consumer revalidates current subscriptions, credentials, dates, and filters before sending; see [notification recovery](DESIGN_NOTIFICATIONS.md#standalone-delivery). Local queues/history are bounded; only pending delivery and application state persist. This runtime supports one process, one host, and a writable local SQLite file. Distributed scheduling and deployment remain available for larger instances.

## 🎯 The Problem: API Bans & Inefficiency

In a multi-user system, multiple users often want to watch the same popular campgrounds (e.g., Lower Pines in Yosemite) for the same dates.

- **Legacy Approach**: 10 users = 10 API calls every minute. **Result**: IP ban from Recreation.gov.
- **Smart Approach**: 10 users = 1 API call every minute. **Result**: High performance and API safety.

---

## 🏗️ The Data Flow (User to Alert)

```mermaid
graph TD
    A[User in React UI] -->|POST /scans| B(FastAPI Backend)
    B -->|Calculate Hash| C{Unique Target Exists?}
    C -->|No| D[Create New UniqueTarget]
    C -->|Yes| E[Link UserScan to Existing]

    F[Celery Beat Scheduler] -->|Every 5m (default)| G[Identify Targets to Check]
    G -->|Enqueue| H[camply.search.check_campsite_availability Task]

    H -->|Hit Provider API| I[Raw Results]
    I -->|Update Cache| J[scan_results Table]

    J -->|New Opening Found| K[Fan-out: Match UserScans]
    K -->|User A matches| L[Enqueue camply.notifications.send_pushover_notification]
    K -->|User B matches| M[Enqueue camply.notifications.send_pushover_notification]

    L -->|Pushover API| N[User Mobile Alert]
```

---

## 🔄 The `UniqueTarget` State Machine

A `UniqueTarget` represents a background polling job. Its lifecycle is:

1.  **Initialized**: Created when the first user subscribes to a park/date range.
2.  **Active**: `is_active=True`. Polled by the worker as long as at least one linked `UserScan` is active.
3.  **Cooldown**: After a check, `last_checked_at` is updated. It won't be checked again until the provider's `rate_limit_interval` has passed.
4.  **Dormant**: If all users delete their scans for this target, `is_active` becomes `False`. The record remains for history but the worker skips it.

---

## 📣 The "Fan-out" Notification Logic

We separate **Checking** from **Notifying** to ensure high throughput.

1.  **The Poller** is "Blind": It just wants to know "What sites are open for Park X between Date A and B?".
2.  **Standardization**: Raw results are converted into `CampsiteDTO`s.
3.  **Matching**: The worker queries the `user_scans` table for that `target_id`.
4.  **Filtering**:
    - _User A_ only wants **Electric** sites.
    - _User B_ wants **any** site but for **3+ nights**.
    - The worker checks the `CampsiteDTO` list against these filters.
5.  **Individual Alerts**: A user is only alerted if their specific criteria are met, even if other sites are open.

---

## 🔒 Concurrency & Locking

To prevent race conditions (two workers checking the same park simultaneously):

- We use **Valkey Distributed Locks**.
- Before a `camply.search.check_campsite_availability` (`check_target_availability`) task starts, it attempts to acquire a lock: `lock:target_id`.
- If the lock is held, the task exits immediately.
