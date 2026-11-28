# Route Audit Matrix & Responsive State Model

**Feature**: `20261126-182156-mobile-responsive-audit`
**Date**: 2026-11-26
**Spec**: [spec.md](spec.md)

Because this feature makes no backend or database schema changes, the domain model for this audit consists of the **Viewport Tier Matrix**, **26-Route Audit Inventory**, and **Interactive Mobile Component States**.

---

## 1. Viewport Tiers

| Tier                      | Dimensions   | Purpose                                                           | Overflow Policy       |
| :------------------------ | :----------- | :---------------------------------------------------------------- | :-------------------- |
| **Compact Phone (Short)** | `375 × 667`  | Dialog, sticky footer, and nested date-picker vertical fit        | `scrollWidth <= 375`  |
| **Compact Phone (Tall)**  | `375 × 812`  | Minimum primary full-page target width (graceful down to 360 px)  | `scrollWidth <= 375`  |
| **Standard Phone**        | `390 × 844`  | Baseline modern smartphone snapshot & visual target               | `scrollWidth <= 390`  |
| **Tablet Breakpoint**     | `768 × 1024` | `md:` breakpoint handoff (header nav, hybrid admin tables, grids) | `scrollWidth <= 768`  |
| **Desktop Guard**         | `1280 × 800` | Existing desktop baseline regression protection                   | Zero unintended diffs |

---

## 2. Complete 26-Route Audit Inventory

| #   | Route                                     | Group          | Current Mobile Baseline                                                                  | Target Mobile Visual Coverage                                                                                                                                                  | Key Mobile Risk Areas                                                                                          |
| :-- | :---------------------------------------- | :------------- | :--------------------------------------------------------------------------------------- | :----------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | :------------------------------------------------------------------------------------------------------------- |
| 1   | `/`                                       | Public / Core  | `home-mobile-light`                                                                      | Keep + add `home-search-dropdown-mobile-light` & `mobile-nav-drawer-mobile-dark`                                                                                               | Search dropdown width/truncation, hero CTA spacing, slide-over drawer                                          |
| 2   | `/search`                                 | Discovery      | `search-mobile-light`, `map-explore-*`, `map-collapsed-*`, `map-error-*`, `map-focus-*`  | Keep + add `map-selected-mobile-dark`                                                                                                                                          | Filter sidebar stacking, RV length grid, map popup/card bounds, pagination taps                                |
| 3   | `/providers`                              | Public         | None (desktop only)                                                                      | Add `providers-mobile-light`                                                                                                                                                   | Provider card grid, badge wrapping, external link tap targets                                                  |
| 4   | `/how-it-works`                           | Public         | None (desktop only)                                                                      | Add `how-it-works-mobile-dark`                                                                                                                                                 | Multi-column step/feature grids, heading scale, CTA spacing                                                    |
| 5   | `/faq`                                    | Public         | None (desktop only)                                                                      | Add `faq-mobile-light`                                                                                                                                                         | Accordion row tap targets, long question wrapping                                                              |
| 6   | `/contact`                                | Public         | None                                                                                     | Add `contact-mobile-light`                                                                                                                                                     | Stacked form inputs (`text-base`), info cards                                                                  |
| 7   | `/ethos`                                  | Public (gated) | None (desktop only)                                                                      | Add `ethos-mobile-light`                                                                                                                                                       | Long-form section spacing, typography scale                                                                    |
| 8   | `/contribute`                             | Public (gated) | None                                                                                     | Add `contribute-mobile-dark`                                                                                                                                                   | Multi-column card grids, button wrapping                                                                       |
| 9   | `/privacy`                                | Legal          | None                                                                                     | Overflow sweep + `privacy-mobile-light`                                                                                                                                        | Long links/prose wrapping, heading scale                                                                       |
| 10  | `/terms`                                  | Legal          | None                                                                                     | Overflow sweep (shared prose layout)                                                                                                                                           | Long links/prose wrapping                                                                                      |
| 11  | `/auth`                                   | Account        | None (desktop only)                                                                      | Add `auth-mobile-light`                                                                                                                                                        | Input auto-zoom prevention, card padding, submit tap target                                                    |
| 12  | `/invite-only`                            | Access         | `early-access-mobile-light`                                                              | Keep existing                                                                                                                                                                  | Email input zoom prevention, status callout wrapping                                                           |
| 13  | `/dashboard`                              | Camper         | `dashboard-mobile-light`, `dashboard-expanded-mobile-dark`, `area-dashboard-mobile-dark` | Keep + add `dashboard-empty-mobile-light`, `scan-form-dialog-mobile-light` (`375×667`), `scan-form-checkin-calendar-mobile-light` (`375×667`), `scan-delete-error-mobile-dark` | Stat grid, scan card action rows, pinned ScanForm dialog, clamped DatePicker                                   |
| 14  | `/dashboard/scans/:scanId`                | Camper         | `scan-detail-*`, `scan-detail-grid-*`, `scan-detail-paginated-*`, `area-scan-detail-*`   | Keep existing (recently reworked in found-campsites-ui)                                                                                                                        | Verify header pills, calendar, cards, and sticky grid column at 375 px                                         |
| 15  | `/profile`                                | Account        | `profile-ntfy-mobile-light`                                                              | Keep + add `profile-mobile-light` (Pushover + Active Sessions)                                                                                                                 | Long email/URL/topic/token wrapping, copy/test buttons, Active Sessions rows                                   |
| 16  | `/campground/:providerId/:campgroundId`   | Discovery      | `map-campground-*`, `enrichment-campground-*`, `enrichment-dialog-mobile-dark`           | Keep existing                                                                                                                                                                  | Long titles, provider badges, monitor CTA, carousel & photo viewer close target                                |
| 17  | `/rec-area/:providerId/:recreationAreaId` | Discovery      | `map-area-*`, `enrichment-area-*`, `area-picker-mobile-dark`                             | Keep existing                                                                                                                                                                  | Long titles, child campground rows, `AreaCoveragePicker` dialog                                                |
| 18  | `/admin`                                  | Admin          | `admin-overview-mobile-light`                                                            | Keep + add `admin-api-trends-table-mobile-dark`                                                                                                                                | KPI cards, Recharts axis/legend overlap, trend table horizontal scroll                                         |
| 19  | `/admin/users`                            | Admin          | `admin-reset-password-mobile-light`                                                      | Keep + add `admin-users-mobile-light`, `admin-create-user-password-mobile-dark`                                                                                                | **Hybrid stacked cards** (`<md`), filter bar wrapping, pinned Create/Reset dialogs + password reveal wrap      |
| 20  | `/admin/users/:userId`                    | Admin          | None (desktop only)                                                                      | Add `admin-user-detail-mobile-light`                                                                                                                                           | `grid-cols-1 sm:grid-cols-2`, UUID/email wrapping, action toggles, contained scans table                       |
| 21  | `/admin/invitations`                      | Admin          | None (desktop only)                                                                      | Add `admin-invitations-mobile-light`                                                                                                                                           | **Hybrid stacked cards** (`<md`), Approve/Revoke touch targets, filter tabs                                    |
| 22  | `/admin/scans`                            | Admin          | None (desktop only)                                                                      | Add `admin-scans-mobile-dark`                                                                                                                                                  | **Hybrid stacked cards** (`<md`), filter controls wrapping, pause/delete actions                               |
| 23  | `/admin/scans/:scanId`                    | Admin          | `admin-area-scan-detail-mobile-dark`                                                     | Keep + add `admin-scan-detail-mobile-light`                                                                                                                                    | Metadata grid stacking, contained results table                                                                |
| 24  | `/admin/targets/:targetId`                | Admin          | None (desktop only)                                                                      | Add `admin-target-detail-mobile-dark`                                                                                                                                          | Metadata grid stacking, UUID wrapping, contained subscribers/results tables                                    |
| 25  | `/admin/operations`                       | Admin          | `admin-operations-mobile-light`                                                          | Keep existing (re-verify after scroll/dialog fixes)                                                                                                                            | Metric cards, contained worker/task scroll tables (`min-w-[500px]`/`min-w-[950px]`), pinned task detail dialog |
| 26  | `/admin/audit`                            | Admin          | None (desktop only)                                                                      | Add `admin-audit-mobile-light`                                                                                                                                                 | Contained horizontal-scroll audit log table, filter controls, detail payload wrapping                          |

_(Utility route `/dev/preview` already has `dev-preview-mobile-light` and is verified alongside the 26 production routes.)_

---

## 3. Interactive Component State Models

### Mobile Navigation Drawer (`Header` + `Sheet`)

- **States**: `closed` (default) ↔ `open`
- **Transitions**:
  - Tap menu button → `open` (`aria-expanded="true"`, backdrop visible, focus trapped inside drawer, body scroll locked)
  - Tap any nav link / auth button → navigate + `closed`
  - Tap backdrop or close button → `closed` + focus returns to menu trigger
  - Press `Escape` → `closed` + focus returns to menu trigger
  - Route pathname change (`location.pathname`) → `closed` (safety guard)

### Viewport-Bounded Multi-Field Dialog (`DialogContent` + `DialogBody`)

- **Layout structure**:
  - Outer container: `fixed`, centered, `w-[calc(100vw-2rem)] sm:w-full`, `max-h-[calc(100dvh-2rem)]`, `flex flex-col overflow-hidden`
  - Pinned `DialogHeader`: `shrink-0` with `pr-10` clearance for the `44×44 px` close trigger
  - Scrollable `DialogBody`: `flex-1 overflow-y-auto min-h-0`
  - Pinned `DialogFooter`: `shrink-0 border-t` with `flex-col-reverse gap-2 sm:flex-row sm:justify-end`

### Admin Hybrid List Representation (`AdminUsers`, `AdminInvites`, `AdminScans`)

- **Viewport `< 768 px` (`md:hidden`)**: Vertical list of cards displaying primary identifier (email / destination), status badges, secondary metadata (dates, counts, role), and full-width or wrapped `≥44 px` action buttons.
- **Viewport `>= 768 px` (`hidden md:block`)**: Existing desktop `<table>` inside `overflow-x-auto` preserved unchanged.
