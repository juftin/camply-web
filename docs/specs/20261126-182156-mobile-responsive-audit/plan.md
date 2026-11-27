# Implementation Plan: Full Mobile-Responsive UI Audit & Polish

**Branch**: `20261126-182156-mobile-responsive-audit` | **Date**: 2026-11-26 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `docs/specs/20261126-182156-mobile-responsive-audit/spec.md`

## Summary

Conduct a systematic, route-by-route mobile-responsive UI audit and polish across all 26 web application routes and interactive overlays (`T4.1.6`), upgrading shared UI primitives (`Sheet` slide-over mobile navigation drawer with consistently sticky header, viewport-bounded `Dialog` with pinned header/footer and `44×44 px` close target, clamped `DatePicker`, and auto-zoom-safe `Input`), converting action-heavy Admin management lists (`Users`, `Invitations`, `Scans`) to stacked mobile cards while hardening horizontal-scroll containment for dense telemetry/log/detail tables, and expanding Playwright visual & zero-overflow verification to cover every route and key mobile overlay without regressing desktop layouts.

## Technical Context

**Language/Version**: TypeScript (native TypeScript 7 via `@typescript/native` + Vite 8), React 18.3, Node >=24 (`pnpm@12`)

**Primary Dependencies**: Tailwind CSS 3.4, `tailwindcss-animate`, `@radix-ui/react-dialog` (reused for `Sheet` drawer—zero new runtime dependencies), `@radix-ui/react-dropdown-menu`, `@radix-ui/react-label`, `@radix-ui/react-switch`, `lucide-react`, `recharts`, `maplibre-gl`, `embla-carousel-react`, `react-router-dom`, `react-hook-form`, `@tanstack/react-query`

**Storage**: N/A (frontend-only UI refinements; zero backend, API, or database changes)

**Testing**: Vitest 5 + Testing Library (`task frontend:test`), Playwright visual snapshot & horizontal-overflow runner (`src/frontend/tooling/run-snapshots.ts`, `task frontend:snapshot`), Oxlint + Oxfmt (`task frontend:lint`), native TypeScript typecheck (`task frontend:check`)

**Target Platform**: Responsive web browsers on smartphones (375×667, 375×812, 390×844; graceful usability down to 360 px), tablets (768×1024 transition breakpoint), and desktop regression guard (1280×800), in both light and dark modes

**Project Type**: Full-stack web monorepo — scoped strictly to the React SPA under `src/frontend/` and visual baselines under `tests/frontend/snapshots/baselines/`

**Performance Goals**: Zero additional runtime npm dependencies; negligible bundle impact; Playwright visual snapshot suite remains fast under existing parallel worker concurrency

**Constraints**: Zero document-level horizontal overflow (`scrollWidth <= innerWidth`) across all 26 routes at 375 px, 390 px, and 768 px; minimum 44×44 px effective touch targets on primary mobile controls; 16 px mobile input font size (`text-base sm:text-sm`) to prevent iOS Safari focus zoom; desktop layouts (1280 px+) unregressed; reduced-motion preferences honored; `/docs/` VitePress portal excluded

**Scale/Scope**: 26 application routes, shared shell (`Header`, `Layout`, `AdminNav`, `DismissibleBanner`), 4 core UI primitives (`sheet.tsx`, `dialog.tsx`, `date-picker.tsx`, `input.tsx`), 6 modal/overlay workflows, 9 admin views (3 hybrid card/table lists + 6 telemetry/detail/log views), ~25 new representative mobile visual snapshot baselines + 26-route automated overflow check

## Constitution Check

_GATE: Must pass before Phase 0 research. Re-check after Phase 1 design._

| Principle                                  | Pre-Design | Post-Design | Verification                                                                                                                                                     |
| :----------------------------------------- | :--------- | :---------- | :--------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **I. Reliability & Precision**             | PASS       | PASS        | Frontend-only UI polish; preserves all availability, alert, and booking link accuracy without altering API/polling logic.                                        |
| **II. Type Safety & Static Analysis**      | PASS       | PASS        | All React/TypeScript edits and snapshot tooling updates must pass `task frontend:check` (`tsc`), `task frontend:lint` (`oxlint` + `oxfmt`).                      |
| **III. Modern Workflow & Automation**      | PASS       | PASS        | Uses the local `task frontend:*` workflows for frontend checks and Playwright verification.                                                                      |
| **IV. Monorepos & Separation of Concerns** | PASS       | PASS        | Strictly scoped to `src/frontend/`, `tests/frontend/snapshots/baselines/`, and `docs/`; zero backend/Python boundary changes.                                    |
| **V. Automated Verification**              | PASS       | PASS        | Colocated Vitest unit/component tests written/updated alongside primitive & page changes, plus Playwright mobile overflow assertions and visual baselines in CI. |

No constitution violations; Complexity Tracking is not required.

## Project Structure

### Documentation (this feature)

```text
docs/specs/20261126-182156-mobile-responsive-audit/
├── spec.md                              # Feature specification (clarified)
├── plan.md                              # This implementation plan
├── research.md                          # Phase 0 architectural & gap research
├── data-model.md                        # Route audit matrix & responsive state models
├── quickstart.md                        # End-to-end validation & verification runbook
├── audit-report.md                      # Deliverable created during implementation (FR-015 / SC-007)
├── checklists/
│   └── requirements.md                  # Spec quality checklist (16/16 passing)
└── contracts/
    └── responsive-ui-contract.md        # UI primitive, layout, and verification contracts
```

### Source Code (repository root)

```text
src/frontend/
├── components/
│   ├── Header.tsx                       # Sticky mobile header + Radix Sheet slide-over drawer
│   ├── Layout.tsx                       # Responsive footer spacing & link tap targets
│   ├── AdminNav.tsx                     # Mobile-safe horizontal scroll nav with active visibility
│   ├── SearchBar.tsx                    # Mobile touch targets & dropdown bounds
│   ├── SearchDropdown.tsx               # Viewport-clamped suggestion list & clean truncation
│   ├── ScanForm.tsx                     # Pinned header/footer DialogBody, stacked date grid
│   ├── ScanCard.tsx                     # Mobile action wrapping & bounded delete dialog
│   ├── AreaCoveragePicker.tsx           # Narrow-screen filter & campground row wrapping
│   ├── NotificationSettings.tsx         # Long URL/topic/token wrapping & copy/test ergonomics
│   ├── ActiveSessions.tsx               # Mobile-friendly session rows & revoke controls
│   ├── DestinationDetails.tsx           # Mobile lightbox dialog bounds & close target
│   ├── ChangePasswordRequired.tsx       # Auto-zoom-safe inputs & stacked actions
│   ├── admin/
│   │   └── AdminTrendsPanel.tsx         # Mobile chart tick/legend legibility & table scroll
│   └── ui/
│       ├── sheet.tsx                    # NEW: Radix Dialog-backed slide-over drawer primitive
│       ├── dialog.tsx                   # Viewport bounds, 44px close target, DialogBody, footer gap
│       ├── date-picker.tsx              # Viewport-clamped popover, mobile touch & font sizing
│       └── input.tsx                    # text-base sm:text-sm to prevent iOS focus auto-zoom
├── pages/
│   ├── Home.tsx                         # Hero spacing, search bar/dropdown mobile fit
│   ├── SearchPage.tsx                   # Collapsible/stacked mobile filters, map, pagination
│   ├── Campground.tsx                   # Header/badge wrapping, action layout, detail sections
│   ├── RecreationArea.tsx               # Header/badge wrapping, child campground list fit
│   ├── Dashboard.tsx                    # Group header wrapping, empty state, mobile spacing
│   ├── ScanDetail.tsx                   # Audit verification (already reworked in spec 033)
│   ├── Auth.tsx                         # Touch-friendly auth card & inputs
│   ├── InviteOnly.tsx                   # Mobile form spacing & status messages
│   ├── Profile.tsx                      # Account details, long email wrapping, sections
│   ├── Providers.tsx                    # Responsive card grid & badge wrapping
│   ├── HowItWorks.tsx                   # Mobile step grid & typography scale
│   ├── FAQ.tsx                          # Tappable accordion rows & spacing
│   ├── Contact.tsx                      # Stacked form & info cards
│   ├── Ethos.tsx / Contribute.tsx       # Community pages mobile spacing & readability
│   ├── PrivacyPolicy.tsx / TermsOfService.tsx # Readable prose & link wrapping
│   └── admin/
│       ├── AdminOverview.tsx            # KPI grid & trend panel mobile spacing
│       ├── AdminUsers.tsx               # Hybrid mobile cards (<md) + desktop table + pinned dialogs
│       ├── AdminUserDetail.tsx          # Single-col mobile metadata, break-all UUIDs, scroll table
│       ├── AdminInvites.tsx             # Hybrid mobile cards (<md) + desktop table
│       ├── AdminScans.tsx               # Hybrid mobile cards (<md) + desktop table + wrapping filters
│       ├── AdminScanDetail.tsx          # Mobile metadata grid + contained scroll table
│       ├── AdminTargetDetail.tsx        # Mobile metadata grid + contained scroll table
│       ├── AdminOperations.tsx          # Metric grids, contained scroll tables, pinned task dialog
│       └── AdminAudit.tsx               # Contained scroll log table & wrapping filters
└── tooling/
    └── run-snapshots.ts                 # 26-route zero-overflow guard + ~25 new mobile baselines
tests/frontend/snapshots/baselines/      # Updated & newly added mobile Playwright PNG baselines
docs/
├── CHECKLIST.md                         # Mark T4.1.6 complete upon verification
├── PLAN.md                              # Mark Phase 4 Polish complete upon verification
└── architecture/DESIGN_FRONTEND.md      # Document mobile drawer, dialog, and admin card patterns
```

**Structure Decision**: Reuse the existing single React SPA structure under `src/frontend/` with colocated Vitest tests (`*.test.tsx`) and centralized visual verification in `src/frontend/tooling/run-snapshots.ts`. Add only one new UI primitive (`src/frontend/components/ui/sheet.tsx`, backed by existing `@radix-ui/react-dialog`) and keep hybrid admin mobile cards colocated in their respective admin page modules to avoid speculative abstractions.

## Implementation Strategy

### Wave 1 — Shared Primitives & Navigation Shell (`FR-002`, `FR-003`, `FR-004`, `FR-005`, `FR-011`)

- Add `ui/sheet.tsx` and refactor `Header.tsx` to use a consistently sticky mobile header + Radix slide-over drawer (dimmed backdrop, focus trap, Escape/backdrop/route-change dismissal, `aria-expanded`, reduced-motion safe).
- Harden `ui/dialog.tsx` (mobile viewport margins `w-[calc(100vw-2rem)]`, `max-h-[calc(100dvh-2rem)]`, `rounded-lg`, 44×44 px close target, `gap-2` on stacked `DialogFooter`, and `DialogBody` flex-scroll pattern).
- Harden `ui/date-picker.tsx` (clamped popover width, safe mobile alignment, `text-base sm:text-sm` selects, larger touch controls) and `ui/input.tsx` (`text-base sm:text-sm`).
- Audit `Layout.tsx` footer tap targets and `AdminNav.tsx` mobile scrolling/active-item visibility.

### Wave 2 — Core Camper Flows, Forms & Account Views (`FR-004`, `FR-006`, `FR-007`, `FR-008`)

- Refactor `ScanForm.tsx` to use pinned header/footer `DialogBody` and `grid-cols-1 sm:grid-cols-2` date fields; verify `AreaCoveragePicker`, `ScanCard` delete modal, and `DestinationDetails` photo viewer at 375×667.
- Audit and polish `Home` + `SearchBar` + `SearchDropdown`, `SearchPage` filters/map/pagination, `Campground`, `RecreationArea`, `Dashboard` (populated + empty), `ScanDetail`, `Auth`, `InviteOnly`, `ChangePasswordRequired`, and `Profile` (`NotificationSettings` + `ActiveSessions` long-string wrapping).

### Wave 3 — Public / Informational Routes & 768 px Breakpoint (`FR-010`, `FR-011`, `FR-012`)

- Audit and polish `Providers`, `HowItWorks`, `FAQ`, `Contact`, `Ethos`, `Contribute`, `PrivacyPolicy`, `TermsOfService`, and verify clean mobile→desktop header/grid transitions at 768 px in both light and dark modes.

### Wave 4 — Admin Mobile Experience (`FR-009`)

- Add responsive stacked mobile card views (`md:hidden`) alongside existing desktop tables (`hidden md:block`) in `AdminUsers.tsx`, `AdminInvites.tsx`, and `AdminScans.tsx`.
- Upgrade `AdminUsers`, `AdminUserDetail`, and `AdminOperations` dialogs to use viewport-bounded pinned header/footer `DialogBody` with safe wrapping for generated passwords and JSON payloads.
- Harden self-contained scroll containers (`min-w-0` ancestors + `overflow-x-auto`), mobile metadata grids (`grid-cols-1 sm:grid-cols-2`, `break-all` for UUIDs/emails), wrapping filter bars, and `AdminTrendsPanel` chart legibility across `AdminOverview`, `AdminUserDetail`, `AdminScanDetail`, `AdminTargetDetail`, `AdminOperations`, and `AdminAudit`.

### Wave 5 — Automated Verification, Baselines & Audit Record (`FR-013`, `FR-014`, `FR-015`)

- Enforce `document.documentElement.scrollWidth <= window.innerWidth` in `src/frontend/tooling/run-snapshots.ts` across all mobile scenarios and add a 26-route automated overflow sweep covering 375 px, 390 px, and 768 px.
- Add representative mobile snapshots in light and dark themes for previously desktop-only routes and critical overlays. Use the project-locked Playwright Chromium build and the CI image’s fonts locally. Follow the [quickstart](quickstart.md) to update affected baselines and check mobile and desktop captures for unintended diffs.
- Record route-by-route findings and fixes in `docs/specs/20261126-182156-mobile-responsive-audit/audit-report.md`, update `docs/architecture/DESIGN_FRONTEND.md`, and check off `T4.1.6` in `docs/CHECKLIST.md` and Phase 4 Polish in `docs/PLAN.md`.
