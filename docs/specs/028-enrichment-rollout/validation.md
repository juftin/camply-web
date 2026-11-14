# Enrichment rollout verification

## Production diagnosis (read-only)

The deployed backend exposes the new enrichment schema and version 2.20.0. Many Glacier's public cached endpoint, `/api/campground/1/251869`, returned `details: null`, while earlier Recreation.gov campground IDs had populated photo snapshots from the startup sync. The existing RIDB archive produces eight validated Many Glacier photos; a direct source-image request returned HTTP 200. No production database or administrative operation was performed.

The missing continuation is reproducible from the original control flow: one 100-destination batch per full daily catalog sync, with no separate discovery or continuation. Both standalone and Celery now resume existing stale work independently of catalog ingestion.

## Local checks

- Test-first: the three shared-engine regressions failed before implementation; runtime/task/schedule regressions also failed before their implementation.
- All 42 focused engine/runtime checks passed; broader worker/provider/standalone-admin checks passed with 156 tests and six opt-in skips.
- `task test` passed end to end: 17 release checks, 1,428 backend tests with 23 opt-in skips, 81 installed-package tests, 370 frontend tests, and 10 Pages tests plus HTTP verification.
- `task fix`, `task lint`, `task check`, and `task docs:check` passed. Mypy checked 168 source files and import-boundary checks passed.
- `task standalone:test` passed against a freshly built, core-only installed wheel, real HTTP, SQLite, and Chromium. The synthetic provider exercises actual cache persistence without live RIDB requests.
- Many Glacier parser/source validation is read-only research, not a live-network unit test. Committed fixtures and integration upstreams remain synthetic.

The synthetic 205-destination regression verifies three batch results (`has_more`: true, true, false), exactly 205 distinct fetches, 205 persisted snapshots, a photo on the final destination, zero catalog imports, and client closure after each batch. Fresh and unsupported work skip source clients; whole-batch failure stops immediate continuations; both runtimes recover periodically.

Database verification in that isolated test:

```sql
SELECT COUNT(*) FROM campgrounds WHERE details IS NOT NULL;
-- 205
```

## Convergence inspection

The seven functional requirements, four success criteria, six user-story acceptance scenarios, five edge cases, five design decisions, and five constitution principles were inspected against source and tests. No missing implementation, contradictions, or unrequested production behavior remain: **Converged**. No new schema, UI, public API, or dependency changes were introduced.

## Release verification

The follow-up release must update both distributed worker and beat roles (or restart the standalone process). The independent periodic task normally begins within five minutes, then successful bounded continuations process the backlog. Seven-day freshness, one-hour cooldowns, atomic claims, and last-good snapshots remain in effect. Many Glacier's cache must be checked again after its batch runs in the deployed environment; this workspace cannot access cluster administration. PR CI independently verifies the fix before release.
