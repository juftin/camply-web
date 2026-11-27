---
description: "Dependency-ordered task list for reworking the Found Campsites and Scan Detail UI"
---

# Tasks: Rework Found Campsites UI

**Input**: Design documents from `docs/specs/20261122-140251-found-campsites-ui/`

**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`, `contracts/ui-contract.md`, `quickstart.md`

**Tests**: Included per Camply Constitution Principle V (Automated Verification) and Test-First Mentality. Write test tasks first within each phase and verify they fail before implementing.

**Organization**: Tasks are grouped by user story (`US1`–`US4`) so each story is independently implementable and testable.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependency on incomplete tasks)
- **[Story]**: Maps task to a specific user story from `spec.md` (`[US1]`, `[US2]`, `[US3]`, `[US4]`)
- Exact file paths are included in every task description

## Path Conventions

- Frontend source & colocated unit tests: `src/frontend/`
- Visual snapshot tooling & baselines: `src/frontend/tooling/run-snapshots.ts`, `tests/frontend/snapshots/baselines/`
- Architecture & checklist documentation: `docs/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Confirm baseline health and prepare the subcomponent directory structure

- [x] T001 Confirm existing frontend baseline passes by running `pnpm exec vitest run src/frontend/components/FoundCampsites.test.tsx src/frontend/pages/ScanDetail.test.tsx` and create the `src/frontend/components/found-campsites/` directory for modular UI components

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Build and thoroughly verify the pure TypeScript availability, calendar, filtering, sorting, and grid-window domain module that all user stories depend on

**⚠️ CRITICAL**: Complete this phase before starting User Stories 1–4.

- [x] T002 Write failing unit tests in `src/frontend/lib/availability.test.ts` covering: maximal consecutive `AvailableStay` blocks (`stay.nights >= scan.min_stay_length`, exclusive check-out `end = addDays(lastNight, 1)`, non-combining across campsites/campgrounds); `NormalizedFoundSite` deduplication by `${providerId}:${campgroundId}:${campsiteId}` and fallback `displayName` (`"Campsite ${campsiteId}"`); `applyCalendarDayClick` state transitions (single-night select, same-day clear, forward range, reverse-click auto-normalization, restart after active range); `stayMatchesSelection` (`stay.start <= start && start < stay.end` for single night, `stay.start <= start && stay.end >= end` for continuous range); `buildCalendarMonth` (soonest-opening default month with `scan.start_date` fallback when empty, scan-window clamping, `scan.end_date` checkout-boundary selectability only when `selection?.end === null`, Friday/Saturday `isWeekendNight` flags, per-night unique `availableSiteCount` computed from search-filtered sites); `filterAndSortSites` across `soonest`, `longest`, `most_nights`, and `name` (evaluating matching stays for `soonest`/`longest` when `dateSelection` is active); and 14-day `buildGridWindow` clamping and pagination helpers
- [x] T003 Implement pure domain types and helpers (`AvailableStay`, `NormalizedFoundSite`, `DateSelection`, `CalendarDayCell`, `CalendarMonth`, `FoundViewMode`, `FoundSortMode`, `GridWindow`, `SelectedGridStay`, `normalizeFoundSites`, `applyCalendarDayClick`, `stayMatchesSelection`, `getInitialCalendarMonth`, `getCalendarMonthBounds`, `buildCalendarMonth`, `filterAndSortSites`, `buildGridWindow`, `formatStayRangeDate`) in `src/frontend/lib/availability.ts` so all tests in `src/frontend/lib/availability.test.ts` pass

**Checkpoint**: `pnpm exec vitest run src/frontend/lib/availability.test.ts` passes cleanly; all user story UI phases can proceed.

---

## Phase 3: User Story 1 - Explore openings visually with an interactive availability calendar (Priority: P1) 🎯 MVP

**Goal**: Provide an interactive monthly availability calendar scoped to the scan window that shows opening counts and weekend cues at a glance and filters found campsites by single night or check-in → check-out range.

**Independent Test**: Render a scan spanning multiple months with overlapping openings; verify the calendar opens on the month of the soonest qualifying opening, bounds month navigation to the scan window, shows per-night site counts and weekend cues, filters overlapping sites accurately on single-night click and two-date check-in → check-out selection (including reverse order and `scan.end_date` checkout boundary), and clears cleanly in one click.

### Tests for User Story 1 ⚠️

- [x] T004 [P] [US1] Write failing component tests in `src/frontend/components/found-campsites/AvailabilityCalendar.test.tsx` verifying: initial month opens to soonest qualifying opening (or `scan.start_date` when empty); `"Previous month"` / `"Next month"` buttons clamp to `[monthOf(scan.start_date), monthOf(scan.end_date)]`; day cells expose descriptive `aria-label` (date + available site count) and `aria-pressed`; single-night selection, same-day toggle-off, check-in → check-out range selection (forward and reverse), `scan.end_date` checkout-boundary enablement only when `selection?.end === null`, hover range preview, active filter summary pill, and `"Clear dates"` button

### Implementation for User Story 1

- [x] T005 [US1] Implement `AvailabilityCalendar` in `src/frontend/components/found-campsites/AvailabilityCalendar.tsx` using `buildCalendarMonth`, `getCalendarMonthBounds`, and `applyCalendarDayClick` from `src/frontend/lib/availability.ts`, rendering Sun–Sat month grid, per-night site count cues, Fri/Sat weekend-night styling, out-of-window disabled cells, hover range preview, keyboard navigation, active selection badge, and `"Clear dates"` action
- [x] T006 [US1] Integrate `AvailabilityCalendar` state (`dateSelection`, `visibleMonth`, automatic reset/preservation across scan changes and live refreshes) into `src/frontend/components/FoundCampsites.tsx` so calendar day counts reflect the current search-filtered qualifying sites and clicking dates immediately filters displayed results and updates the `role="status"` summary count

**Checkpoint**: User Story 1 calendar browsing and date-range filtering work and pass `AvailabilityCalendar.test.tsx`.

---

## Phase 4: User Story 2 - Browse scannable, deduplicated campsite cards (Priority: P1)

**Goal**: Render each unique qualifying campsite once as a clean, scannable card with campground attribution, structured capability badges, readable check-in → check-out stay chips (highlighting matches to any active calendar selection and expanding inline when >4 stays exist), full-result search, 4-mode sorting, bounded pagination (`SITES_PER_PAGE = 10`), and prominent booking CTAs.

**Independent Test**: Render a scan containing a campsite with 5+ separate stay windows, rich capabilities, an unnamed campsite, a stale recreation-area observation, and 12+ sites across pages; verify each unique `(provider, campground, campsite)` appears once, stay chips expand inline beyond 4, active calendar filters highlight matching stay chips, search and sort (`soonest`, `longest`, `most_nights`, `name`) evaluate all pages and reset to page 1, pagination clamps on result shrinkage, and booking links carry accessible site + campground labels.

### Tests for User Story 2 ⚠️

- [x] T007 [P] [US2] Update and expand component tests in `src/frontend/components/FoundCampsites.test.tsx` to test: deduplicated site cards (site with multiple stays rendered once), fallback `Campsite <id>` label, campground attribution + stale badge on multi-campground/stale sites, structured capability badges (`campsite_type`, `Electric hookup`, `Accessible`, `Up to N ft`, `permitted_equipment`) omitting unknown fields, stay-chip capping at `4` with inline `"+N more stays"` / `"Show fewer stays"` toggle, stay-chip highlighting when a calendar date/range filter is active, full-result search (`"Search found campsites"`), sort selector (`"Sort campsites"` with `soonest`, `longest`, `most_nights`, `name`), pagination (`SITES_PER_PAGE = 10`, `"Previous campsites"` / `"Next campsites"`, clamping on live refresh shrinkage), single concise disclaimer, and filter-empty reset states (`"Clear filters"` / `"Clear search"` / `"Clear dates"`)

### Implementation for User Story 2

- [x] T008 [P] [US2] Implement `CampsiteCardList` in `src/frontend/components/found-campsites/CampsiteCardList.tsx` displaying deduplicated `NormalizedFoundSite` cards with campground eyebrow (when present), stale badge with relative freshness context, icon-backed capability badges, formatted `Check-in → Check-out · N nights` stay chips (capped at `4` prioritizing matching stays, inline `"+N more stays"` / `"Show fewer stays"` toggle, year shown when crossing New Year's Day), visual highlight for stays matching `dateSelection`, prominent external booking CTA (`target="_blank" rel="noopener noreferrer"`, accessible `aria-label="View <name> on provider website"` plus `(<campground>)`), and `<nav aria-label="Campsite pages">` pagination (`SITES_PER_PAGE = 10`)
- [x] T009 [US2] Rework `src/frontend/components/FoundCampsites.tsx` to replace the legacy exact-date-range `<details>` accordions with the desktop split / mobile stacked `AvailabilityCalendar` + `CampsiteCardList` layout, clean toolbar (`"Search found campsites"`, `"Sort campsites"`), accurate live `role="status"` counts (`N sites · M openings`), distinct waiting/active-empty/paused-empty/partial-coverage-empty/filter-empty states, single concise provider disclaimer, and `#results` anchor scrolling

**Checkpoint**: User Stories 1 and 2 together deliver the complete P1 MVP; `pnpm exec vitest run src/frontend/components/FoundCampsites.test.tsx src/frontend/components/found-campsites/AvailabilityCalendar.test.tsx` passes cleanly.

---

## Phase 5: User Story 3 - Switch between Cards and Availability Grid views (Priority: P2)

**Goal**: Add a segmented view switcher (`Cards` | `Grid`) that lets users inspect night-by-night availability in a 14-day Sites × Dates matrix with a sticky campsite column, weekend cues, date-window navigation, inline stay inspection and booking CTA, and zero horizontal viewport overflow.

**Independent Test**: Render a multi-week scan with multiple campsites, switch to Grid view, verify rows/columns and weekend cues, step date windows forward/backward, click an available night cell to open the inline stay inspector and verify the booking link, dismiss via Escape/close, switch back to Cards view, and verify search, sort, date filter, and view mode persist across switches and live data refreshes.

### Tests for User Story 3 ⚠️

- [x] T010 [P] [US3] Write failing component tests in `src/frontend/components/found-campsites/AvailabilityGrid.test.tsx` verifying: matrix renders matching campsites as rows (with sticky identity column and campground label) and up to 14 consecutive dates as columns; `"Previous dates"` / `"Next dates"` controls step within `[scan.start_date, scan.end_date)`; clicking or keyboard-activating an available cell toggles `aria-pressed` and opens the inline stay inspector showing `Check-in → Check-out`, night count, capabilities, stale indicator (if applicable), and provider booking link; closing via close button or `Escape` dismisses the inspector; and stale/removed selected stays auto-clear when results refresh
- [x] T011 [US3] Add view-switcher interaction and state-persistence tests in `src/frontend/components/FoundCampsites.test.tsx` (after `T007`) verifying toggling `"Results view"` (`"Cards"` ↔ `"Grid"`), preserving search query, sort order, and active `dateSelection` across switches and live refreshes, and aligning the grid window to an active calendar date filter

### Implementation for User Story 3

- [x] T012 [P] [US3] Implement `AvailabilityGrid` in `src/frontend/components/found-campsites/AvailabilityGrid.tsx` with bounded 14-day window navigation (`buildGridWindow`), inner `overflow-x-auto` container with sticky left site column (preventing document horizontal overflow), weekend column tinting, accessible available night buttons (`aria-label` with site, night, and full stay range; `aria-pressed`), inline stay inspector panel with capabilities, staleness context, external booking CTA (`target="_blank" rel="noopener noreferrer"`, `aria-label="View <name> on provider website"` plus `(<campground>)`), close button, and `Escape` key handler, plus `<nav aria-label="Campsite pages">` row pagination (`SITES_PER_PAGE = 10`)
- [x] T013 [US3] Add the `"Results view"` segmented switcher (`"Cards"` | `"Grid"`) to the toolbar in `src/frontend/components/FoundCampsites.tsx`, wire `viewMode` and `gridStartDate` state (synced with `dateSelection` and preserved across live refreshes), and ensure compact date-filter summary/clear controls remain visible when browsing Grid view

**Checkpoint**: User Stories 1, 2, and 3 all work seamlessly and pass all component tests.

---

## Phase 6: User Story 4 - Navigate a cohesive scan detail header and recreation-area coverage summary (Priority: P2)

**Goal**: Clean up `ScanDetail.tsx` with a single cohesive header (eliminating the duplicate `Scan overview` card and repeated freshness/criteria blocks) and replace raw recreation-area coverage text and ISO timestamps with a structured, expandable `CoverageSummary` component.

**Independent Test**: Render both a single-campground scan and a partial-coverage recreation-area scan in `ScanDetail`; verify scan status (`Monitoring`/`Paused`/`Ended`), criteria, freshness, creation time, external provider link, and edit action appear once in the cohesive header with no duplicate `Scan overview` card; verify recreation-area coverage displays structured counts, a partial-coverage warning, and an expandable breakdown with human-readable relative timestamps (zero raw ISO timestamps); and verify catalog-error resilience, refresh-error retry with cached results, and `#results` anchor behavior.

### Tests for User Story 4 ⚠️

- [x] T014 [P] [US4] Write failing component tests in `src/frontend/components/found-campsites/CoverageSummary.test.tsx` verifying: `<section aria-label="Campground coverage">` renders coverage mode (`All campgrounds` / `Selected campgrounds`), eligible/unavailable and checked/pending/failed counts, partial-coverage warning when `coverage_status !== "complete"`, expandable per-campground breakdown with status badges, `unavailable_reason`, and human-readable `formatRelativeTime` labels (never raw ISO timestamp strings)
- [x] T015 [P] [US4] Update integration tests in `src/frontend/pages/ScanDetail.test.tsx` to match the reworked `FoundCampsites` and consolidated `ScanDetail` UI: verify single cohesive header with saved criteria/status/freshness/created metadata (no duplicate `Scan overview` accordion or duplicate disclaimer), `CoverageSummary` integration for recreation-area scans, calendar filtering + Cards/Grid view flows, live-refresh state preservation (view mode, search, date filter, pagination clamping), paused/waiting/empty/partial-coverage states, cached-results retry on refresh failure, and graceful fallback when destination metadata fails to load

### Implementation for User Story 4

- [x] T016 [P] [US4] Implement `CoverageSummary` in `src/frontend/components/found-campsites/CoverageSummary.tsx` preserving `<section aria-label="Campground coverage">`, showing compact coverage mode and status counts, clear amber partial/failed warning callout when `coverage_status !== "complete"`, and an expandable `<details>` list of member campgrounds with status badges (`Checked`, `Pending`, `Failed`, `Unavailable`), `unavailable_reason`, and human-readable `formatRelativeTime(member.last_checked_at)` timestamps
- [x] T017 [US4] Refactor `src/frontend/pages/ScanDetail.tsx` to widen the container to `max-w-5xl`, consolidate destination title, parent recreation area, external provider link, status badges (`Monitoring`/`Paused`/`Ended`), `Last checked`, `Created`, saved criteria pills, and `ScanForm` edit button into one cohesive header, replace raw coverage `<p>` lines with `<CoverageSummary scan={scan} />`, and remove the redundant bottom `Scan overview` `<details>` card

**Checkpoint**: All 4 user stories are complete and independently verified; `pnpm exec vitest run src/frontend/lib/availability.test.ts src/frontend/components/FoundCampsites.test.tsx src/frontend/components/found-campsites/ src/frontend/pages/ScanDetail.test.tsx` passes cleanly.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Visual regression coverage (desktop/mobile, light/dark), documentation alignment, and full project quality gates

- [x] T018 Update existing `scan-detail-*`, `scan-detail-paginated-*`, and `area-scan-detail-*` scenarios and add Grid-view / calendar-filter visual snapshot scenarios in `src/frontend/tooling/run-snapshots.ts` (asserting zero viewport horizontal overflow on desktop `1280×800` and mobile `375×812`/`390×844` in both light and dark themes)
- [ ] T019 Run `task frontend:snapshot:update` and `task frontend:snapshot:check` to capture and verify updated visual baselines in `tests/frontend/snapshots/baselines/` and inspect `tmp/snapshots/report.html` for visual polish across desktop/mobile and light/dark modes _(blocked in this Linux container: Chromium requires OS `libglib-2.0.so.0`; run `task frontend:snapshot:update -- --filter scan-detail` on a machine/CI runner with Chromium system deps)_
- [x] T020 [P] Update `docs/architecture/DESIGN_FRONTEND.md` to document the reworked Found Campsites calendar + deduplicated cards + availability grid UX and consolidated Scan Detail header
- [x] T021 [P] Update `docs/CHECKLIST.md` to reflect completion of the Found Campsites UI rework
- [x] T022 Run full validation pipeline per `docs/specs/20261122-140251-found-campsites-ui/quickstart.md`: `task frontend:fix && task frontend:check && task frontend:lint && task frontend:test` and confirm zero errors, zero warnings, and 100% passing tests

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies — start immediately.
- **Phase 2 (Foundational)**: Depends on Phase 1 — **blocks all user stories** (`US1`–`US4`) because `src/frontend/lib/availability.ts` defines the shared view models and pure calculations.
- **Phase 3 (`US1` — Interactive Calendar)**: Depends on Phase 2.
- **Phase 4 (`US2` — Deduplicated Campsite Cards)**: Depends on Phase 2; integrates cleanly with `US1` inside `FoundCampsites.tsx` (`T008` can be authored in parallel with `US1`, then integrated in `T009`).
- **Phase 5 (`US3` — Cards ↔ Grid View Switcher)**: Depends on Phase 2 (`T010`, `T012` can be authored in parallel with `US1`/`US2`; toolbar wiring `T013` follows `T009`).
- **Phase 6 (`US4` — Cohesive Scan Detail & Coverage Summary)**: Depends on Phase 2 (`T014`, `T016` have zero dependency on `US1`–`US3` and can run in parallel; `T015`/`T017` integrate with `FoundCampsites`).
- **Phase 7 (Polish & Cross-Cutting)**: Depends on Phases 3–6 completing.

### Parallel Opportunities

```bash
# Once Phase 2 (src/frontend/lib/availability.ts) passes, independent subcomponents & tests can be authored in parallel:
Task: "T004 [P] [US1] AvailabilityCalendar.test.tsx"
Task: "T008 [P] [US2] CampsiteCardList.tsx"
Task: "T010 [P] [US3] AvailabilityGrid.test.tsx"
Task: "T012 [P] [US3] AvailabilityGrid.tsx"
Task: "T014 [P] [US4] CoverageSummary.test.tsx"
Task: "T016 [P] [US4] CoverageSummary.tsx"

# In Phase 7, documentation updates can run in parallel:
Task: "T020 [P] Update docs/architecture/DESIGN_FRONTEND.md"
Task: "T021 [P] Update docs/CHECKLIST.md"
```

---

## Implementation Strategy

### MVP First (Phase 1 + Phase 2 + User Stories 1 & 2)

1. Complete Phase 1 (Setup) and Phase 2 (`src/frontend/lib/availability.ts` + unit tests).
2. Implement Phase 3 (`US1` — Interactive Availability Calendar) and Phase 4 (`US2` — Deduplicated Campsite Cards + refactored `FoundCampsites.tsx`).
3. **Checkpoint**: Validate calendar date/range filtering, deduplicated cards, search, sort, pagination, and empty states independently.

### Incremental Delivery

1. Add Phase 5 (`US3` — Availability Grid + Cards ↔ Grid view switcher) → verify matrix interactions, stay inspector, and mobile scroll behavior.
2. Add Phase 6 (`US4` — `CoverageSummary` + cohesive `ScanDetail.tsx` header cleanup) → verify full page integration and refresh/error resilience.
3. Complete Phase 7 (Playwright visual snapshots across desktop/mobile & light/dark, docs updates, and full `task frontend:check && task frontend:lint && task frontend:test` gate).

---

## Phase 8: Convergence

- [ ] T023 Capture and verify refreshed Playwright visual snapshot baselines (`scan-detail-*`, `scan-detail-grid-*`, `scan-detail-paginated-*`, `area-scan-detail-*`) in `tests/frontend/snapshots/baselines/` via `task frontend:snapshot:update -- --filter scan-detail` and `task frontend:snapshot:check` on an environment with Chromium system libraries (`libglib-2.0.so.0`) per SC-006 (missing)
- [x] T024 Add automated tests in `src/frontend/components/FoundCampsites.test.tsx` and `src/frontend/pages/ScanDetail.test.tsx` covering partial-coverage recreation-area empty state, checked paused-scan empty state, active-scan empty state, and date-filter-only / combined search+date-filter empty reset (`Clear dates` / `Clear filters`) per FR-015 (partial)
- [x] T025 Re-anchor `gridStartDate` in `src/frontend/components/FoundCampsites.tsx` when initial openings arrive after a waiting/empty mount or when saved scan dates change (without overriding manual user grid navigation) and add a regression test in `src/frontend/components/FoundCampsites.test.tsx` per FR-008 / FR-012 (partial)
- [x] T026 Align the Found campsites UI rework entry in `docs/CHECKLIST.md` so Playwright visual baseline status accurately reflects whether `T023` has completed per plan: Documentation (partial)
