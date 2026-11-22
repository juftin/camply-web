# Quickstart Validation Guide: Rework Found Campsites UI

**Feature**: `033-found-campsites-ui`
**References**: [spec.md](spec.md) · [data-model.md](data-model.md) · [contracts/ui-contract.md](contracts/ui-contract.md)

## Prerequisites

- Dependencies installed via `task frontend:install` (Node >= 24, pnpm 12).
- No backend or database setup is required for unit tests or mocked visual snapshot checks.

## 1. Automated Unit & Component Verification

Run the availability domain tests, Found Campsites component tests, and Scan Detail integration tests:

```bash
pnpm exec vitest run --config src/frontend/vite.config.ts \
  lib/availability.test.ts \
  components/FoundCampsites.test.tsx \
  components/found-campsites/ \
  pages/ScanDetail.test.tsx
```

**Expected outcomes**:

- `availability.test.ts` passes all qualifying stay, deduplication, calendar month/boundary, single-night & range-normalization filtering, sorting, and grid window tests.
- `FoundCampsites.test.tsx` verifies calendar rendering, single-night and check-in/check-out filtering, deduplicated site cards, stay-chip expansion (>4 stays), capability badges, Cards ↔ Grid view switching, Grid cell stay inspection, search/sort/pagination, and filter-empty reset flows.
- `ScanDetail.test.tsx` verifies cohesive header consolidation (no duplicate overview card or repeated disclaimers), polished recreation-area coverage with relative timestamps, stale-result labeling, refresh-resilient state preservation, empty/waiting/paused/error states, and `#results` anchor behavior.

## 2. Static Type Check, Linting & Full Frontend Suite

```bash
task frontend:check && task frontend:lint && task frontend:test
```

**Expected outcomes**:

- Zero TypeScript (`tsc`) errors.
- Zero `oxlint` warnings/errors and clean `oxfmt` formatting.
- Entire Vitest frontend suite passes with zero regressions.

## 3. Visual Snapshot & Responsive Verification (Desktop/Mobile, Light/Dark)

Capture and verify Playwright visual snapshots covering single-campground Cards view, Grid view, paginated results, and recreation-area partial coverage across desktop (`1280×800`) and mobile (`375×812` / `390×844`) in both light and dark themes:

```bash
task frontend:snapshot
```

When intentionally updating approved visual baselines after inspecting `tmp/snapshots/report.html`:

```bash
task frontend:snapshot:update && task frontend:snapshot:check
```

**Expected outcomes**:

- Zero viewport horizontal overflow across all scan detail scenarios (including Grid view on mobile).
- Calendar, Cards view, Grid view, and recreation-area coverage render cleanly in both light and dark themes.
- Snapshot verification (`task frontend:snapshot:check`) passes cleanly against updated baselines.

## 4. Manual Interactive Walkthrough (Optional Local Dev)

Start the frontend (or full stack with `task dev`) and open any saved campground scan and recreation-area scan (`/dashboard/scans/:scanId`):

1. Confirm the calendar opens directly on the month of the soonest opening with site counts and weekend-night cues visible immediately.
2. Click one open night → verify cards filter immediately and matching stay chips highlight.
3. Click a second date → verify range filtering keeps only continuously available campsites; click **Clear dates** to restore all results.
4. Switch **Cards** → **Grid** → click an available cell to inspect the stay and verify the booking link; confirm mobile horizontal scroll keeps the site column sticky without page overflow.
5. Verify a recreation-area scan shows structured coverage counts, an expandable member list with relative timestamps, and clear stale badges on retained failed-campground results.
