# Implementation plan

1. Audit the scanner's per-site fan-out, snapshot schema and scan API; retain existing delivery guards and new-opening detection.
2. Store site attributes through an additive Alembic migration. Share minimum-stay and site-filter logic in the database package so API and worker agree; older unknown attributes cannot satisfy restrictive filters until refreshed.
3. Add summary/direct worker configuration and a validated public app URL. Enqueue one summary per matching subscription and label its action “View campsites”; preserve direct mode and old serialized notification payloads.
4. Enrich scan results with attributes and provider campground booking URLs, filter counts consistently, and regenerate OpenAPI types.
5. Replace the raw-date list with a responsive, searchable site list and explicit check-in/check-out blocks. Keep freshness and empty/error states visible.
6. Run regression tests, Task quality gates, migration round-trip verification on a disposable database, and visual snapshots. Update architecture/configuration docs and checklist.

Constitution check: preserve provider-verified snapshots, asynchronous delivery, Pydantic contracts, typed React/TanStack Query and package boundaries. Add behavior tests before implementation. No new dependencies or notification channels.

## Grouped results refinement

1. Preview desktop/mobile date sections with synthetic data before changing the results page (completed and reviewed).
2. Add behavior tests for shared ranges, separated stays, minimum stays, unique counts, search, sorting, collapsing and campground/provider links; confirm they fail against the current site-card layout.
3. Reuse the existing consecutive-night calculation, group by both endpoints, and render native details/summary sections with compact site rows. Preserve freshness, empty/error states and alert anchors. Read the full campground URL with TanStack Query from the existing campground endpoint; no backend contract changes or direct provider requests.
4. Verify frontend tests, lint/types, and desktop/mobile light/dark screenshots of the actual page. Update the frontend blueprint and global checklist.
