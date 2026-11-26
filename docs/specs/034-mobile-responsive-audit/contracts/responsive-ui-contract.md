# Responsive UI & Verification Contracts

**Feature**: `034-mobile-responsive-audit`
**Date**: 2026-11-26
**Spec**: [spec.md](../spec.md)

This contract defines the shared component interfaces, layout invariants, and automated verification gates that all audited routes and primitives must satisfy.

---

## 1. Document Overflow Invariant (`FR-001`, `SC-001`)

For every application route and active mobile overlay at `375 px`, `390 px`, and `768 px`:

```ts
document.documentElement.scrollWidth <= window.innerWidth;
```

- Horizontal scrolling is permitted **only** inside explicitly scoped inner containers (e.g., `AdminNav`, `AvailabilityGrid`, dense telemetry/log/detail tables) whose ancestors enforce `min-w-0` and `overflow-x-hidden` / proper grid sizing so the document itself never widens.

---

## 2. Touch Target & Input Ergonomics Contract (`FR-002`, `FR-005`, `SC-002`)

- **Primary interactive controls on mobile** (header menu trigger, dialog close button, modal submit/cancel buttons, form controls, navigation drawer links, pagination buttons, admin card action buttons): minimum `44×44 px` effective touch target (`min-h-[44px]` / `h-11 w-11` on mobile; may step back to desktop height at `sm:`/`md:` where needed to protect desktop baselines).
- **Compact secondary chips/toggles** (e.g., calendar day cells, filter pills): minimum `36×36 px` with `>= 6–8 px` gap so adjacent taps do not collide.
- **Form inputs (`Input`, `<select>`, `<textarea>`)**: computed font size `>= 16 px` below `sm:` (`text-base sm:text-sm`) to eliminate iOS Safari automatic focus zoom.

---

## 3. `Sheet` Slide-Over Drawer Contract (`src/frontend/components/ui/sheet.tsx`, `FR-003`)

Built on `@radix-ui/react-dialog` (`DialogPrimitive`):

| Export                                                        | Responsibility                                                                                                                                                                                |
| :------------------------------------------------------------ | :-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `Sheet`                                                       | Controlled/uncontrolled root (`open`, `onOpenChange`)                                                                                                                                         |
| `SheetTrigger`                                                | Button trigger exposing `aria-expanded` and `aria-controls`                                                                                                                                   |
| `SheetOverlay`                                                | Full-viewport dimmed backdrop (`fixed inset-0 z-50 bg-black/80`)                                                                                                                              |
| `SheetContent`                                                | Slide-over panel (`side?: "left" \| "right"`, default `"right"`), `w-[min(85vw,320px)] h-dvh`, focus trap, Escape/outside-tap close, `44×44 px` close button, `motion-reduce:transition-none` |
| `SheetHeader`, `SheetTitle`, `SheetDescription`, `SheetClose` | Accessible labeling & close primitives                                                                                                                                                        |

**Header contract (`Header.tsx`)**:

- `<header>` stays consistently `sticky top-0 z-50` on all viewports (no hide-on-scroll transform on mobile).
- Mobile menu trigger is `min-h-11 min-w-11` (`44×44 px`) with `aria-label="Toggle mobile menu"` and `aria-expanded`.
- Selecting any link, pressing `Escape`, tapping the backdrop, or changing `location.pathname` closes the drawer cleanly.

---

## 4. `Dialog` & `DatePicker` Contract (`FR-004`, `SC-003`)

**`DialogContent` (`src/frontend/components/ui/dialog.tsx`)**:

- Default responsive sizing: `w-[calc(100vw-2rem)] sm:w-full max-w-lg max-h-[calc(100dvh-2rem)] rounded-lg`.
- Close button: `44×44 px` hit area (`h-11 w-11` centered icon) with `aria-label` / `sr-only` `"Close"`.
- `DialogFooter`: `flex flex-col-reverse gap-2 sm:flex-row sm:justify-end sm:gap-2` (no overlapping stacked mobile buttons).
- Optional `DialogBody` export (or pinned-layout class convention) for multi-field dialogs (`ScanForm`, `AdminUsers` Create/Reset, `AdminUserDetail` Reset, `AdminOperations` Task Detail): outer `flex flex-col overflow-hidden p-0`, pinned header (`px-6 pt-6 pb-4 shrink-0`), scrollable `DialogBody` (`flex-1 min-h-0 overflow-y-auto px-6 py-2`), pinned footer (`px-6 py-4 border-t shrink-0`).

**`DatePicker` (`src/frontend/components/ui/date-picker.tsx`)**:

- Popover width clamped via `w-[min(calc(100vw-3rem),316px)] max-w-full`.
- On mobile (`< sm`), popover aligns cleanly inside its full-width stacked container without overflowing left or right past the dialog or viewport edge.
- Month/year `<select>` controls use `text-base sm:text-xs` (or `sm:text-sm`) to avoid iOS zoom; prev/next month buttons use at least `h-9 w-9` (`h-10 w-10` on mobile) with clear hit regions.
- In `ScanForm.tsx`, Check-in and Check-out inputs use `grid-cols-1 sm:grid-cols-2 gap-4` so each date trigger has full mobile width.

---

## 5. Admin Hybrid Table Contract (`FR-009`, `SC-004`)

| Page                                                                                                           | Mobile Pattern (`< md`)                                                                                                          | Desktop Pattern (`>= md`)  |
| :------------------------------------------------------------------------------------------------------------- | :------------------------------------------------------------------------------------------------------------------------------- | :------------------------- |
| `AdminUsers`                                                                                                   | Stacked user cards (email with `break-all`, role/status/invited badges, scan count, detail link + Reset/Admin/Scanning controls) | Existing desktop `<table>` |
| `AdminInvites`                                                                                                 | Stacked invitation cards (email with `break-all`, status badge, timestamps, Approve/Revoke buttons)                              | Existing desktop `<table>` |
| `AdminScans`                                                                                                   | Stacked scan cards (destination, user email, dates/filters, status badge, detail link + Pause/Resume/Delete buttons)             | Existing desktop `<table>` |
| `AdminOperations`, `AdminAudit`, `AdminScanDetail`, `AdminTargetDetail`, `AdminUserDetail`, `AdminTrendsPanel` | Self-contained `overflow-x-auto` table wrapper inside `min-w-0` parent with `scrollWidth <= innerWidth` on document              | Existing desktop `<table>` |

- All existing Vitest admin tests (`AdminPages.test.tsx`, `AdminInteractions.test.tsx`, `AdminInvites.test.tsx`, `AdminUsersCreate.test.tsx`, `AdminUserDetail.test.tsx`, `AdminOperations.test.tsx`) must continue passing without duplicate-element query ambiguity (ensure accessible roles/labels remain unambiguous across responsive markup or test desktop/mobile cleanly).

---

## 6. Automated Visual & Overflow Verification Contract (`FR-014`, `SC-005`, `SC-006`)

In `src/frontend/tooling/run-snapshots.ts`:

- Every scenario with `viewport.width <= 768` MUST assert `document.documentElement.scrollWidth <= window.innerWidth` and fail the run with the scenario name and offending pixel delta if overflow occurs.
- Every previously desktop-only route and critical overlay MUST have at least one representative mobile scenario (balancing `light` and `dark` themes across the suite), including:
  - Open mobile navigation drawer
  - `ScanForm` dialog and open check-in calendar popover at `375×667`
  - All 9 Admin routes (Overview + trends table, Users + Create User password reveal, User Detail, Invitations, Scans, Scan Detail, Target Detail, Operations, Audit)
  - Public/Auth/Account routes (`Auth`, `Providers`, `HowItWorks`, `FAQ`, `Contact`, `Ethos`, `Contribute`, `Privacy`, `Dashboard empty`, `Profile` with Active Sessions, `Home search dropdown`, `Map selected`, `Scan delete error`)
- Existing desktop baselines (`1280×800`) MUST pass `task frontend:snapshot -- --check --filter desktop` with zero unintended diffs using the locked Chromium build and matching fonts.
