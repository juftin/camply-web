# Data Model: Rework Found Campsites UI

**Feature**: `20261122-140251-found-campsites-ui`
**Date**: 2026-11-22

All data models are **client-side view models** derived deterministically from the existing `ScanDetailResponse` (`src/frontend/lib/structs.ts`). No backend database models, migrations, or API schemas are modified.

## Core Derived Entities (`src/frontend/lib/availability.ts`)

### 1. `AvailableStay`

Represents a maximal contiguous block of occupied nights for a single campsite that satisfies `scan.min_stay_length`.

| Field    | Type                    | Description / Invariants                                                                       |
| -------- | ----------------------- | ---------------------------------------------------------------------------------------------- |
| `start`  | `string` (`YYYY-MM-DD`) | Inclusive check-in date (first occupied night).                                                |
| `end`    | `string` (`YYYY-MM-DD`) | Exclusive check-out date (`addDays(lastOccupiedNight, 1)`). Always `> start`.                  |
| `nights` | `number`                | Number of consecutive occupied nights (`>= scan.min_stay_length`).                             |
| `dates`  | `string[]`              | Sorted, deduplicated ISO strings of occupied nights in `[start, end)`. Length equals `nights`. |

### 2. `NormalizedFoundSite`

Represents one unique campsite in the scan's results after deduplication and qualifying-stay derivation.

| Field                  | Type                  | Description / Invariants                                                                                                     |
| ---------------------- | --------------------- | ---------------------------------------------------------------------------------------------------------------------------- |
| `key`                  | `string`              | Unique composite identity `${providerId}:${campgroundId}:${campsiteId}`. Never merges sites across campgrounds or providers. |
| `providerId`           | `number`              | Provider identifier (`item.provider_id ?? 0`).                                                                               |
| `campgroundId`         | `string`              | Campground identifier (`item.campground_id ?? ""`).                                                                          |
| `campgroundName`       | `string`              | Optional campground display label (used when multiple campgrounds or recreation-area scan).                                  |
| `campsiteId`           | `string`              | Provider-local campsite ID.                                                                                                  |
| `displayName`          | `string`              | `item.campsite_name.trim()                                                                                                   |     | "Campsite ${item.campsite_id}"`. |
| `campsiteType`         | `string \| null`      | Standardized site type when known.                                                                                           |
| `isElectric`           | `boolean \| null`     | Electric hookup capability when known.                                                                                       |
| `isAccessible`         | `boolean \| null`     | ADA accessibility when known.                                                                                                |
| `maxVehicleLength`     | `number \| null`      | Maximum compatible vehicle length in feet when known.                                                                        |
| `permittedEquipment`   | `string[]`            | Normalized permitted equipment labels (empty array when unknown).                                                            |
| `bookingUrl`           | `string`              | Provider destination URL (empty string when absent).                                                                         |
| `lastCheckedAt`        | `string \| null`      | Per-campground last check timestamp when provided.                                                                           |
| `isStale`              | `boolean`             | `true` when retained from a failed campground check.                                                                         |
| `stays`                | `AvailableStay[]`     | Sorted chronologically by `start`. Always non-empty (`stays.length >= 1`); sites with zero qualifying stays are excluded.    |
| `availableNightSet`    | `ReadonlySet<string>` | Fast lookup of every occupied night belonging to a qualifying stay on this site.                                             |
| `soonestCheckIn`       | `string`              | `stays[0].start`.                                                                                                            |
| `longestStayNights`    | `number`              | `max(stay.nights)` across `stays`.                                                                                           |
| `totalAvailableNights` | `number`              | Sum of `stay.nights` across `stays`.                                                                                         |
| `searchText`           | `string`              | Precomputed lowercase search haystack combining `campgroundName`, `displayName`, `campsiteId`, and `campsiteType`.           |

### 3. `DateSelection`

Represents the user's active filter selection on the interactive availability calendar.

```ts
export type DateSelection =
  | null
  | { start: string; end: null } // Single occupied night filter
  | { start: string; end: string }; // Exclusive check-out range [start, end), start < end
```

**State transitions (`applyCalendarDayClick`)**:

| Prior State               | User Action                                              | Next State                                       |
| ------------------------- | -------------------------------------------------------- | ------------------------------------------------ |
| `null`                    | Click in-window night `D` (`start_date <= D < end_date`) | `{ start: D, end: null }`                        |
| `{ start: S, end: null }` | Click `S` again                                          | `null` (clears filter)                           |
| `{ start: S, end: null }` | Click `D > S` (`D <= end_date`)                          | `{ start: S, end: D }`                           |
| `{ start: S, end: null }` | Click `D < S` (`D >= start_date`)                        | `{ start: D, end: S }` (auto-normalized)         |
| `{ start: S, end: E }`    | Click in-window night `D` (`start_date <= D < end_date`) | `{ start: D, end: null }` (starts new selection) |
| Any active state          | Click "Clear dates"                                      | `null`                                           |

**Matching predicate (`stayMatchesSelection`)**:

- `selection === null`: matches all qualifying stays.
- `selection.end === null`: matches iff `stay.start <= selection.start && selection.start < stay.end`.
- `selection.end !== null`: matches iff `stay.start <= selection.start && stay.end >= selection.end` (one continuous stay covers every night in `[start, end)`).

### 4. `CalendarDayCell` & `CalendarMonth`

Derived for the currently displayed `(year, month)` from the scan window and the current **search-filtered** qualifying sites (so searching by campsite name, type, or campground immediately updates per-night opening counts on the calendar).

| Field                | Type                    | Description                                                                          |
| -------------------- | ----------------------- | ------------------------------------------------------------------------------------ |
| `date`               | `string` (`YYYY-MM-DD`) | Calendar day ISO string.                                                             |
| `dayNumber`          | `number`                | Day of month (`1..31`).                                                              |
| `isCurrentMonth`     | `boolean`               | Whether the cell belongs to the displayed month.                                     |
| `isInScanWindow`     | `boolean`               | `scan.start_date <= date && date < scan.end_date` (occupied night in scan window).   |
| `isCheckoutBoundary` | `boolean`               | `date === scan.end_date` (selectable only when choosing the second date of a range). |
| `isWeekendNight`     | `boolean`               | Friday (`5`) or Saturday (`6`) occupied night.                                       |
| `availableSiteCount` | `number`                | Number of distinct `NormalizedFoundSite` entries with `availableNightSet.has(date)`. |
| `isSelectable`       | `boolean`               | `isCurrentMonth && (isInScanWindow                                                   |     | (isCheckoutBoundary && selection?.end === null))`. |

**Default initial month**:

- Month of the soonest `AvailableStay.start` across all qualifying sites; falls back to the month of `scan.start_date` if there are no qualifying openings.
- Month navigation is clamped to `[monthOf(scan.start_date), monthOf(scan.end_date)]`.

### 5. `FoundViewMode` & `FoundSortMode`

```ts
export type FoundViewMode = "cards" | "grid";
export type FoundSortMode = "soonest" | "longest" | "most_nights" | "name";
```

**Sorting semantics (`filterAndSortSites`)**:

- When `dateSelection` is active, `soonest` (earliest check-in ascending) and `longest` (longest stay descending) evaluate each campsite's **matching** stay(s); when `dateSelection === null`, they evaluate all qualifying stays on the campsite.
- `most_nights` sorts by `totalAvailableNights` descending; `name` sorts by campground name (when multi-campground), then case-insensitive `displayName`, then `campsiteId`.

### 6. `GridWindow` & `SelectedGridStay`

- `GridWindow`: `{ dates: string[]; startDate: string; endDate: string; canPrev: boolean; canNext: boolean }` representing up to `14` consecutive occupied nights inside `[scan.start_date, scan.end_date)`.
- `SelectedGridStay`: `{ siteKey: string; stayStart: string; stayEnd: string } | null` identifying the currently inspected qualifying stay in Grid view. Cleared automatically if the referenced site or stay disappears after a filter change or live refresh.

### 7. `CoverageMember` (existing `ScanDetailResponse["campgrounds"]`)

Consumed directly by `CoverageSummary.tsx` without schema changes:

- Groups summary counts from `scan.eligible_campground_count`, `scan.checked_campground_count`, `scan.pending_campground_count`, `scan.failed_campground_count`, `scan.unavailable_selection_count`, and `scan.coverage_status`.
- Renders each member's `campground_name`, `eligible`, `outcome`, `unavailable_reason`, and human-readable `formatRelativeTime(member.last_checked_at)`.
