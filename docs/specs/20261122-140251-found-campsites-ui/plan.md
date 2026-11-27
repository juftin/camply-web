# Implementation Plan: Rework Found Campsites UI

**Branch**: `roasted-bird` | **Date**: 2026-11-22 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `docs/specs/20261122-140251-found-campsites-ui/spec.md`

## Summary

Replace the fragmented exact-date-range accordion results in `FoundCampsites` and redundant summary blocks in `ScanDetail` with an intuitive, visual-first availability browsing experience built strictly on existing scan detail data:

1. Extract pure, thoroughly unit-tested availability, deduplication, calendar-grid, range-filtering, sorting, and grid-window logic into `src/frontend/lib/availability.ts`.
2. Rework `FoundCampsites.tsx` around an interactive availability calendar (`AvailabilityCalendar.tsx`) paired with deduplicated, scannable campsite cards (`CampsiteCardList.tsx`), plus a segmented view switcher to toggle into a Sites × Dates availability matrix (`AvailabilityGrid.tsx`) with inline stay inspection and booking.
3. Clean up `ScanDetail.tsx` with a cohesive header (eliminating the duplicate `Scan overview` accordion and repeated provider disclaimers) and a structured, expandable recreation-area `CoverageSummary.tsx` component with human-readable relative timestamps.
4. Verify thoroughly via Vitest unit/component tests, TypeScript/oxlint/oxfmt gates, and Playwright desktop/mobile light/dark visual snapshot baselines.

## Technical Context

**Language/Version**: TypeScript (native TypeScript 7.0.2 / `tsc --noEmit`), React 18.3, Vite 8.3
**Primary Dependencies**: Tailwind CSS 3.4, Lucide React icons, Radix UI primitives (`Dialog`, `Switch`, `Label`), React Router 7, TanStack Query 5 (zero new npm dependencies required)
**Storage**: N/A (client-side view state derived from existing `ScanDetailResponse`; no database or API schema changes)
**Testing**: Vitest 5 + Testing Library (`@testing-library/react`, `@testing-library/user-event`, `jsdom`) and Playwright visual snapshot suite (`src/frontend/tooling/run-snapshots.ts`)
**Target Platform**: Modern desktop and mobile web browsers (responsive `375px`–`1280px+`, light and dark themes)
**Project Type**: Full-stack web application monorepo — frontend-only slice under `src/frontend/`
**Performance Goals**: Instantaneous (<16ms) client-side filtering, sorting, calendar month switching, and view toggling for scans with 100+ campsites across multi-month windows; strictly bounded DOM via pagination (`10` sites/page) and 14-day grid windows
**Constraints**: Frontend-only (no backend/API/schema changes); zero horizontal document overflow on mobile (`375px`/`390px`); full keyboard and screen-reader accessibility; preserve `#results` deep-link anchor and existing `ScanDetailResponse` contract
**Scale/Scope**: Single-campground and recreation-area scans (1 to 100+ campsites, 1-day to multi-month/cross-year windows); ~7–9 frontend source/test files plus visual snapshot scenario/baseline updates

## Constitution Check

_GATE: Must pass before Phase 0 research. Re-check after Phase 1 design._

| Principle                                  | Pre-Design Check                                                                                                                                                                                                 | Post-Design Verification                                                                                                                                                                         |
| ------------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **I. Reliability & Precision**             | PASS — Reuses verified backend-filtered `ScanDetailResponse` data; preserves exact minimum-stay consecutive block math, unique `(provider, campground, campsite)` identity, and stale/partial coverage warnings. | PASS — `src/frontend/lib/availability.ts` enforces strict non-combining per-site consecutive stays, continuous-stay range matching `[start, end)`, and explicit stale & partial-coverage states. |
| **II. Type Safety & Static Analysis**      | PASS — Strictly typed TypeScript modules validated by `task frontend:check` (`tsc`) and `task frontend:lint` (`oxlint` + `oxfmt`).                                                                               | PASS — All view models (`NormalizedFoundSite`, `DateSelection`, `CalendarDayCell`, `GridWindow`) are strictly typed with zero `any`; no external untyped libraries introduced.                   |
| **III. Modern Workflow & Automation**      | PASS — All validation runs via `task frontend:check`, `task frontend:lint`, `task frontend:test`, and `task frontend:snapshot`.                                                                                  | PASS — Quickstart and planned verification use `task` commands exclusively; zero new tooling dependencies added.                                                                                 |
| **IV. Monorepos & Separation of Concerns** | PASS — Strictly scoped to `src/frontend/` and `tests/frontend/snapshots/baselines/`; Python `src/camply/` untouched.                                                                                             | PASS — Pure domain helpers cleanly separated in `src/frontend/lib/availability.ts` from UI presentation in `src/frontend/components/found-campsites/` and `src/frontend/pages/ScanDetail.tsx`.   |
| **V. Automated Verification**              | PASS — Plan mandates unit tests for availability logic, component/integration tests for `FoundCampsites` & `ScanDetail`, and Playwright desktop/mobile light/dark visual snapshots.                              | PASS — Test plan covers every user story, edge case, keyboard/a11y contract, refresh resilience, and visual regression baseline.                                                                 |

No Constitution violations exist.

## Project Structure

### Documentation (this feature)

```text
docs/specs/20261122-140251-found-campsites-ui/
├── spec.md                     # Feature specification
├── checklists/
│   └── requirements.md         # Spec quality checklist
├── plan.md                     # This file (/speckit.plan output)
├── research.md                 # Phase 0 design decisions & rationale
├── data-model.md               # Phase 1 client-side view models & state transitions
├── contracts/
│   └── ui-contract.md          # Phase 1 UI, a11y, lifecycle & viewport contract
├── quickstart.md               # Phase 1 validation guide
└── tasks.md                    # Phase 2 output (/speckit.tasks - not created yet)
```

### Source Code (repository root)

```text
package.json
Taskfile.yaml
tasks/
└── frontend.yaml
src/
└── frontend/
    ├── lib/
    │   ├── availability.ts                 # NEW: pure stay, calendar, filter, sort, & grid helpers
    │   ├── availability.test.ts            # NEW: exhaustive unit tests for domain math
    │   ├── structs.ts                      # UNCHANGED: existing ScanDetailResponse types
    │   ├── utils.ts                        # EXISTING: ISO date & relative-time helpers
    │   └── weekdays.ts                     # EXISTING: weekday/weekend conventions
    ├── components/
    │   ├── FoundCampsites.tsx              # UPDATED: orchestrator (toolbar, view switcher, states)
    │   ├── FoundCampsites.test.tsx         # UPDATED: comprehensive interactive component tests
    │   └── found-campsites/                # NEW: focused subcomponents
    │       ├── AvailabilityCalendar.tsx    # Interactive monthly availability calendar & range picker
    │       ├── CampsiteCardList.tsx        # Deduplicated campsite cards, stay chips, & pagination
    │       ├── AvailabilityGrid.tsx        # Sites × Dates matrix with sticky column & stay inspector
    │       └── CoverageSummary.tsx         # Structured recreation-area campground coverage panel
    ├── pages/
    │   ├── ScanDetail.tsx                  # UPDATED: cohesive header, CoverageSummary, remove duplicate overview
    │   └── ScanDetail.test.tsx             # UPDATED: page-level integration, refresh, & coverage tests
    └── tooling/
        └── run-snapshots.ts                # UPDATED: scan-detail & grid/calendar snapshot scenarios
tests/
└── frontend/
    └── snapshots/
        └── baselines/                      # UPDATED: refreshed scan-detail & area-scan-detail baselines
docs/
├── architecture/
│   └── DESIGN_FRONTEND.md                  # UPDATED: reflect calendar + cards + grid results UX
└── CHECKLIST.md                            # UPDATED: track feature completion before PR
```

**Structure Decision**: Keep all changes cleanly inside `src/frontend/` (plus existing Playwright visual baselines under `tests/frontend/snapshots/baselines/` and docs). Separating pure availability/calendar/grid logic into `src/frontend/lib/availability.ts` and focused subcomponents under `src/frontend/components/found-campsites/` keeps `FoundCampsites.tsx` and `ScanDetail.tsx` concise, modular, and independently testable while preserving existing component export paths and zero backend coupling.

## Complexity Tracking

No Constitution violations — no complexity exceptions required.
