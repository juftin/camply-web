# Implementation plan

1. Audit the scanner's per-site fan-out, snapshot schema and scan API; retain existing delivery guards and new-opening detection.
2. Store site attributes through an additive Alembic migration. Share minimum-stay and site-filter logic in the database package so API and worker agree; older unknown attributes cannot satisfy restrictive filters until refreshed.
3. Add summary/direct worker configuration and a validated public app URL. Enqueue one summary per matching subscription and label its action “View campsites”; preserve direct mode and old serialized notification payloads.
4. Enrich scan results with attributes and provider campground booking URLs, filter counts consistently, and regenerate OpenAPI types.
5. Replace the raw-date list with a responsive, searchable site list and explicit check-in/check-out blocks. Keep freshness and empty/error states visible.
6. Run regression tests, Task quality gates, migration round-trip verification on a disposable database, and visual snapshots. Update architecture/configuration docs and checklist.

Constitution check: preserve provider-verified snapshots, asynchronous delivery, Pydantic contracts, typed React/TanStack Query and package boundaries. Add behavior tests before implementation. No new dependencies or notification channels.
