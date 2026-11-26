# Research: Full Mobile-Responsive UI Audit & Polish

**Feature**: `034-mobile-responsive-audit`
**Date**: 2026-11-26
**Spec**: [spec.md](spec.md)

## Overview

This research consolidates architectural and UX decisions for executing the full 26-route mobile-responsive audit (`T4.1.6`) across `src/frontend/` without adding runtime dependencies, altering backend APIs, or regressing desktop layouts.

---

## 1. Mobile Navigation Drawer & Sticky Header (`FR-003`)

- **Decision**: Add a reusable `Sheet` UI primitive built on the already-installed `@radix-ui/react-dialog` (`^1.3.1`) in `src/frontend/components/ui/sheet.tsx`, replace the inline sticky dropdown in `src/frontend/components/Header.tsx` with a right-side slide-over drawer, and remove mobile hide-on-scroll logic so `<header>` stays consistently `sticky top-0 z-50`.
- **Rationale**:
  - `@radix-ui/react-dialog` already ships in `package.json` and natively provides focus trapping, dimmed overlay backdrop, body scroll locking, Escape dismissal, outside-click dismissal, and ARIA dialog semantics (`role="dialog"`, `aria-modal="true"`).
  - The current `Header.tsx` implementation uses a `sticky top-[73px]` inline dropdown without backdrop, focus containment, or Escape handling, and its `lastScrollY` hide-on-scroll behavior causes visual jumps and misalignment when toggled mid-scroll.
  - Adding `motion-reduce:transition-none` / `motion-reduce:animate-none` respects user reduced-motion preferences.
- **Alternatives considered**:
  - _Polishing the existing inline dropdown_: Rejected during clarification (Option B selected); inline dropdowns cannot cleanly trap focus or prevent background scroll bleed on long pages.
  - _Installing a separate drawer library (`vaul`)_: Rejected to avoid unnecessary third-party dependency additions when `@radix-ui/react-dialog` already covers all drawer requirements cleanly.

---

## 2. Viewport-Bounded Dialogs with Pinned Header/Footer & Clamped Pickers (`FR-004`, `FR-005`)

- **Decision**: Upgrade `src/frontend/components/ui/dialog.tsx` to enforce safe mobile viewport bounds (`w-[calc(100vw-2rem)] sm:w-full`, `max-h-[calc(100dvh-2rem)]`, `rounded-lg`), increase the close button tap target to `44×44 px` (`h-11 w-11` effective hit area), add vertical gap (`gap-2`) to stacked mobile `DialogFooter` buttons, and introduce a `DialogBody` (flex column layout `flex flex-col max-h-[calc(100dvh-2rem)] p-0` with pinned header/footer and `flex-1 overflow-y-auto` body) for multi-field dialogs (`ScanForm`, `AdminUsers` Create/Reset dialogs, `AdminUserDetail` Reset dialog, `AdminOperations` task detail dialog). Update `src/frontend/components/ui/date-picker.tsx` to clamp popover width (`w-[min(calc(100vw-3rem),316px)] max-w-full`), support mobile-safe alignment inside dialogs, stack check-in/check-out date triggers (`grid-cols-1 sm:grid-cols-2`) in `ScanForm.tsx`, and enlarge interactive controls inside the calendar.
- **Rationale**:
  - Current `DialogContent` uses `w-full max-w-lg` with zero horizontal margin on mobile, a `16×16` close icon, and `sm:space-x-2` on `DialogFooter` (leaving zero vertical gap when buttons stack via `flex-col-reverse`).
  - `DatePicker` currently positions a fixed `w-[290px]` popover absolutely (`left-0` / `right-0`) inside scrolling containers, which risks horizontal clipping on 375 px screens—especially when paired side-by-side in a 2-column date grid inside a padded modal.
  - Pinning `DialogHeader` and `DialogFooter` while scrolling `DialogBody` guarantees Close, Cancel, and Submit remain reachable on short 375×667 screens even when all filter sections are expanded.
- **Alternatives considered**:
  - _Full-screen mobile sheets for complex forms_: Rejected during clarification (Option B selected); pinned-header/footer bounded dialogs preserve a unified dialog mental model across all screen sizes with less layout divergence.
  - _Replacing `DatePicker` with native `<input type="date">` on mobile_: Rejected because `DatePicker` provides stay-length previews, check-out anchoring, and quick duration presets tested across `ScanForm.dates.test.tsx` and `date-picker.test.tsx`.

---

## 3. Preventing iOS Safari Auto-Zoom & Touch Target Ergonomics (`FR-002`, `FR-005`)

- **Decision**: Update `src/frontend/components/ui/input.tsx` and native `<select>` / `<textarea>` form controls to use `text-base sm:text-sm` (`16px` on mobile, preserving `14px` on `sm+` desktop views), and audit primary mobile touch targets (header trigger, dialog close, pagination, filter chips, theme toggle, row action buttons, copy/test buttons) so they achieve at least `44×44 px` effective tap area (via `min-h-11 min-w-11` or padded hit regions) on mobile viewports without inflating desktop density.
- **Rationale**:
  - Mobile Safari automatically zooms the viewport whenever a focused form field has computed `font-size < 16px`, causing disorienting horizontal pan on Auth, Profile, ScanForm, and Admin forms. Using `text-base sm:text-sm` eliminates auto-zoom completely on phones while keeping desktop pixel-identical.
  - Primary interactive controls using `h-10` (40px) or `h-7`/`h-8` (28–32px) on touchscreens benefit from responsive mobile sizing (`min-h-[44px] sm:min-h-0` or `h-11 sm:h-10` on primary triggers) while compact secondary tags maintain ≥8 px spacing (`gap-2`).
- **Alternatives considered**:
  - _Disabling pinch-zoom via `<meta name="viewport" content="maximum-scale=1">`_: Rejected as an accessibility violation (WCAG 1.4.4).

---

## 4. Hybrid Mobile Strategy for Admin Tables (`FR-009`)

- **Decision**: Implement responsive stacked mobile card views (`md:hidden`) alongside existing desktop tables (`hidden md:block overflow-x-auto`) for the three action-heavy management lists (`AdminUsers.tsx`, `AdminInvites.tsx`, `AdminScans.tsx`), while keeping and hardening self-contained horizontal scroll containers (`overflow-x-auto`, `min-w-0` on parent flex/grid wrappers, readable cell wrapping/truncation) for dense telemetry, log, and detail tables (`AdminOperations.tsx`, `AdminAudit.tsx`, `AdminScanDetail.tsx`, `AdminTargetDetail.tsx`, `AdminUserDetail.tsx`, `AdminTrendsPanel.tsx`).
- **Rationale**:
  - Selected during clarification (Option B). Action-heavy management rows contain emails, status badges, and multiple mutation buttons (approve/revoke, reset password, toggle admin/scanning, pause/delete scan) that are awkward to scroll horizontally to reach on a phone.
  - Telemetry/log tables (task attempts, audit events, API percentile trend matrices) require side-by-side column scanning where horizontal scroll inside a contained wrapper is clearer and less noisy than tall repetitive cards.
  - Keeping card and table markup colocated within each admin page (using small shared subcomponents only where repeated) honors Simplicity First and preserves existing desktop tables and tests unchanged.
- **Alternatives considered**:
  - _Scroll-only tables everywhere_: Rejected during clarification; makes quick mobile admin actions (approving an invite, resetting a password) clunky.
  - _Stacked cards for every table including audit/task logs_: Rejected during clarification; loses tabular comparability and adds unnecessary boilerplate.

---

## 5. Long-String Containment, Flex/Grid Overflow Traps & Recharts Mobile Sizing (`FR-001`, `FR-008`, `FR-009`)

- **Decision**: Systematically audit all 26 routes for the four classic Tailwind mobile overflow traps:
  1. Missing `min-w-0` on flex/grid children containing long text or scrollable tables (especially `AdminUserDetail`, `AdminScanDetail`, `AdminTargetDetail`, `Profile`, `NotificationSettings`, `ActiveSessions`).
  2. Multi-column `grid-cols-2` metadata blocks with long emails/UUIDs/URLs (switch to `grid-cols-1 sm:grid-cols-2` with `break-words` / `break-all`).
  3. Non-wrapping header/toolbar `flex items-center justify-between` rows (add `flex-wrap gap-2` or `flex-col sm:flex-row`).
  4. Chart legends/axes in `AdminTrendsPanel.tsx` on 375 px screens (responsive height, angled/thinned ticks or concise tick formatting, wrapping time-window/metric controls).
- **Rationale**:
  - Even when inner tables have `overflow-x-auto`, a CSS Grid or flex ancestor without `min-w-0` expands to the table's intrinsic width and creates document-level horizontal overflow (`scrollWidth > innerWidth`).

---

## 6. Automated Mobile Visual & Overflow Verification (`FR-014`, `SC-005`)

- **Decision**:
  1. Add an automated document-level horizontal overflow assertion (`document.documentElement.scrollWidth <= window.innerWidth`) to every mobile scenario executed in `src/frontend/tooling/run-snapshots.ts` (and verify across 375 px, 390 px, and 768 px in an automated route-sweep check).
  2. Add one representative mobile visual baseline (balancing `light` and `dark` themes across the newly covered routes) for every previously desktop-only route and critical overlay (~24–26 new mobile scenarios, bringing mobile coverage to 100% of application routes and key dialogs/pickers).
  3. Capture and update visual baselines inside the deterministic CI Playwright Docker container (`task snapshot:docker -- --update`) so Linux font rendering matches GitHub Actions CI with zero platform drift.
- **Rationale**:
  - Currently 24 desktop scenarios lack mobile baselines (`auth`, `providers`, `how-it-works`, `faq`, `ethos`, `home-search-dropdown`, `map-selected`, `dashboard-empty`, `profile`, `scan-form-dialog`, `scan-form-checkin-calendar`, `scan-form-checkout-calendar`, `scan-delete-error`, and 11 admin scenarios), plus `contact`, `contribute`, `privacy`, `terms`, and the open mobile navigation drawer.
  - Adding one representative theme per newly added route keeps CI snapshot runtime fast (parallel Playwright workers in `run-snapshots.ts`) while locking in visual and zero-overflow verification across all 26 routes.
- **Alternatives considered**:
  - _Adding both light and dark baselines for every single route (+50 PNGs)_: Rejected during clarification (Option A selected) to balance coverage with CI runtime and baseline maintenance overhead.
