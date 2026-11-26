---
description: "Dependency-ordered task list for the full 26-route mobile-responsive UI audit and polish (Phase 4 T4.1.6)"
---

# Tasks: Full Mobile-Responsive UI Audit & Polish

**Input**: Design documents from `docs/specs/034-mobile-responsive-audit/`

**Prerequisites**: `plan.md` (required), `spec.md` (required for user stories), `research.md`, `data-model.md`, `contracts/responsive-ui-contract.md`, `quickstart.md`

**Tests**: Included per Camply Constitution Principle V (Automated Verification) and Test-First Mentality. Write or update Vitest component tests before modifying UI code within each phase and verify Playwright overflow/visual baselines in Phase 7.

**Organization**: Tasks are grouped by user story (`US1`–`US5`) so each story can be implemented and verified independently.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: Maps task to a specific user story from `spec.md` (`[US1]`–`[US5]`)
- Exact repository-relative file paths are included in every task description

## Path Conventions

- Frontend UI primitives, components, and pages: `src/frontend/`
- Playwright visual snapshot & overflow tooling: `src/frontend/tooling/run-snapshots.ts`
- Visual snapshot baselines: `tests/frontend/snapshots/baselines/`
- Specification, audit record, and architecture docs: `docs/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Confirm baseline health and initialize the route-by-route audit tracking record

- [ ] T001 Confirm the existing frontend baseline passes (`task frontend:check && task frontend:lint && task frontend:test`) and initialize `docs/specs/034-mobile-responsive-audit/audit-report.md` with the 26-route inventory table from `docs/specs/034-mobile-responsive-audit/data-model.md`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Upgrade shared navigation, modal, date-picker, and input primitives that all user stories rely on

**⚠️ CRITICAL**: Complete this phase before beginning User Stories 1–5.

- [ ] T002 Create the `@radix-ui/react-dialog`-backed slide-over drawer primitive (`Sheet`, `SheetTrigger`, `SheetOverlay`, `SheetContent` with `side?: "left" | "right"`, `w-[min(85vw,320px)] h-dvh`, dimmed backdrop `bg-black/80`, `44×44 px` close button, focus trap, Escape/backdrop close, and `motion-reduce:transition-none`) in `src/frontend/components/ui/sheet.tsx` with unit tests in `src/frontend/components/ui/sheet.test.tsx`
- [ ] T003 [P] Upgrade `DialogContent` (`w-[calc(100vw-2rem)] sm:w-full max-w-lg max-h-[calc(100dvh-2rem)] rounded-lg`, `44×44 px` close hit area), `DialogFooter` (`flex-col-reverse gap-2 sm:flex-row sm:justify-end`), and add `DialogBody` (pinned header/footer flex-scroll layout) in `src/frontend/components/ui/dialog.tsx`
- [ ] T004 [P] Update `Input` in `src/frontend/components/ui/input.tsx` to use `text-base sm:text-sm` (16 px on mobile, 14 px on `sm+`) to prevent iOS Safari focus auto-zoom while preserving desktop typography
- [ ] T005 [P] Harden `DatePicker` in `src/frontend/components/ui/date-picker.tsx` and update tests in `src/frontend/components/ui/date-picker.test.tsx`: clamp popover width with `w-[min(calc(100vw-3rem),316px)] max-w-full`, align cleanly inside narrow dialogs without horizontal clipping, use `text-base sm:text-xs` on month/year `<select>` controls, and enlarge prev/next month and day button touch ergonomics
- [ ] T006 Refactor `Header` in `src/frontend/components/Header.tsx` (depends on T002) to keep `<header>` consistently `sticky top-0 z-50` (removing mobile hide-on-scroll), replace the inline sticky dropdown with `Sheet` (`min-h-11 min-w-11` menu trigger with `aria-expanded`, auto-close on `location.pathname` change, route tap, backdrop tap, and Escape), and add/update tests in `src/frontend/components/Layout.test.tsx`
- [ ] T007 [P] Audit and refine footer link wrapping/touch targets in `src/frontend/components/Layout.tsx` and mobile horizontal scrolling/active-item visibility in `src/frontend/components/AdminNav.tsx`

**Checkpoint**: Shared primitives (`Sheet`, `Dialog`/`DialogBody`, `Input`, `DatePicker`, sticky `Header`, `Layout`, `AdminNav`) are verified and pass Vitest; user stories can now proceed in parallel.

---

## Phase 3: User Story 1 - Complete core camper discovery and monitoring journeys on phones (Priority: P1) 🎯 MVP

**Goal**: Ensure every core camper journey—Home search, Explore (filters + map + pins), Campground & Recreation Area details, Dashboard, and Scan Detail—fits cleanly on `375 px` and `390 px` phones with zero horizontal overflow, clear hierarchy, and comfortable touch targets.

**Independent Test**: Render Home (with search dropdown), Explore (expanded/collapsed map, filters, selected pin), Campground & Recreation Area details (carousel, overview map, photo viewer), Dashboard (populated/expanded/empty), and Scan Detail (calendar, cards, grid) at `375×812` and `390×844` in light and dark modes; confirm zero document overflow, readable wrapping, and `44×44 px` primary touch targets.

### Tests for User Story 1 ⚠️

- [ ] T008 [P] [US1] Add/update mobile layout and interaction assertions for search dropdown clamping, Explore filter controls, destination headers, and Dashboard scan group wrapping in `src/frontend/pages/SearchPage.test.tsx`, `src/frontend/pages/Dashboard.test.tsx`, `src/frontend/pages/Campground.test.tsx`, and `src/frontend/pages/RecreationArea.test.tsx`

### Implementation for User Story 1

- [ ] T009 [P] [US1] Audit and polish `src/frontend/pages/Home.tsx`, `src/frontend/components/SearchBar.tsx`, and `src/frontend/components/SearchDropdown.tsx` for viewport-clamped autocomplete suggestions, clean long-name truncation, and `44×44 px` touch targets on `375 px` / `390 px` viewports
- [ ] T010 [P] [US1] Audit and polish `src/frontend/pages/SearchPage.tsx` and `src/frontend/components/ExploreMap.tsx` for stacked mobile filters, touch-friendly filter/RV buttons, unobstructed map toggle and selected-pin preview card, and tappable pagination controls
- [ ] T011 [P] [US1] Audit and polish `src/frontend/pages/Campground.tsx`, `src/frontend/pages/RecreationArea.tsx`, and `src/frontend/components/DestinationDetails.tsx` so long destination titles, provider badges, monitoring CTAs, child campground rows, and the photo viewer dialog wrap and fit cleanly without overflow
- [ ] T012 [US1] Audit and polish `src/frontend/pages/Dashboard.tsx`, `src/frontend/components/ScanCard.tsx`, and `src/frontend/pages/ScanDetail.tsx` (verifying stat card grids, campground group headers, empty state, badge/pill wrapping, and `FoundCampsites` calendar/cards/grid ergonomics at `375 px`)

**Checkpoint**: User Story 1 (MVP) delivers clean, overflow-free mobile camper discovery and monitoring across all core routes.

---

## Phase 4: User Story 2 - Complete forms, pickers, dialogs, and account flows comfortably on small screens (Priority: P1)

**Goal**: Make all modal dialogs, nested calendar/campground pickers, authentication forms, invite-only access flows, and Profile settings (Pushover, ntfy, Active Sessions) completely usable on compact `375×667` and `390×844` screens with pinned dialog headers/footers and zero browser auto-zoom.

**Independent Test**: On `375×667` and `390×844` viewports, open Create/Edit Scan (scrolling the dialog body while Save/Cancel stay pinned, opening Check-in/Check-out calendars and Area Coverage Picker), trigger Scan delete confirmation/error, submit Sign In / Sign Up / Forced Password Change / Invite-Only forms, and update Profile (long custom ntfy URLs, copy/test actions, Active Sessions revocation); confirm every input, popover, and button remains reachable with zero overflow.

### Tests for User Story 2 ⚠️

- [ ] T013 [P] [US2] Add/update Vitest component tests covering pinned `ScanForm` header/footer and stacked mobile date fields, `Profile` / `NotificationSettings` / `ActiveSessions` long-string containment, and `InviteOnly` / `ChangePasswordRequired` form accessibility in `src/frontend/components/ScanForm.test.tsx`, `src/frontend/pages/Profile.test.tsx`, `src/frontend/pages/InviteOnly.test.tsx`, and `src/frontend/components/ActiveSessions.test.tsx`

### Implementation for User Story 2

- [ ] T014 [US2] Refactor `src/frontend/components/ScanForm.tsx` and `src/frontend/components/AreaCoveragePicker.tsx` to use viewport-bounded `DialogContent` with pinned `DialogHeader`/`DialogFooter` and scrollable `DialogBody` (fitting `375×667`), stacked `grid-cols-1 sm:grid-cols-2` Check-in/Check-out `DatePicker` fields, `text-base sm:text-sm` native `<select>` controls, and non-overflowing campground selection rows
- [ ] T015 [P] [US2] Audit and polish `src/frontend/pages/Auth.tsx`, `src/frontend/pages/InviteOnly.tsx`, and `src/frontend/components/ChangePasswordRequired.tsx` for auto-zoom-safe `text-base sm:text-sm` inputs, stacked actions, clean error alert wrapping, and `44×44 px` touch targets
- [ ] T016 [P] [US2] Audit and polish `src/frontend/pages/Profile.tsx`, `src/frontend/components/NotificationSettings.tsx`, and `src/frontend/components/ActiveSessions.tsx` so long emails, custom ntfy server URLs, topics, access tokens, and session user-agents wrap safely (`min-w-0 break-all` / `break-words`) with tappable copy, test, save, and revoke controls
- [ ] T017 [P] [US2] Audit and polish scan delete confirmation and delete-error dialogs in `src/frontend/components/ScanCard.tsx` using bounded `DialogContent` and spaced stacked `DialogFooter` actions

**Checkpoint**: User Stories 1 and 2 together make every camper discovery, scan-creation, authentication, and account-management flow smooth on small phones.

---

## Phase 5: User Story 3 - Navigate consistently across all public, informational, and authenticated views on mobile (Priority: P2)

**Goal**: Polish every public and informational page and verify the `768×1024` tablet navigation handoff so the entire site feels cohesive in both light and dark modes.

**Independent Test**: Visit Providers, How It Works, FAQ, Contact, Privacy Policy, Terms of Service, and enabled community pages (Ethos, Contribute) at `375×812`, `390×844`, and `768×1024` in light and dark modes; verify zero overflow, clean typography/grid stacking, tappable controls, and crisp header transition at `768 px`.

### Implementation for User Story 3

- [ ] T018 [P] [US3] Audit and polish `src/frontend/pages/Providers.tsx`, `src/frontend/pages/HowItWorks.tsx`, and `src/frontend/pages/FAQ.tsx` for responsive grid stacking, badge wrapping, `44 px` accordion triggers, and consistent mobile spacing/contrast
- [ ] T019 [P] [US3] Audit and polish `src/frontend/pages/Contact.tsx`, `src/frontend/pages/Ethos.tsx`, `src/frontend/pages/Contribute.tsx`, `src/frontend/pages/PrivacyPolicy.tsx`, and `src/frontend/pages/TermsOfService.tsx` for `text-base sm:text-sm` form inputs, clean prose/URL wrapping, and mobile padding
- [ ] T020 [US3] Audit the `768×1024` tablet breakpoint transition in `src/frontend/components/Header.tsx` and public/camper grid layouts to confirm zero awkward header link wrapping or right-edge clipping

**Checkpoint**: All public, informational, legal, and community routes plus tablet breakpoint handoffs are polished and consistent.

---

## Phase 6: User Story 4 - Inspect and administer the platform effectively on mobile devices (Priority: P2)

**Goal**: Deliver a clean mobile admin experience using stacked mobile cards (`md:hidden`) for action-heavy management lists (`AdminUsers`, `AdminInvites`, `AdminScans`), self-contained horizontal-scroll tables (`min-w-0` ancestors + `overflow-x-auto`) for dense telemetry/log/detail tables, legible mobile trend charts, and pinned `DialogBody` admin modals.

**Independent Test**: Navigate through all 9 Admin routes via `AdminNav` at `375×812` and `390×844` in light and dark modes; verify Users, Invitations, and Scans render stacked mobile cards with tappable actions, Operations/Audit/Detail/Trend tables scroll smoothly inside contained wrappers with zero document overflow, Create User & Reset Password dialogs keep revealed passwords safely wrapped with reachable actions, and Recharts legends/axes stay legible.

### Tests for User Story 4 ⚠️

- [ ] T021 [P] [US4] Update and expand Vitest admin tests to cover hybrid mobile cards alongside desktop tables without query ambiguity and pinned Create/Reset Password dialogs in `src/frontend/pages/admin/AdminPages.test.tsx`, `src/frontend/pages/admin/AdminInvites.test.tsx`, `src/frontend/pages/admin/AdminUsersCreate.test.tsx`, `src/frontend/pages/admin/AdminInteractions.test.tsx`, and `src/frontend/pages/admin/AdminUserDetail.test.tsx`

### Implementation for User Story 4

- [ ] T022 [P] [US4] Add stacked mobile user cards (`md:hidden`) alongside the existing desktop table (`hidden md:block overflow-x-auto`), wrapping filter bar, and pinned `DialogBody` Create User & Reset Password dialogs (with `break-all` temporary password reveal/copy) in `src/frontend/pages/admin/AdminUsers.tsx`
- [ ] T023 [P] [US4] Add stacked mobile invitation cards (`md:hidden`) alongside the existing desktop table (`hidden md:block overflow-x-auto`) with `44 px` Approve/Revoke buttons and wrapping status tabs in `src/frontend/pages/admin/AdminInvites.tsx`
- [ ] T024 [P] [US4] Add stacked mobile scan cards (`md:hidden`) alongside the existing desktop table (`hidden md:block overflow-x-auto`) with wrapping filter bar and pause/resume/delete controls in `src/frontend/pages/admin/AdminScans.tsx`
- [ ] T025 [P] [US4] Harden mobile metadata grids (`grid-cols-1 sm:grid-cols-2`, `min-w-0 break-all` for UUIDs/emails), pinned Reset Password dialog, and self-contained `overflow-x-auto` tables in `src/frontend/pages/admin/AdminUserDetail.tsx`, `src/frontend/pages/admin/AdminScanDetail.tsx`, and `src/frontend/pages/admin/AdminTargetDetail.tsx`
- [ ] T026 [P] [US4] Harden mobile KPI grids, Recharts axis/legend legibility, wrapping time-window/filter controls, pinned task detail dialog, and self-contained `overflow-x-auto` tables (`min-w-0` parent wrappers) in `src/frontend/pages/admin/AdminOverview.tsx`, `src/frontend/components/admin/AdminTrendsPanel.tsx`, `src/frontend/pages/admin/AdminOperations.tsx`, and `src/frontend/pages/admin/AdminAudit.tsx`

**Checkpoint**: All 9 Admin screens are fully usable on mobile with hybrid cards, contained tables, legible charts, and bounded dialogs.

---

## Phase 7: User Story 5 - Guard mobile quality continuously across routes and key states (Priority: P3)

**Goal**: Lock in the audit permanently with automated document-level zero-overflow enforcement across all 26 routes (`375 px`, `390 px`, `768 px`) and one representative mobile visual baseline (balancing light and dark themes) for every previously desktop-only route and critical overlay.

**Independent Test**: Run `task snapshot:docker -- --check` and confirm all existing desktop baselines pass with zero unintended diffs, all newly added mobile visual baselines pass, and every single route passes the automated `document.documentElement.scrollWidth <= window.innerWidth` assertion.

### Implementation for User Story 5

- [ ] T027 [US5] Add automated `document.documentElement.scrollWidth <= window.innerWidth` enforcement to every mobile/tablet scenario (`viewport.width <= 768`) and add an automated 26-route overflow sweep at `375 px`, `390 px`, and `768 px` in `src/frontend/tooling/run-snapshots.ts`
- [ ] T028 [US5] Add one representative mobile visual snapshot scenario (balancing `light` and `dark` across the suite) for every previously desktop-only route and critical overlay in `src/frontend/tooling/run-snapshots.ts` (open mobile nav drawer, `Auth`, `Providers`, `HowItWorks`, `FAQ`, `Contact`, `Ethos`, `Contribute`, `Privacy`, `Home search dropdown`, `Map selected`, `Dashboard empty`, `Profile` with Active Sessions, `ScanForm` dialog & check-in calendar at `375×667`, `Scan delete error`, `AdminUsers` list + Create User password reveal, `AdminUserDetail`, `AdminInvites`, `AdminScans`, `AdminScanDetail`, `AdminTargetDetail`, `AdminAudit`, and `AdminTrendsPanel` API table)
- [ ] T029 [US5] Capture new and intentionally updated mobile visual baselines in `tests/frontend/snapshots/baselines/` via `task snapshot:docker -- --update --filter mobile` and verify both mobile and desktop suites pass `task snapshot:docker -- --check` with zero unintended desktop diffs
- [ ] T030 [US5] Generate and inspect the visual comparison gallery (`task snapshot:report` → `tmp/snapshots/report.html`) to confirm visual polish, alignment, and light/dark contrast across all audited views

**Checkpoint**: Automated zero-overflow and visual regression gates permanently protect all 26 routes on mobile and desktop.

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Complete traceability documentation, close roadmap item `T4.1.6`, and run final quality gates

- [ ] T031 [P] Complete the route-by-route audit findings and remediation summary across all 26 routes in `docs/specs/034-mobile-responsive-audit/audit-report.md` (`FR-015` / `SC-007`)
- [ ] T032 [P] Update `docs/architecture/DESIGN_FRONTEND.md` to document the `Sheet` slide-over mobile drawer, viewport-bounded pinned `DialogBody`, clamped `DatePicker`, and hybrid Admin mobile card/table patterns
- [ ] T033 [P] Mark `T4.1.6` complete in `docs/CHECKLIST.md`, mark Phase 4 Polish complete in `docs/PLAN.md`, and add spec `034` to `docs/specs/index.md`
- [ ] T034 Run the full verification pipeline per `docs/specs/034-mobile-responsive-audit/quickstart.md` (`task frontend:fix && task frontend:check && task frontend:lint && task frontend:test && task snapshot:docker -- --check`) and confirm zero errors, zero warnings, and 100% passing checks

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies — start immediately.
- **Phase 2 (Foundational)**: Depends on Phase 1 — **BLOCKS** all user stories (`US1`–`US5`) because `Sheet`, `Dialog`/`DialogBody`, `Input`, `DatePicker`, and sticky `Header` are shared across all routes.
- **Phases 3–6 (`US1`, `US2`, `US3`, `US4`)**: All depend on Phase 2 completion; they touch disjoint page files and can proceed in parallel or sequentially in priority order (`US1` → `US2` → `US3` → `US4`).
- **Phase 7 (`US5` — Visual & Overflow Verification)**: Depends on Phases 3–6 completing so captured mobile baselines reflect all remediations.
- **Phase 8 (Polish & Closing)**: Depends on Phase 7 passing cleanly.

### User Story Dependencies

- **User Story 1 (P1)**: Independent after Phase 2.
- **User Story 2 (P1)**: Independent after Phase 2 (`T014` depends on `T003`–`T005`; `T017` shares `ScanCard.tsx` with `T012`, so sequence `T012` → `T017` if working sequentially).
- **User Story 3 (P2)**: Independent after Phase 2 (`T020` verifies `Header.tsx` from `T006` at `768 px`).
- **User Story 4 (P2)**: Independent after Phase 2 (`T022`–`T026` touch separate admin files and can run in parallel).
- **User Story 5 (P3)**: Depends on `US1`–`US4` UI fixes so final baselines capture the polished mobile state.

### Parallel Opportunities

```bash
# Phase 2 primitives (independent files):
Task: "T003 [P] Upgrade DialogContent, DialogFooter, and DialogBody in src/frontend/components/ui/dialog.tsx"
Task: "T004 [P] Update Input text-base sm:text-sm in src/frontend/components/ui/input.tsx"
Task: "T005 [P] Harden DatePicker clamping in src/frontend/components/ui/date-picker.tsx"
Task: "T007 [P] Audit footer and AdminNav in src/frontend/components/Layout.tsx and src/frontend/components/AdminNav.tsx"

# Phase 6 Admin mobile polish (independent page files):
Task: "T022 [P] [US4] Hybrid mobile cards and pinned dialogs in src/frontend/pages/admin/AdminUsers.tsx"
Task: "T023 [P] [US4] Hybrid mobile cards in src/frontend/pages/admin/AdminInvites.tsx"
Task: "T024 [P] [US4] Hybrid mobile cards in src/frontend/pages/admin/AdminScans.tsx"
Task: "T025 [P] [US4] Detail metadata grids and scroll tables in AdminUserDetail/AdminScanDetail/AdminTargetDetail"
Task: "T026 [P] [US4] KPIs, Recharts, Operations, and Audit scroll containment"

# Phase 8 documentation updates:
Task: "T031 [P] Complete docs/specs/034-mobile-responsive-audit/audit-report.md"
Task: "T032 [P] Update docs/architecture/DESIGN_FRONTEND.md"
Task: "T033 [P] Update docs/CHECKLIST.md, docs/PLAN.md, and docs/specs/index.md"
```

---

## Implementation Strategy

### MVP First (Phases 1–3: Setup + Foundational + US1)

1. Complete Phase 1 (Setup) and Phase 2 (Foundational primitives & sticky `Header` + `Sheet` drawer).
2. Complete Phase 3 (`US1` — core camper discovery & monitoring on phones).
3. **Checkpoint**: Validate `US1` Vitest tests and mobile overflow on core camper routes.

### Incremental Delivery

1. Add Phase 4 (`US2` — pinned `ScanForm`, clamped `DatePicker`, Auth/Profile/Active Sessions).
2. Add Phase 5 (`US3` — public/informational routes & `768 px` tablet handoff).
3. Add Phase 6 (`US4` — hybrid Admin cards, contained telemetry/log tables, legible charts, bounded admin dialogs).
4. Complete Phase 7 (`US5` — 26-route overflow enforcement + representative mobile baselines in Docker Playwright) and Phase 8 (audit report, docs, `T4.1.6` closure).

---

## Notes

- `[P]` marks tasks touching independent files that can run concurrently.
- `[US#]` links each task to its user story in `spec.md` for end-to-end traceability.
- Note on environments without Docker/Chromium: if `task snapshot:docker` cannot run inside a sandboxed container without a Docker daemon, run all Vitest/typecheck/lint gates locally and capture/verify the new Playwright baselines in a Docker-enabled host or CI runner before merging.
