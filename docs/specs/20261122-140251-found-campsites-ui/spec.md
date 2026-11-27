# Feature Specification: Rework Found Campsites UI

**Feature Branch**: `roasted-bird`

**Created**: 2026-11-22

**Status**: Draft

**Input**: User description: "Let's write a spec to re-work the found campsites UI. I don't find it super intuitive. The UI/UX should be pleasant and easy for users. Let's think deeply before deciding what to implement. Ask questions as needed." Clarified scope: interactive calendar/date overview paired with deduplicated campsite cards as the primary browsing model, a view switcher (Cards and Availability Grid), cohesive scan detail page and recreation-area coverage cleanup, and frontend-only changes using existing scan detail data.

## User Scenarios & Testing _(mandatory)_

### User Story 1 - Explore openings visually with an interactive availability calendar (Priority: P1)

As a camper checking a saved scan, I want to see at a glance on an interactive calendar which dates have qualifying campsite openings and filter results by clicking a night or stay window, so I can immediately tell when I can go without digging through dozens of collapsed date-range accordions.

**Why this priority**: Campers plan trips around dates and weekends first. Grouping results strictly by exact check-in/check-out pairs fragments overlapping openings across many collapsed sections and hides overall availability patterns.

**Independent Test**: Load a scan spanning multiple weeks with overlapping openings across several campsites (including weekend and weekday stays). Verify that the calendar opens on the month of the soonest qualifying opening, highlights dates with openings and their counts, filters matching sites when a single night or a check-in/check-out date range is selected, and restores all sites when cleared.

**Acceptance Scenarios**:

1. **Given** a scan with qualifying openings across multiple dates, **When** I open the scan detail page, **Then** an interactive calendar displays the month of the soonest qualifying opening, clearly distinguishing days inside the scan window with openings (including available site counts), days inside the scan window with no openings, weekends, and days outside the scan window.
2. **Given** a scan whose date window spans multiple months, **When** I navigate between months in the calendar, **Then** navigation stays bounded to the months overlapping the scan's date window and accurately reflects opening indicators for each displayed month.
3. **Given** Site A is open Jul 1–3, Site B is open Jul 1–5, and Site C is open Jul 2–4, **When** I select the single night Jul 2 on the calendar, **Then** the filtered results show Sites A, B, and C (all sites with a qualifying stay covering Jul 2) and display an active date filter indicator with a one-click clear action.
4. **Given** the same overlapping openings, **When** I select a check-in date of Jul 2 and a check-out date of Jul 4 (2 nights: Jul 2 and Jul 3), **Then** the filtered results show only Sites B and C (sites with a single continuous qualifying stay covering every night in that window) and exclude Site A.
5. **Given** an active date or date-range filter, **When** I click the clear action (or deselect the active date), **Then** the full set of qualifying sites and updated result counts are restored immediately.

---

### User Story 2 - Browse scannable, deduplicated campsite cards (Priority: P1)

As a camper comparing available options, I want each matching campsite to appear once as a clean, scannable card showing its campground, site capabilities, qualifying stays, and a prominent booking action, so I can quickly evaluate suitability and jump to book.

**Why this priority**: In the current layout, a campsite with multiple open weekends is repeated across separate accordions, attributes run together as muted text, and micro-pagination (five sites per accordion) creates unnecessary friction before booking.

**Independent Test**: Load a scan containing multiple campsites (including a site with multiple separate stay windows, a site with rich attributes, an unnamed site, and a stale observation from a recreation-area scan). Verify each distinct campsite appears once, displays readable attribute badges and check-in/check-out stay chips, supports full-result search and sorting, paginates smoothly for large lists, and provides an accessible external booking action.

**Acceptance Scenarios**:

1. **Given** a campsite with three distinct qualifying stay ranges (e.g., Jul 1–3, Jul 8–10, Jul 15–18), **When** I view the default Cards view, **Then** that campsite appears once with all of its qualifying stays listed clearly as check-in → check-out ranges with night counts, rather than duplicating the campsite across separate sections.
2. **Given** a campsite with known attributes (site type, electric hookup, accessibility, maximum vehicle length, permitted equipment), **When** I inspect its card, **Then** each known attribute renders as a clearly structured, scannable visual indicator, while unknown attributes are omitted without placeholder clutter.
3. **Given** a campsite with many distinct qualifying stay ranges (more than four), **When** I view its card, **Then** the card remains compact by showing the primary stays upfront with an inline control to expand and view the remaining stays for that campsite.
4. **Given** an active date or range filter from the calendar, **When** I view matching campsite cards, **Then** each matching card visually emphasizes the stay range(s) that satisfy the active date selection.
5. **Given** a scan with many qualifying sites, **When** I search by campsite name, campsite number, campsite type, or campground name, or change the sort order (soonest opening, longest stay, most available nights, or site name), **Then** search and sort evaluate the entire qualifying result set across all pages, update the unique site count and stay summary accurately, and reset to the first page.
6. **Given** a campsite with a provider booking link, **When** I activate its booking action, **Then** it opens the provider destination in a new tab with an accessible label identifying both the campsite and (when present) its campground.

---

### User Story 3 - Switch between Cards and Availability Grid views (Priority: P2)

As a camper scanning availability across many campsites or comparing dates side by side, I want a view switcher to toggle between the default Cards view and a Sites × Dates Availability Grid view, so I can inspect night-by-night availability patterns visually and still jump straight to booking.

**Why this priority**: Different users and trip scenarios benefit from different mental models: Cards + Calendar excels for quick detail scanning and mobile use, while a Sites × Dates matrix excels at spotting multi-night blocks and comparing sites across dates simultaneously.

**Independent Test**: On a scan with multiple campsites spanning two or more weeks, switch from Cards view to Availability Grid view and back. Verify the grid displays campsites as rows and consecutive dates as columns, clearly marks available nights versus unavailable nights, lets users inspect an available stay and reach the booking link, preserves active search/sort/date filters across view switches, and stays usable on narrow viewports.

**Acceptance Scenarios**:

1. **Given** a scan with qualifying results, **When** I switch the view control from Cards to Grid, **Then** the results render as a matrix with matching campsites as rows (keeping campsite name and campground attribution visible) and consecutive dates as columns with weekend visual cues and distinct styling for available nights.
2. **Given** I am in Grid view on a scan spanning more than a single grid window, **When** I move forward or backward through dates (or switch to Grid view with an active calendar date selection), **Then** the grid aligns cleanly to the requested dates without losing my search query, sort order, or view selection.
3. **Given** I see an available night cell in Grid view, **When** I click or activate that cell, **Then** I can view the complete qualifying stay details (check-in → check-out, night count, site capabilities) and activate the provider booking link directly.
4. **Given** I have entered a search query or date selection and switched to Grid view, **When** I switch back to Cards view or a background availability refresh completes, **Then** my view selection, search text, sort order, and active date filter remain intact.
5. **Given** I am viewing Grid view on a narrow mobile screen, **When** I scroll horizontally across dates, **Then** the campsite identity column stays visible for context and switching back to Cards view remains a single tap away.

---

### User Story 4 - Navigate a cohesive scan detail header and recreation-area coverage summary (Priority: P2)

As a camper managing a campground or recreation-area scan, I want the scan detail page header, saved criteria, freshness, and recreation-area coverage status to be cleanly organized without duplicated overview blocks or raw status text, so the page feels calm, trustworthy, and immediately leads me to available campsites.

**Why this priority**: Even a polished results panel feels cluttered when surrounded by repeated summary blocks, raw unformatted campground status lines, and duplicate disclaimers. Cleaning up the surrounding scan detail layout makes the entire destination experience coherent.

**Independent Test**: Open both a single-campground scan and a recreation-area scan (with mixed checked, pending, failed, and unavailable campgrounds, plus stale results). Verify the page presents scan identity, status, saved criteria, last-checked freshness, provider link, and edit action once without redundant overview cards; renders recreation-area coverage in a structured summary with expandable per-campground status and human-readable timestamps; and handles empty, paused, error, and notification-anchor states cleanly.

**Acceptance Scenarios**:

1. **Given** a single-campground scan, **When** I open the scan detail page, **Then** the header cleanly presents the destination name, parent recreation area (if any), external provider link (when available), active/paused/ended status, last-checked freshness, saved scan criteria (date window, minimum stay, allowed nights, site preferences), and edit action without duplicating the same criteria and status in a second overview card below the results.
2. **Given** a recreation-area scan with eligible, checked, pending, failed, and unavailable campgrounds, **When** I open the scan detail page, **Then** coverage appears as a compact, readable summary (highlighting partial or failed coverage clearly when incomplete) with an expandable per-campground breakdown showing each campground's status and human-readable relative last-checked time rather than raw ISO timestamps or unstyled paragraphs.
3. **Given** a recreation-area scan with matching results from two campgrounds where one campground's latest check failed, **When** I view the results, **Then** retained results from the failed campground remain visible with a clear stale-observation badge, while fresh results from healthy campgrounds remain unmarked.
4. **Given** a scan with no matching results, **When** I view the page, **Then** the empty state clearly distinguishes between waiting for the first check, an active scan with no current matches, a paused scan with instructions to resume, a partial-coverage area scan where unchecked/failed campgrounds may still have openings, and a filter/search mismatch with a one-click reset action.
5. **Given** a user follows a notification link pointing to the results anchor, **When** the scan detail page loads, **Then** the view scrolls smoothly to the Found Campsites section.

---

### Edge Cases

- **Overlapping stays and minimum stay rules**: Nights never combine across different campsites or different campgrounds. Only maximal consecutive stays meeting the scan's saved minimum stay length appear in the calendar counts, cards, and grid. When a user selects a check-in → check-out range on the calendar, a campsite matches only if a single continuous qualifying stay covers every night in `[check-in, check-out)`.
- **Calendar selection edge cases**: Selecting a second date earlier than the first date automatically normalizes the range so the earlier date is check-in and the later date is check-out. Clicking dates outside the scan's date range is disabled. Selecting a date or range that has zero openings either cannot produce a broken state or shows a clear "No sites available for the selected dates" message with a one-click clear button.
- **Scans spanning year boundaries or long windows**: Stay chips include the year whenever a stay crosses New Year's Day (or when the scan spans multiple years). Long scans (e.g., 3–6 months) keep calendar navigation and Grid view bounded and responsive without overwhelming horizontal scroll widths.
- **Identical campsite identifiers across campgrounds**: Two campgrounds in a recreation-area scan that both contain a campsite with local ID `001` count as two distinct sites, render as two distinct cards/rows with their respective campground labels, and never merge their available dates.
- **Live refresh resilience**: When background availability data refreshes, current view mode, search text, sort choice, calendar month, and selected dates are preserved. If refreshed results shrink below the current page, pagination clamps cleanly to the last valid page; if a refresh fails while cached data is loaded, cached results remain visible alongside a retry alert.
- **Paused scans with cached results**: A paused scan with previously observed results continues to display them alongside a single clear notice that availability is no longer being refreshed.
- **Missing optional metadata**: Unnamed campsites fall back cleanly to `Campsite <id>`. Unknown attributes (site type, electric, accessibility, vehicle length, permitted equipment) are omitted gracefully. Sites without a booking URL omit the booking button. If destination catalog metadata fails to load for the header's external campground/area link, the rest of the scan detail and results remain fully usable.
- **Single-concise disclaimer**: A single clear notice reminding campers to verify live availability, stay rules, and vehicle restrictions with the booking provider appears once in the results area rather than repeating in both header and footer.

## Requirements _(mandatory)_

### Functional Requirements

- **FR-001**: The Found Campsites experience MUST display an interactive availability calendar scoped to the scan's saved date window whenever qualifying openings exist, visually distinguishing in-window nights with qualifying openings (with site count indicators), in-window nights without openings, weekend nights, and dates outside the scan window.
- **FR-002**: When rendered, the interactive calendar MUST default to displaying the month of the soonest qualifying opening (with its month-anchor calculation falling back gracefully to the scan's start month when no openings exist) and allow month-by-month navigation bounded to the scan's date window.
- **FR-003**: Users MUST be able to select either a single night (filtering to campsites with a qualifying stay covering that night) or a check-in → check-out date range (filtering to campsites with a single continuous qualifying stay covering every night in the selected range), see the active date filter clearly summarized, and clear the date filter in one click.
- **FR-004**: The default Cards view MUST deduplicate campsites by `(provider, campground, campsite)` identity so each qualifying campsite appears at most once per filtered list, displaying its name (with fallback when unnamed), campground attribution for multi-campground scans, stale-observation status when retained from a failed check, structured attribute badges for known capabilities (type, electric hookup, accessibility, max vehicle length, permitted equipment), qualifying stay chips formatted as check-in → check-out with night counts, and a prominent external booking action when a booking URL is present.
- **FR-005**: When a campsite has more than four distinct qualifying stay ranges, its card MUST display a bounded initial set of stays (prioritizing stays matching any active date filter, then soonest) with an inline expand/collapse control to reveal the remaining stays.
- **FR-006**: When a calendar date or date-range filter is active in Cards view, matching stay chips on each visible campsite card MUST be visually highlighted so users immediately see why the campsite matched.
- **FR-007**: The results panel MUST provide a clean, uncluttered toolbar containing full-result text search (matching campsite name, campsite ID, campsite type, and campground name), sort selection (soonest opening, longest stay, most available nights, and site name), and a view switcher toggling between **Cards** view and **Grid** view.
- **FR-008**: The Grid view MUST present matching campsites as rows and consecutive calendar dates as columns, visually indicating qualifying available nights and weekends, supporting date-window navigation, keeping campsite identity visible during horizontal scroll on narrow screens, and allowing users to inspect any available stay and activate its provider booking link.
- **FR-009**: Results MUST preserve accurate qualifying stay evaluation: only consecutive night blocks meeting or exceeding the scan's saved minimum stay length may appear in calendar indicators, cards, grid cells, and summary counts; nights MUST NEVER combine across distinct campsites or campgrounds.
- **FR-010**: The results summary MUST display accurate, live-updating counts of unique matching campsites and qualifying stays/openings reflecting active search and date filters.
- **FR-011**: Large campsite lists MUST be bounded with clean pagination controls that remain valid when results shrink after a background refresh and reset to the first page whenever search, sort, or date filter changes.
- **FR-012**: Background availability refreshes MUST preserve the user's selected view mode, search query, sort order, displayed calendar month, and active date filter without jarring resets. If a refresh fails while cached data exists, cached results MUST remain visible with an actionable retry prompt.
- **FR-013**: The Scan Detail page MUST present destination identity, provider link (when available), active/paused/ended status, last-checked freshness, saved scan criteria (date range, minimum stay, allowed nights, site preferences), and edit action in one cohesive header structure, eliminating redundant duplicate overview cards and duplicate provider-disclaimer paragraphs.
- **FR-014**: For recreation-area scans, the Scan Detail page MUST render campground coverage in a structured summary showing eligible, checked, pending, failed, and unavailable counts, with a clear partial-coverage notice when incomplete and an expandable per-campground breakdown using human-readable relative timestamps and status indicators.
- **FR-015**: The Scan Detail and Found Campsites views MUST present distinct, helpful empty and status states for: waiting on first check, active scan with no current matches, paused scan (both empty and with cached results), partial recreation-area coverage with no current matches, and empty search/date-filter results with a one-click clear action.
- **FR-016**: Notification deep-links targeting the results anchor MUST scroll smoothly to the Found Campsites section.
- **FR-017**: All interactive elements—including calendar day selection, month navigation, view switcher, grid stay inspection, pagination, coverage expansion, and booking links—MUST support full keyboard navigation, screen-reader accessibility, light and dark themes, and responsive desktop and mobile layouts.
- **FR-018**: All changes MUST rely solely on the scan detail, availability, coverage, and destination information already provided to the page without introducing new server-side data collection or background monitoring behavior.

### Key Entities

- **Qualifying Stay**: A maximal contiguous block of available occupied nights for a single campsite that meets or exceeds the scan's saved minimum stay length, represented to users as an inclusive check-in date, an exclusive check-out date, and a night count.
- **Found Campsite**: A unique campsite identified by provider, campground, and campsite identifier, carrying optional capability metadata (type, electric hookup, accessibility, max vehicle length, permitted equipment), optional campground label and staleness flag, optional booking destination, and one or more Qualifying Stays.
- **Calendar Day Availability**: A single calendar night within the scan's date window summarizing how many distinct Found Campsites have a Qualifying Stay covering that night.
- **Coverage Member** (recreation-area scans): A campground tracked by a recreation-area scan with eligibility state, check outcome (checked, pending, failed, unavailable), and last successful check timestamp.

## Success Criteria _(mandatory)_

### Measurable Outcomes

- **SC-001**: A camper opening a scan with openings spanning multiple overlapping date ranges can determine which nights and weekends have availability within 3 seconds from the calendar overview without expanding any accordions.
- **SC-002**: A camper looking for a specific night or multi-night stay can narrow results to continuously available campsites in at most 2 clicks on the calendar and clear the filter in 1 click.
- **SC-003**: Every qualifying campsite appears exactly once in the Cards view regardless of how many separate date ranges it is available, reducing visual duplication compared to exact-range grouping to zero.
- **SC-004**: Users can switch between Cards view and Availability Grid view and reach a provider booking action from either view in 1–2 interactions while preserving active search and date filters.
- **SC-005**: Scan criteria, freshness, and provider disclaimers each appear once in their primary location on the Scan Detail page (zero duplicated overview cards or repeated disclaimer blocks), and 100% of recreation-area coverage timestamps render in human-readable form.
- **SC-006**: All core browsing journeys (calendar filtering, card inspection, grid inspection, search, sort, pagination, and empty/error states) pass automated verification and visual inspection across desktop and mobile viewports in both light and dark themes with zero accessibility regressions.

## Assumptions

- **Existing availability data**: The existing scan detail view already receives availability filtered for non-past nights, scan window, allowed weekdays, and saved preferences, along with campsite capabilities, provider booking links, per-site staleness, and recreation-area member statuses. No changes to monitoring or stored data are needed.
- **Check-in / check-out range semantics**: Selecting two dates on the calendar follows standard lodging and camping conventions where the first date is check-in (first occupied night) and the second date is check-out (exclusive), matching the rest of Camply's scan creation and stay display.
- **Default view and session state**: Cards view (paired with the interactive calendar) is the default view on both desktop and mobile so first-time and mobile users immediately get a clean, readable layout; view switcher selection is retained for the active visit and across live refreshes without requiring server-side preference persistence.
- **Scope boundary**: Dashboard scan cards, scan creation/editing form workflows, admin scan detail tables, and provider booking URL deep-linking remain unchanged and out of scope for this feature.
