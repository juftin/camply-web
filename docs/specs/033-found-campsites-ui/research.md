# Research: Rework Found Campsites UI

**Feature**: `033-found-campsites-ui`
**Date**: 2026-11-22

## 1. Calendar Implementation Strategy

- **Decision**: Build a focused, zero-dependency interactive availability calendar (`AvailabilityCalendar.tsx`) using the existing date utilities in `src/frontend/lib/utils.ts` (`parseIsoDate`, `toIsoDateString`, `addDays`, `daysBetween`) and existing Tailwind CSS + Lucide icons, following the same calendar-cell generation pattern already established in `src/frontend/components/ui/date-picker.tsx`.
- **Rationale**:
  - `package.json` contains no third-party date/calendar library (e.g., `react-day-picker` or `date-fns`), and `DatePicker.tsx` already implements timezone-safe local ISO `YYYY-MM-DD` month grids with zero added bundle weight.
  - Custom day cells are required to render per-night opening counts, weekend-night cues (Friday/Saturday occupied nights), scan-window boundaries, hover range previews, and accessible button semantics without fighting third-party calendar markup or CSS overrides.
- **Alternatives considered**:
  - _Adding `react-day-picker`_: Adds a new frontend dependency and custom day-cell renderer boilerplate for a single feature that needs custom availability counts and range-boundary rules.
  - _Reusing `DatePicker.tsx` directly_: `DatePicker` is a single-date popover input for form fields (`ScanForm`), whereas Found Campsites needs an always-visible inline availability overview calendar with site counts and range filtering.

## 2. Date-Selection Semantics (Single Night vs. Check-in → Check-out Range)

- **Decision**: Support two-step progressive selection on the availability calendar:
  1. **Unselected (`null`)**: All qualifying sites across the scan window are shown; the calendar acts as a visual overview.
  2. **First click on an in-window occupied night (`{ start, end: null }`)**: Filters to campsites that have at least one qualifying consecutive stay containing that night (`stay.start <= start && start < stay.end`). Clicking the same date again clears the selection.
  3. **Second click on another date (`{ start, end }`)**: Normalizes order so `start < end`, and treats `[start, end)` as an exclusive check-out stay window (`Check-in → Check-out`). Filters to campsites that have a **single continuous qualifying stay** covering every night in `[start, end)` (`stay.start <= start && stay.end >= end`).
  4. **Third click when a range is already active**: Starts a new single-night selection at the clicked date.
  5. **Boundary handling for `scan.end_date`**: `scan.end_date` is the exclusive check-out boundary of the scan (not an occupied night). It is disabled as an initial single-night pick (since no occupied night exists on `end_date`), and enabled as a valid second-click check-out target once a start night is selected (so a user on a `Jul 1 – Jul 3` scan can click `Jul 1` then `Jul 3` to select the full 2-night stay).
- **Rationale**: Matches Camply's existing `ScanForm` check-in/check-out convention and standard lodging/camping calendars (Airbnb, Recreation.gov) while still letting campers click a single Friday or Saturday night in one click to see everything open that night.
- **Alternatives considered**:
  - _Inclusive night-to-night range_: Conflicts with Camply's existing `Check-in → Check-out` labels (`Jul 1 → Jul 3 · 2 nights`), causing off-by-one confusion between calendar selection and displayed stay chips.
  - _Exact check-in-only single click_: Misses campsites whose qualifying stay started one day earlier (e.g., open Thu–Sun when a user clicks Fri), recreating the fragmentation problem we are solving.

## 3. Weekend Night Visual Cues

- **Decision**: Visually highlight **Friday and Saturday occupied nights** (JavaScript `getDay() === 5 || 6`, matching `src/frontend/lib/weekdays.ts` Monday=0 indices `4` and `5` used by Camply's `Weekends` scan preset) with subtle weekend styling in both the Availability Calendar and Availability Grid column headers.
- **Rationale**: In camping availability, nights represent occupied sleeping nights; a standard weekend trip occupies Friday night and Saturday night (checking out Sunday morning). Aligning the calendar and grid cues with `ScanForm`'s `Weekends` preset keeps the entire app internally consistent.
- **Alternatives considered**:
  - _Highlighting Saturday and Sunday_: Misaligns with camping stay semantics where Sunday night is a weeknight requiring Monday off work.

## 4. Layout & Responsive Architecture (Cards View vs. Grid View)

- **Decision**:
  - Widen the `ScanDetail` container from `max-w-4xl` to `max-w-5xl` (matching `Dashboard.tsx`) to give both views comfortable horizontal breathing room.
  - **Cards View (default)**: On desktop (`lg` and up), place the `AvailabilityCalendar` in a sticky left column (`lg:grid-cols-[320px_minmax(0,1fr)]`) beside the deduplicated `CampsiteCardList` so clicking dates immediately filters cards with zero vertical scrolling. On mobile/tablet, stack the calendar cleanly above the site cards.
  - **Grid View**: Give the Sites × Dates matrix full card width (`overflow-x-auto` inner scroll container with a sticky left campsite column so `document.documentElement.scrollWidth <= window.innerWidth` is strictly preserved across all viewports). Display a bounded 14-day window (clamped to `[scan.start_date, scan.end_date)`) with Previous/Next window controls and automatic synchronization when a user has an active calendar date filter.
  - **Stay Inspection in Grid View**: Clicking/activating any available night cell opens a clean inline stay-inspector bar/panel anchored within the grid area (showing the campsite name, campground, full qualifying `Check-in → Check-out · N nights` range, capability badges, staleness notice if applicable, and a prominent `View on provider` booking button), avoiding clipped popovers inside `overflow-x-auto` containers and working identically via keyboard or touch.
- **Rationale**: Inline selection/inspection inside the grid avoids CSS overflow clipping issues common with floating popovers inside horizontally scrollable tables, remains accessible to screen readers and mobile users, and requires zero extra UI primitives.
- **Alternatives considered**:
  - _Floating Radix Popover per grid cell_: Requires installing `@radix-ui/react-popover` (not currently in `package.json`) and introduces positioning/viewport clipping quirks inside horizontally scrolling tables on 375px mobile viewports.
  - _Rendering all scan dates in one horizontal table (e.g., 180 columns)_: Degrades DOM performance and becomes unusable on 3–6 month scans.

## 5. Pagination & Deduplication Boundaries

- **Decision**:
  - Deduplicate `scan.results` by composite key `${site.provider_id ?? 0}:${site.campground_id ?? ""}:${site.campsite_id}` before computing maximal consecutive qualifying stays (`stay.nights >= scan.min_stay_length`), preserving distinct sites that share a local `campsite_id` across different campgrounds.
  - Paginate the deduplicated site list at `SITES_PER_PAGE = 10` in both Cards view and Grid view (replacing the old 5-sites-per-accordion micro-pagination).
  - Cap initially rendered stay chips per campsite card at `4` (prioritizing stays matching the active date selection, then soonest), with an inline `+N more stays` / `Show fewer` toggle per card.
- **Rationale**: Showing 10 deduplicated sites per page fits comfortably in a single viewport scan without nested pagination controls, keeps DOM size strictly bounded for 100+ site recreation-area scans, and satisfies the existing `manyCampsites` (12–13 sites) visual snapshot and pagination tests cleanly.
- **Alternatives considered**:
  - _Infinite scroll / virtual list_: Adds unnecessary complexity and breaks deterministic Playwright visual snapshot testing and keyboard pagination workflows.
  - _5 sites per page_: Too cramped when sites are already deduplicated to one card per site.

## 6. Scan Detail Consolidation & Existing Test/Snapshot Impact

- **Decision**:
  - Consolidate `ScanDetail.tsx` into a single cohesive header (destination name, parent recreation area, external provider link, status badges `Monitoring`/`Paused`/`Ended`, `Last checked`, `Created`, compact saved criteria pills, and `Edit Scan` button), followed by `<CoverageSummary />` (for recreation-area scans) and `<FoundCampsites />`. Remove the duplicate bottom `<details>Scan overview</details>` card and remove the second repeated provider disclaimer.
  - Keep the `<section aria-label="Campground coverage">` landmark and `<section id="results" aria-labelledby="found-campsites-heading">` landmark intact so accessibility landmarks, `#results` alert deep-links, and snapshot waits remain clean.
  - Update `src/frontend/components/FoundCampsites.test.tsx`, `src/frontend/pages/ScanDetail.test.tsx`, and the `scan-detail-*` / `area-scan-detail-*` scenarios + baselines in `src/frontend/tooling/run-snapshots.ts` (including adding coverage for Calendar date filtering and Grid view snapshots).
- **Rationale**: Eliminates all three layers of visual duplication identified in the spec while keeping existing URL routes, API hooks (`useScanDetail`, `getCampground`, `getRecreationArea`), and landmark roles intact.
- **Alternatives considered**:
  - _Keeping the bottom "Scan overview" accordion_: Directly violates FR-013 and SC-005 by duplicating scan status, dates, criteria, and freshness already presented in the header.
