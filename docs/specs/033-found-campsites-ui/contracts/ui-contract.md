# UI & Accessibility Contract: Found Campsites & Scan Detail

**Feature**: `033-found-campsites-ui`
**Date**: 2026-11-22

Because this feature is strictly frontend-only (`FR-018`), no HTTP endpoints or OpenAPI schemas change. This contract defines the component boundaries, user-facing interaction invariants, and accessibility semantics relied upon by automated tests and visual snapshots.

## 1. Component Interfaces

### `FoundCampsites` (`src/frontend/components/FoundCampsites.tsx`)

```ts
export interface FoundCampsitesProps {
  scan: ScanDetailResponse;
}
```

- Preserves the existing default named export and prop signature consumed by `src/frontend/pages/ScanDetail.tsx`.
- Maintains `<section id="results" aria-labelledby="found-campsites-heading">` so `#results` notification links scroll cleanly into view.
- Internally coordinates:
  - `AvailabilityCalendar` (`src/frontend/components/found-campsites/AvailabilityCalendar.tsx`)
  - `CampsiteCardList` (`src/frontend/components/found-campsites/CampsiteCardList.tsx`)
  - `AvailabilityGrid` (`src/frontend/components/found-campsites/AvailabilityGrid.tsx`)

### `CoverageSummary` (`src/frontend/components/found-campsites/CoverageSummary.tsx`)

```ts
export interface CoverageSummaryProps {
  scan: ScanDetailResponse;
}
```

- Rendered by `ScanDetail.tsx` only when `scan.destination_type === "recreation_area"`.
- Preserves `<section aria-label="Campground coverage">` landmark.
- Displays coverage mode (`All campgrounds` / `Selected campgrounds`), eligible/unavailable and checked/pending/failed counts, partial-coverage warning whenever `coverage_status !== "complete"`, and an expandable per-campground breakdown using human-readable relative timestamps (`formatRelativeTime`) rather than raw ISO strings.

## 2. Accessibility & Interactive Semantics

| Control / Region       | Role / Accessible Name                                                                                                                                                              | Behavior Contract                                                                                                                                  |
| ---------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------- |
| Results section        | `region` named `"Found campsites"` (`id="results"`)                                                                                                                                 | Scroll target for `#results` hash links.                                                                                                           |
| Summary status         | `role="status"`                                                                                                                                                                     | Live count of unique matching sites and qualifying stays/openings (e.g., `"3 sites · 4 openings"`), updating on search or date filter.             |
| Search input           | `searchbox` named `"Search found campsites"`                                                                                                                                        | Searches across all pages by campground name, campsite name, campsite ID, and campsite type; resets pagination to page 1.                          |
| Sort select            | `combobox` named `"Sort campsites"`                                                                                                                                                 | Options: `soonest` (`Soonest opening`), `longest` (`Longest stay`), `most_nights` (`Most available nights`), `name` (`Site name`).                 |
| View switcher          | `group` / `radiogroup` named `"Results view"` with buttons `"Cards"` and `"Grid"` (`aria-pressed` or `aria-checked`)                                                                | Switches between Cards view and Grid view while preserving search, sort, and date filter state.                                                    |
| Calendar navigation    | Buttons `"Previous month"` and `"Next month"`                                                                                                                                       | Bounded to scan's `[start_date, end_date]` month span; disabled at boundaries.                                                                     |
| Calendar day buttons   | `<button>` per selectable day with descriptive `aria-label` (e.g., `"Thu, Jul 1, 2027 — 3 sites available"` or `"Fri, Jul 2, 2027 — no openings"`) and `aria-pressed` when selected | Single click selects night; second click forms normalized check-in → check-out range; clicking selected single night clears.                       |
| Clear date filter      | Button `"Clear dates"` (when date filter active)                                                                                                                                    | Resets `dateSelection` to `null` and restores full list.                                                                                           |
| Stay chip expansion    | Button `"+N more stays"` / `"Show fewer stays"` on cards with >4 stays                                                                                                              | Expands/collapses remaining stays inline per campsite card without affecting other cards.                                                          |
| Provider booking link  | `<a>` with `target="_blank" rel="noopener noreferrer"` and `aria-label="View <name> on provider website"` (plus `(<campground>)` when campground name is present)                   | Rendered only when `booking_url` is non-empty; comfortable touch target (`min-h-9` / button styling).                                              |
| Grid window navigation | Buttons `"Previous dates"` and `"Next dates"`                                                                                                                                       | Steps the 14-day grid window cleanly within `[scan.start_date, scan.end_date)`.                                                                    |
| Grid available cell    | `<button>` with `aria-label` identifying site, night date, and full stay range (`aria-pressed` when inspected)                                                                      | Activates inline stay inspector panel showing full stay details, capabilities, and provider booking CTA; dismissible via close button or `Escape`. |
| Pagination nav         | `<nav aria-label="Campsite pages">` with `"Previous campsites"` and `"Next campsites"` buttons and range status (`"1–10 of 12 sites"`)                                              | Shown whenever matching sites exceed `SITES_PER_PAGE` (10); clamps automatically if live refresh shrinks results.                                  |

## 3. Lifecycle, Empty & Error State Contract

| Condition                                                                                                                  | Expected UI                                                                                                                                                 |
| -------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `results` has no qualifying stays AND `last_checked_at === null`                                                           | Waiting state: `"Waiting for the first check"` + active/paused helper text.                                                                                 |
| `results` has no qualifying stays AND `last_checked_at !== null` AND recreation area with `coverage_status !== "complete"` | Distinct partial-coverage empty message explaining checked campgrounds have no openings yet while unchecked/failed campgrounds may still have availability. |
| `results` has no qualifying stays AND `last_checked_at !== null` AND paused (`!is_active`)                                 | Checked empty state noting scan is paused and can be resumed from the dashboard.                                                                            |
| `results` has no qualifying stays AND `last_checked_at !== null` AND active                                                | Checked empty state noting Camply will notify when new openings match.                                                                                      |
| Qualifying stays exist, but active search and/or calendar date filter matches 0 sites                                      | Filter-empty state distinguishing search vs. date filter mismatch, with a one-click `"Clear filters"` / `"Clear search"` / `"Clear dates"` action.          |
| `!is_active` AND qualifying stays exist                                                                                    | Single clear paused notice stating availability is not being refreshed while showing cached snapshot.                                                       |
| Refresh error occurs while cached `scan` data is loaded                                                                    | Error alert (`role="alert"`) with `"Try again"` button while keeping cached results visible.                                                                |
| Destination catalog request (`getCampground` / `getRecreationArea`) fails                                                  | Header omits external destination link gracefully; Found Campsites remains fully interactive.                                                               |

## 4. Layout & Viewport Invariants

- Zero horizontal document overflow (`document.documentElement.scrollWidth <= window.innerWidth`) across desktop (`1280×800`) and mobile (`375×812`, `390×844`) viewports in both Cards and Grid views.
- Single concise booking-confirmation disclaimer rendered once in `FoundCampsites` (no duplicate disclaimer between header and footer).
- Zero duplicate `Scan overview` card on `ScanDetail`; scan status, dates, criteria, freshness, and creation time appear once in the cohesive header.
