# Standalone runtime review — 2026-10-28

Base: `7da9ea8` on `main`. Scope: preserve current application behavior while making the optional Python/SQLite runtime maintainable and safe to upgrade.

## Design decisions

Keep the single Python process, SQLite, bounded local consumers, shared provider engine, durable outbox, and explicit admin capabilities. They implement the requested small-instance deployment without rebuilding a broker or monitoring system. Keep distributed as the default and install its dependency extras explicitly in existing workflows.

Starting again against current main, use `db.availability` as the source of site preferences and qualifying stay blocks. Do not maintain a second date/stay implementation in the local runner. The shared engine now preserves current UTC expiration, campsite details, new-night detection, and summary/direct notification modes for both runtimes.

Treat a durable delivery as an actual summary or direct notification. The `delivery_key` distinguishes a saved scan's summary from individual site alerts. Summary payloads retain credential-free opening snapshots; delivery revalidates every site and recomputes its count under current dates and preferences. No remaining match skips the intent. Only qualifying new nights trigger a new intent.

An accepted external send and its acknowledgment are separate operations. When SQLite is busy during acknowledgment, retry only persistence, without repeating the HTTP request. Unexpected storage faults terminate the supervised consumer and fail readiness. Crash-after-acceptance duplicates remain possible and documented. Repeated target polling cycles get distinct job IDs; retries retain the cycle identity and target context remains separate.

Preserve the previous PR's migration rather than rewriting it. Merge `ef2486672984` and current-main `09367969f1a4` at `4d64e0e4ae18`, then rename the intent identity column. Fresh installs, populated current-main databases, and earlier PR databases can reach a single head while retaining pending payloads. Earlier direct payloads are still understood. Search migration verification explicitly downgrades to the pre-index schema and upgrades through the merge again; a relative `-1` is ambiguous at a merge revision and would not express the index boundary.

Default summary links to the Python listener, with explicit `CAMPLY_APP_URL` taking precedence for public HTTPS deployments and path prefixes. Clear obsolete output once before parallel workspace builds; do not pass per-package `--clear`, which can race while creating the shared output directory. Apply the same sequencing to release source distributions, whose existing regression seeds a stale archive and rebuilds every package. Validate pnpm 12’s multi-document lock YAML with its appropriate parser option and preserve uv’s generated lock formatting. Keep map worker assets, response compression, generated API types, release stamping/source distributions, dependency upgrades, and current distributed workflows intact.

## Regression evidence

Existing current-main summary/direct regressions initially failed against the rebased extraction, and `upgrade head` initially found two revision heads. Those failures drove the shared-engine and migration changes. New tests reproduced a busy acknowledgment after upstream acceptance and conflated job identities before their fixes.

The distributed admin smoke hands Uvicorn an already-bound socket, preventing a service from taking a guessed API port before startup. Metrics and synthetic upstream services allocate their ports before dependent listeners are chosen.

The expanded installed-wheel smoke uses a separate core-only environment outside the checkout, real SQLite, generated upstream HTTP, real cookies/CSRF, and Chromium. It verifies map discovery, stored campsite attributes, summary deep links, compressed immutable MapLibre worker assets, two subscriptions sharing one check, and persisted pending-delivery restart recovery. It rejects Celery/Redis/Prometheus/psycopg dependencies and imports.

Current verification results are recorded in [quickstart.md](quickstart.md#verification-evidence-2026-10-28). No visual baselines were changed. The snapshot run uses an isolated port to avoid reusing another worktree's development server.
