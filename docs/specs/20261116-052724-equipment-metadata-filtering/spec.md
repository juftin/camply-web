# Feature Specification: Equipment Metadata and Filtering

**Feature Branch**: `20261116-052724-equipment-metadata-filtering`
**Created**: 2026-11-16
**Status**: Draft
**Input**: User description: "Write a spec to implement equipment metadata and filtering (Phase 3.2: T3.2.1b discovery amenity/RV metadata population and T3.2.2 equipment length RV/Trailer and ADA/site-catalog filtering)"

## User Scenarios & Testing _(mandatory)_

### User Story 1 - Discover campgrounds by real amenities and RV capacity (Priority: P1)

A camper searching for a destination in Explore applies filters for electric hookups, pet-friendly campgrounds, ADA accessibility, or a minimum RV/trailer length. The catalog reflects actual amenities and maximum vehicle sizes supported by each campground's provider rather than blank defaults, so matching destinations appear accurately in both list and map views.

**Why this priority**: Explore already presents amenity and RV length controls to campers, but unpopulated provider metadata causes those filters to return empty or misleading results. Populating discovery metadata makes existing search controls immediately trustworthy and useful.

**Independent Test**: Run catalog metadata synchronization across synthetic provider catalogs containing electric, pet-friendly, water, sewer, ADA-accessible, and length-limited sites alongside sites lacking those attributes, then search Explore with each filter individually and in combination. Confirm only qualifying campgrounds and parent recreation areas appear, and non-qualifying or unknown destinations are excluded when a filter is active.

**Acceptance Scenarios**:

1. **Given** a provider catalog where Campground A has campsites with electric hookups, water, sewer, pets allowed, ADA accessibility, and a 40-foot maximum vehicle length, and Campground B has only non-electric tent sites with no pets and a 15-foot limit, **When** a camper filters Explore by electric hookups and a 30-foot minimum RV length, **Then** Campground A appears in results and Campground B is excluded.
2. **Given** a recreation area that contains at least one reservable campground supporting pets and a 25-foot trailer, **When** a camper views discovery results filtered by pets allowed and 25-foot RV length, **Then** the recreation area's aggregated capabilities reflect its eligible campgrounds accurately.
3. **Given** a provider whose catalog omits an optional facet (such as pet rules or sewer hookups), **When** discovery metadata is synced, **Then** unknown attributes default conservatively to not verified rather than fabricating support, while verified facets from the provider remain searchable.
4. **Given** a campground whose catalog updates in a subsequent sync (for example, adding electric sites or changing its maximum RV length), **When** the catalog refresh completes, **Then** Explore filters reflect the updated capabilities without stale attributes from deleted or disabled sites.

---

### User Story 2 - Filter saved scans and alerts by equipment type and vehicle length (Priority: P1)

A camper with an RV, trailer, camper van, or large tent creates or edits a saved scan and enters their required vehicle/equipment length (and optionally compatible equipment categories). Background availability checks and alert notifications only match campsites that can physically accommodate that equipment, preventing false-positive alerts for tent-only pads or short driveways.

**Why this priority**: Campers using trailers or motorhomes cannot book sites that are too short or prohibit their vehicle type. Receiving alerts for sites they cannot occupy erodes trust in real-time monitoring.

**Independent Test**: Create two saved scans targeting the same synthetic campground and dates—one requiring a 30-foot RV/trailer and one with no length restriction—and simulate availability across three sites: a 35-foot RV site, a 20-foot RV site, and a tent-only site with no length limit. Confirm both scans share one upstream check, the 30-foot scan matches and alerts only on the 35-foot site, and the unrestricted scan matches all three.

**Acceptance Scenarios**:

1. **Given** a scan form for a campground or recreation area, **When** a camper enters a vehicle/equipment length of 28 feet, **Then** the preference is validated, saved with the scan, and displayed on scan cards and scan detail pages.
2. **Given** an active saved scan requiring 28 feet of equipment length, **When** availability arrives with Site 1 allowing RVs/trailers up to 35 feet, Site 2 allowing RVs up to 24 feet, and Site 3 allowing tents only, **Then** only Site 1 appears in matching scan results, available-site counts, and outgoing notifications.
3. **Given** two subscribers watching the same campground and dates—one requiring 20 feet and one requiring 35 feet—**When** Site 1 (max 25 feet) becomes available, **Then** only the 20-foot subscriber receives a new-opening alert and sees a match, while the 35-foot subscriber receives nothing.
4. **Given** an existing saved scan with no equipment length specified, **When** a camper edits it to require 30 feet (or clears an existing length requirement back to unrestricted), **Then** matching results and pending notifications update against the new preference without losing scan identity, dates, or active status.

---

### User Story 3 - Filter saved scans by accessibility and inspect site capabilities (Priority: P2)

A camper who needs an ADA-accessible campsite enables an accessibility requirement on their saved scan, and campers inspecting matching sites on scan detail pages see accurate equipment and capability metadata (such as permitted equipment types, maximum length, electric hookups, and accessibility status).

**Why this priority**: Accessibility data is already partially captured by providers during availability checks, but campers cannot yet require it on saved scans or reliably inspect vehicle/equipment limits on matched results.

**Independent Test**: Save a scan with the accessibility requirement enabled for a synthetic campground containing one accessible site, one non-accessible site, and one site whose accessibility is unknown. Verify only the explicitly accessible site qualifies for results and notifications, and verify matched sites display their persisted capability details.

**Acceptance Scenarios**:

1. **Given** a scan with the ADA-accessible filter enabled, **When** availability includes an explicitly accessible site, a non-accessible site, and a site with unknown accessibility, **Then** only the explicitly accessible site qualifies for results, counts, and alerts.
2. **Given** a scan matching a site with known equipment limits (for example, "RV/Trailer up to 35 ft", electric hookup, accessible), **When** the camper opens the scan details, **Then** the matched site row displays those persisted capabilities clearly alongside booking links.
3. **Given** a recreation-area scan covering multiple campgrounds, **When** the camper sets an equipment length, equipment category, electric hookup, or accessibility filter, **Then** the filter is evaluated consistently across every covered campground in the area.

---

### User Story 4 - Preserve reliability across providers with differing catalog depth (Priority: P2)

Across all supported providers (Recreation.gov, UseDirect deployments, GoingToCamp deployments, and ReserveAmerica), catalog ingestion and availability polling extract verifiable equipment, length, electric, pet, water, sewer, and ADA attributes without breaking or delaying availability checks when a provider lacks a particular field.

**Why this priority**: Providers expose metadata unevenly—some supply full site catalogs in bulk, while others expose vehicle length or hookup details only on availability grids or facility details. Graceful degradation keeps monitoring reliable across all 26+ providers.

**Independent Test**: Run catalog sync and availability parsing against fixtures for each provider family (complete metadata, partial metadata, and unavailable optional detail fields). Confirm verified fields populate accurately, missing fields remain marked unknown rather than crashing or stalling scans, and unavailable optional endpoints never block availability matching.

**Acceptance Scenarios**:

1. **Given** a provider that supplies maximum vehicle length and permitted equipment on availability responses or site catalogs, **When** availability is persisted, **Then** the site's normalized equipment list, maximum vehicle length, electric flag, and accessibility flag are stored cleanly for filtering across all subscribers.
2. **Given** a site whose provider reports multiple equipment categories with different length limits (for example, Tent unlimited and Trailer up to 25 feet), **When** a camper filters for a 30-foot RV/trailer, **Then** the site does not qualify for that RV/trailer request because the compatible vehicle category limit is 25 feet.
3. **Given** an existing saved scan created before this feature, **When** the system upgrades and resumes checking, **Then** the scan continues running with no equipment length or accessibility restriction applied unless the user enables one.

---

### Edge Cases

- **Unknown vs unsupported attributes**: When a provider does not report a site's maximum vehicle length or accessibility status, a scan with that filter enabled MUST NOT match the site (fail closed), while an unrestricted scan still includes it.
- **Zero or cleared length**: Leaving equipment length blank or clearing it means unrestricted; entering zero or a negative length is rejected as invalid input (or clearly normalized to unrestricted only if explicitly defined by the form, never silently treating `1` foot as valid if out of sensible bounds—reject non-positive inputs `<= 0` when a length filter is supplied).
- **Upper bound validation**: Unreasonably large lengths (such as negative numbers, non-integer text, or values exceeding practical road limits like 200 feet) produce an actionable validation error before saving.
- **Zero-length provider values**: Some upstream providers encode "no length limit" or "missing length" as `0` or `null`; provider adapters MUST distinguish explicit positive maximum lengths from unset/zero sentinel values so `0` does not falsely pass a 25-foot filter or falsely reject a tent-only scan with no length filter.
- **Mixed equipment on a single site**: A site allowing tents and RVs up to 20 feet satisfies a 20-foot RV filter, fails a 25-foot RV filter, and satisfies an unrestricted or tent scan.
- **Unit consistency**: All user-entered and discovery RV lengths are compared in whole feet. Providers supplying metric lengths (e.g., meters) or fractional lengths convert conservatively downward to whole feet so a site is never advertised as longer than it is.
- **Multi-provider / multi-subscriber deduplication**: Changing one user's equipment length or accessibility filter MUST NOT trigger duplicate upstream polling or alter another subscriber's results on the same shared campground target.
- **Catalog staleness and enrichment failures**: Failing to fetch optional supplemental amenity details for a subset of campgrounds MUST NOT roll back core campground discovery or disable existing scans; last known verified metadata is retained until refreshed.

## Requirements _(mandatory)_

### Functional Requirements

- **FR-001**: System MUST populate discovery amenity and RV capacity metadata—electric hookups, water hookups, sewer hookups, pet-friendly status, ADA accessibility, maximum RV/trailer length, and supported site types—during catalog synchronization from verifiable provider data wherever the provider supplies them.
- **FR-002**: System MUST aggregate campground-level discovery amenities and maximum RV length onto parent recreation areas based on their enabled, reservable child campgrounds.
- **FR-003**: Explore discovery MUST allow campers to filter by ADA accessibility in addition to existing electric hookup, pets allowed, and minimum RV length filters across both list and map views.
- **FR-004**: System MUST treat unverified or unavailable discovery attributes conservatively (not verified / unknown) and MUST NOT infer amenities solely from unrelated fields (for example, water or sewer hookups alone do not imply electric hookups).
- **FR-005**: System MUST persist normalized site-level capability metadata alongside availability observations, including standardized site type, permitted equipment categories/names, maximum compatible vehicle/equipment length in whole feet (unknown when unstated), electric hookup status, and ADA accessibility status.
- **FR-006**: Saved scans MUST support optional user preferences for required vehicle/equipment length (in whole feet), preferred site/equipment types, electric hookup requirement, and ADA accessibility requirement.
- **FR-007**: System MUST validate scan equipment length inputs before saving, rejecting non-positive values (`<= 0`) and unrealistic values above a defined upper limit with clear user-facing error messages while treating omitted or cleared values as unrestricted.
- **FR-008**: Availability matching—across scan creation, scan result queries, matched counts, and notification delivery—MUST evaluate equipment length, equipment/site type, electric hookup, and ADA accessibility consistently using one shared filtering rule.
- **FR-009**: When a scan specifies a required vehicle/equipment length, a campsite MUST match only if its persisted maximum compatible vehicle length is explicitly known and greater than or equal to the scan's required length.
- **FR-010**: When a scan requires ADA accessibility, a campsite MUST match only if its persisted accessibility flag is explicitly true; unknown accessibility MUST NOT satisfy the filter.
- **FR-011**: Equipment, length, and accessibility filters MUST apply uniformly to both single-campground scans and recreation-area scans (`all` and `selected` coverage modes).
- **FR-012**: Multiple users monitoring the same campground and date window with different equipment lengths, site types, or accessibility filters MUST continue sharing one upstream availability poll while receiving isolated, preference-filtered results and alerts.
- **FR-013**: Pending outgoing notifications MUST be re-evaluated against the scan's current equipment and accessibility preferences before sending, preventing stale alerts after a user tightens their filter.
- **FR-014**: Users MUST be able to configure, view, edit, and clear equipment length and accessibility preferences in the scan creation/editing UI, and view persisted site equipment/length/accessibility capabilities on scan result cards/rows.
- **FR-015**: Existing saved scans and existing availability records created before this change MUST remain valid after migration with no length or accessibility restriction added automatically.

### Key Entities

- **Discovery Destination Summary**: Searchable campground or recreation-area summary containing aggregated amenities (electric, water, sewer, pets allowed, ADA accessibility), supported site types, and maximum RV/trailer length in feet.
- **Site Capability Snapshot**: Normalized per-campsite attributes captured during availability checks or site-catalog sync, recording site type, permitted equipment categories/names, maximum compatible vehicle length (unknown when omitted), electric hookups (unknown when omitted), and ADA accessibility (unknown when omitted).
- **Saved Scan Equipment Preferences**: Optional user-owned constraints on a saved scan—required vehicle length (feet), preferred site/equipment types, electric requirement, and ADA accessibility requirement—stored independently of shared polling targets.

## Success Criteria _(mandatory)_

### Measurable Outcomes

- **SC-001**: In synthetic end-to-end tests covering all supported provider families, 100% of provider-reported discovery amenities and RV length limits appear accurately in Explore search results after catalog sync, and filtering by electric, pets, ADA, or minimum RV length excludes 100% of non-qualifying destinations.
- **SC-002**: When a saved scan specifies a vehicle length or ADA accessibility requirement, 0% of qualifying matches, displayed site counts, or delivered alerts include campsites that are too short, non-accessible, or missing verified capability metadata.
- **SC-003**: Two or more users monitoring the same campground and date range with distinct equipment lengths or accessibility settings generate at most one upstream provider availability poll per refresh interval while receiving 100% preference-accurate results and alerts.
- **SC-004**: Campers can set, edit, and clear equipment length and accessibility filters in the scan form and view matched site capability details on desktop and mobile views with zero regressions to existing visual or functional suites.
- **SC-005**: Existing saved scans without new equipment or accessibility fields continue matching and alerting identically before and after schema migration.

## Assumptions

- **Units**: Vehicle and equipment lengths are measured and compared in whole feet across user inputs, discovery filters, and normalized site capabilities (matching the existing Explore RV length selector and US/Canadian park conventions; any metric upstream measurement is converted conservatively downward to whole feet).
- **Conservative unknown handling**: Providers vary in what metadata they expose. Missing or zero-sentinel length fields remain unknown rather than guessed, and active user filters fail closed so users are never alerted on an unverified fit.
- **Existing discovery schema**: The search index already defines fields for electric, water, sewer, pets, ADA accessibility, campsite types, and maximum RV length, so populating them primarily requires provider catalog extraction, aggregation, and exposing ADA parity in Explore filters.
- **Out of scope**:
  - Provider-enforced per-night booking restrictions (`T3.2.3`, such as per-night `minStay`/`maxStay` rules and residency advance-booking windows) are tracked separately and excluded from this specification.
  - Wilderness/backcountry permits and tours (`PLAN.md` Phase 3 Permits) are excluded from this specification.
  - Standalone legacy CLI `--equipment` parity (`20261110-005958-cli-parity` `D07`) is deferred separately, though its future implementation can consume the normalized provider equipment metadata introduced here.
