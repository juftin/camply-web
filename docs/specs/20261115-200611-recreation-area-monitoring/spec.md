# Feature Specification: Recreation-area and selected-campground monitoring

**Feature Branch**: `flawless-elk`

**Created**: 2026-11-15

**Status**: Specified and planned; implementation not started.

**Input**: “Write a spec to monitor entire recreation areas instead of singular campgrounds.” Follow-up: “The spec should also allow for multiple campgrounds in a given recreation area, but not all of them.”

## User Scenarios & Testing

### User Story 1 - Monitor every campground in a recreation area (Priority: P1)

As a camper who is flexible about where to stay within a park, I want to create one scan for its entire recreation area so I can find an opening without creating a separate scan for every campground.

**Why this priority**: The existing saved-scan workflow requires one campground per scan, even though discovery already groups campgrounds into recreation areas.

**Independent Test**: Using a synthetic area containing three eligible campgrounds, create one area scan with dates and preferences. Verify that all three are checked and qualifying openings from each are available through the same saved scan.

**Acceptance Scenarios**:

1. **Given** an area with three eligible campgrounds, **When** I choose “Monitor recreation area,” **Then** the form identifies the area and provider, defaults to “All campgrounds,” and shows that three campgrounds will be monitored.
2. **Given** valid dates, minimum stay, campsite types, and an electric requirement, **When** I save, **Then** one scan appears on my dashboard with the area name, “All campgrounds,” the campground count, and my dates and preferences.
3. **Given** a fourth campground becomes eligible in a successful catalog refresh, **When** the next monitoring round begins, **Then** the existing scan includes it automatically without an edit or another saved scan.
4. **Given** an area with more campgrounds than fit on a discovery page, **When** I monitor all campgrounds, **Then** every eligible member is included regardless of discovery pagination or map bounds.

---

### User Story 2 - Monitor selected campgrounds within an area (Priority: P1)

As a camper interested in several campgrounds within a park, I want to select only those campgrounds in one scan so I receive relevant openings without monitoring the rest of the park.

**Why this priority**: Campgrounds within one area can differ substantially in location and suitability. Area monitoring must support a deliberate subset as well as the whole area.

**Independent Test**: Select two of four synthetic campgrounds in one area. Verify that only those two contribute monitoring work, results, counts, and alerts to the scan, including after the area's catalog changes.

**Acceptance Scenarios**:

1. **Given** four eligible campgrounds in an area, **When** I choose “Selected campgrounds” and select two, **Then** I can review their names and save one scan covering exactly those two with shared dates and preferences.
2. **Given** a selected-campground scan, **When** an unselected campground has an opening or a new campground joins the area, **Then** neither contributes results or alerts to that scan and neither is added to its selection.
3. **Given** selected campgrounds outside the currently displayed page or search results, **When** I search or page through the choices, **Then** my existing selections remain selected and the total selected count remains accurate.
4. **Given** “Selected campgrounds” with no selections, **When** I try to save, **Then** the form explains that at least one campground is required and no scan is created.
5. **Given** all currently eligible campgrounds are explicitly selected, **When** I save, **Then** the scan remains a fixed selection; it does not silently become “All campgrounds.”
6. **Given** a campground outside the chosen provider or recreation area, **When** a selection containing it is submitted, **Then** the save fails without changing any saved scan.

---

### User Story 3 - Find and act on openings across campgrounds (Priority: P1)

As a camper, I want one results destination and scan summary that clearly identify each opening's campground so I can choose and book a qualifying stay.

**Why this priority**: Aggregating openings is useful only if campsite identities, consecutive stays, freshness, and booking destinations remain accurate.

**Independent Test**: Return matching and nonmatching openings from two included campgrounds, each containing a campsite with the same local ID. Verify independent site counts, campground labels, booking links, matching filters, and new-opening summaries.

**Acceptance Scenarios**:

1. **Given** matching openings in two included campgrounds and nonmatching openings elsewhere, **When** I view the scan, **Then** results and dashboard counts include only qualifying openings from its covered campgrounds, with a campground label and correct booking action for every site.
2. **Given** two campgrounds each have campsite `001`, **When** both sites match, **Then** they count as two distinct sites, and each site's separated stay ranges remain separate.
3. **Given** one available night at each of two campgrounds and a two-night minimum, **When** matches are evaluated, **Then** nights from different campgrounds or sites never combine into a qualifying stay.
4. **Given** newly matching openings in several included campgrounds within one notification window, **When** summary notifications are enabled, **Then** I receive at most one summary for that saved scan and window, identifying the area and affected campgrounds and linking to that scan's results.
5. **Given** unchanged openings, a failed campground check, or a new opening in an excluded campground, **When** another round runs, **Then** these do not produce a new-opening alert; a previously closed qualifying opening can alert when a successful check observes it again.
6. **Given** one included campground fails while others succeed, **When** I view results, **Then** successful results remain available, retained results from the failed campground are marked stale with their last successful check, and the area is visibly only partially checked.

---

### User Story 4 - Manage one scan without affecting other subscriptions (Priority: P2)

As a camper, I want to edit, pause, resume, or delete an area scan as one item while other campers and my separate campground scans continue to work.

**Why this priority**: Area coverage must fit existing scan ownership and lifecycle controls without multiplying user-visible subscriptions or disrupting shared monitoring.

**Independent Test**: Create overlapping all-area, selected-campground, and individual-campground scans for two users. Change one scan and verify its coverage and preferences change independently while common campground checks remain shared.

**Acceptance Scenarios**:

1. **Given** a saved area scan, **When** I edit it, **Then** its area, coverage mode, selected campgrounds, dates, and preferences are prefilled; saving preserves its identity, creation date, and active preference, while cancel or a failed save preserves its saved values.
2. **Given** a selected-campground scan, **When** I add or remove selections or switch between “All campgrounds” and “Selected campgrounds,” **Then** subsequent checks, results, and alerts reflect the saved coverage without altering another scan.
3. **Given** an area scan, **When** I change its destination to another area or to a single campground, **Then** coverage is validated for the new destination and old campground selections are not carried into another area.
4. **Given** overlapping scans, **When** I pause or delete one, **Then** it receives no further alerts, and campground checks continue wherever another eligible scan still needs them.
5. **Given** identical campground/date coverage across several scans or users, **When** monitoring runs, **Then** each campground/date combination has one logical availability check per round and each scan applies its own preferences to the shared observations.
6. **Given** a user without ownership, invitation eligibility, or permission to create scans, **When** that user attempts an area-scan operation, **Then** the same access rules as existing campground scans apply; scanning suspension continues to allow editing saved scans but prevents checks and notifications.

### Edge Cases

- Areas and campgrounds with identical names or native IDs across different providers remain distinct; campsite IDs can also repeat across campgrounds.
- An unknown or disabled area, or an area with no eligible campgrounds, cannot be used for a new scan. The form explains why; it never falls back to unrelated nearby campgrounds.
- A selected campground becoming disabled, nonreservable, removed, or assigned to another area stops contributing checks, results, and alerts. Its saved selection remains visible as unavailable until removed by the user; it can resume automatically if it becomes eligible in the original area again.
- An existing all-area scan that loses every eligible campground, or a selected scan with no eligible selections remaining, stays saved with an explicit “No eligible campgrounds” status and performs no availability checks. Restoring eligible membership resumes coverage if the scan remains active and permitted.
- Disabling or removing the parent area stops its scans' monitoring and alerts and shows the unavailable destination without deleting the user's saved scan. Restoring the area restores eligible coverage subject to the saved active preference and access rules.
- Failed or incomplete catalog refreshes do not establish that campgrounds have left an area. Last confirmed membership is retained until a successful refresh establishes changes.
- Missing campground coordinates or photos do not prevent inclusion. Campgrounds without a confirmed parent relationship are not guessed into an area.
- Partial or total provider failure never appears as a successful empty result. A successful empty response clears that campground's old openings; a failed response preserves its last successful observation with stale labeling.
- Date validation, exclusive check-out, minimum consecutive stay, expired-night removal, paused-result labeling, and ended-scan behavior follow existing campground scans.
- Selection order and repeated submitted IDs do not create distinct coverage definitions. All-area mode remains distinct from an explicit subset containing every current member.
- A user may keep separate overlapping scans, including an individual scan and an area scan covering the same campground. Alert suppression remains per saved scan; no cross-scan notification merge is introduced.

## Requirements

### Functional Requirements

- **FR-001**: Users MUST be able to save a scan for either a single campground or one provider-qualified recreation area. An area scan MUST offer “All campgrounds” and “Selected campgrounds” coverage, with shared dates, minimum stay, campsite types, and electric preference across included campgrounds.
- **FR-002**: Recreation-area detail pages and area entries in discovery lists and map details MUST offer a monitoring action. The new-scan destination picker MUST distinguish recreation areas from campgrounds and allow either to be selected. Area monitoring MUST default to “All campgrounds” and show the area, provider, and eligible campground count before saving.
- **FR-003**: Users choosing “Selected campgrounds” MUST be able to discover every eligible campground in the chosen area, search choices by campground name, select one or more, and review their selected names and count. Selection MUST survive changes to search text or displayed pages, and an explicit subset MUST remain a subset even when it contains all current members.
- **FR-004**: Eligible area membership MUST consist only of enabled, reservable campgrounds explicitly associated with the selected area and provider. All-area coverage MUST include the complete eligible membership without discovery limits or dependence on the map viewport. Subset coverage MUST include exactly the saved selections that remain eligible members.
- **FR-005**: Successful catalog changes MUST affect coverage by the next monitoring round after that refresh. All-area scans MUST include newly eligible members automatically. Subset scans MUST NOT add unselected members automatically and MUST retain unavailable selections visibly for review and possible restoration. Failed or incomplete catalog refreshes MUST preserve last confirmed membership.
- **FR-006**: Creation MUST reject unknown or disabled destinations, invalid dates or stay preferences, areas with no eligible campgrounds, and empty or invalid subsets. A new subset containing any unknown, ineligible, cross-area, or cross-provider campground MUST fail as a whole. Existing unavailable selections may remain on an edited scan, but any newly selected campground MUST be eligible. Changing destination or coverage MUST leave at least one eligible campground; edits only to dates or preferences on an existing unavailable scan remain allowed. Submitting conflicting destination or coverage choices MUST fail without partial changes.
- **FR-007**: One saved area scan MUST appear as one manageable item in the user's dashboard and administration views. Its name, provider, coverage mode, dates, and counts MUST distinguish total included eligible campgrounds, unavailable saved selections, and campgrounds with qualifying openings. It MUST NOT appear as several separately managed child scans.
- **FR-008**: Area scans MUST support existing ownership, invitation, suspension, pause/resume, edit, delete, and expiration behavior. Editing MUST support changing destination, coverage mode, selected campgrounds, dates, and preferences while preserving scan identity, creation date, and active preference. Failed saves and canceled edits MUST leave saved coverage unchanged. Changing areas MUST require valid coverage for the new area.
- **FR-009**: For a given user, duplicate scans MUST be rejected when provider, destination kind and identity, coverage mode, normalized selected membership when applicable, and dates match an existing scan, regardless of personal filters. Selection order or repeated IDs MUST NOT bypass this rule. All-area and selected coverage remain different definitions; distinct overlapping scans are permitted.
- **FR-010**: Overlapping area, subset, and single-campground scans MUST share one logical availability check per provider, campground, and date range per monitoring round, including across users. Removing one subscription MUST NOT change another's preferences, observations, or eligibility, and no campground check may continue solely for paused, suspended, deleted, ended, or unavailable coverage.
- **FR-011**: Results, counts, and alerts MUST apply the same saved preferences and existing date/stay rules to each included campsite independently. Provider, campground, and campsite together determine site identity. Nights MUST NOT combine across campgrounds or sites, and repeated stay ranges for one site MUST NOT inflate the distinct-site count.
- **FR-012**: Area-scan results MUST show each site's campground name, site identity, qualifying consecutive stays, known attributes, and correct provider booking action. Results MUST retain existing stay-date grouping and bounded display, with search covering the whole included result set by campground name or site name/number. The area overview MUST link to its provider destination when a link is available.
- **FR-013**: Each monitoring round MUST evaluate the scan's eligible coverage as established at the start of that round and finish after every included campground succeeds or reaches a bounded check-failure deadline defined during planning. Successful observations MUST become available without waiting for failed campgrounds. Status MUST distinguish waiting for an initial check, complete coverage, partial failures or pending checks, no eligible campgrounds, paused, and ended scans. A last-successful-full-check time MUST advance only when every included campground succeeds; per-campground freshness and retained stale observations MUST remain visible. No matches in partial coverage MUST NOT be presented as no availability throughout the area.
- **FR-014**: Failure in one campground MUST NOT prevent checking or alerting on successful observations from others. A failed check MUST retain its last successful observation without treating retained results as new openings. A successful empty check MUST remove previous openings for that campground. Removed or excluded coverage MUST stop contributing displayed results and notifications.
- **FR-015**: In summary mode, newly matching sites observed successfully for one saved area scan MUST be combined into at most one summary per bounded notification window. The window MUST close soon enough to meet the existing 60-second detection-to-delivery objective and MUST NOT wait for the entire area round if other campground checks are still pending. Summaries MUST identify the recreation area and affected campground names and link to the saved scan's results, including after authentication and under configured deployment path prefixes. Unchanged openings MUST remain suppressed, and reopened qualifying stays MUST follow existing alert behavior. Where individual alerts are configured, each MUST identify its actual campground and use that site's booking destination.
- **FR-016**: Existing campground scans MUST retain their identities, saved preferences, controls, and notification behavior. Existing campground-only creation requests MUST continue to work. Expanded scan representations MUST clearly identify the destination kind and area coverage without inventing a campground identity for an area.
- **FR-017**: Area and subset monitoring MUST behave consistently in both standalone and distributed deployments. Larger areas MUST respect existing provider pacing and bounded scheduling; including more campgrounds MUST NOT grant faster polling or bypass provider limits. Opening a dashboard or results page MUST use saved observations without triggering provider availability requests.
- **FR-018**: Coverage selection, selected-name review, validation, saved-scan controls, and results MUST work with keyboard navigation and on mobile and desktop. Initial loading, no eligible campgrounds, save failures, and stale or partial results MUST have distinct, actionable messages.

### Key Entities

- **Scan destination**: A single campground or recreation area, identified within its provider; establishes which coverage choices are valid.
- **Area coverage selection**: Either all eligible members dynamically, or an explicitly saved nonempty set of campground identities in one recreation area. An unavailable saved selection remains identifiable without contributing eligible coverage.
- **Saved scan**: One user's destination, coverage selection, date window, shared matching preferences, active preference, and stable identity.
- **Campground observation**: Availability for one provider-qualified campground and date window, reusable by all eligible scans covering it, with last successful check and failure state.
- **Monitoring round**: One evaluation of an area scan's included campgrounds, ending after success or failure for each member, used to describe coverage completeness.
- **Notification window**: A bounded period grouping a saved area scan's newly observed matching openings into one summary without waiting for every campground or exceeding the notification delivery objective.
- **Matching opening**: A provider- and campground-qualified campsite with independently qualifying consecutive stays, booking destination, and observation freshness.

## Success Criteria

### Measurable Outcomes

- **SC-001**: A user can create one all-area scan covering 100% of eligible members in a synthetic 125-campground area, including members beyond the first discovery page, without creating or managing child scans.
- **SC-002**: Selecting two of four campgrounds yields results, counts, and alerts from exactly those two. Adding a fifth campground does not change this subset, while an all-area scan includes it by the next round after a successful catalog refresh.
- **SC-003**: Acceptance checks verify that 100% of displayed and notified matches belong to included campgrounds and satisfy saved preferences; repeated site IDs in different campgrounds stay distinct, and zero stays combine nights across sites or campgrounds.
- **SC-004**: For ten users with overlapping area, subset, and campground scans covering the same three campground/date combinations, one monitoring round performs three logical availability checks, with independently filtered results for each saved scan.
- **SC-005**: A round with three successful campground checks and one failure exposes all successful matches, identifies partial coverage and stale observations, and generates no false closure or reopened alert from the failed check. In summary mode it sends at most one summary per saved scan per notification window within the existing 60-second detection-to-delivery objective.
- **SC-006**: Creation, subset editing, mode changes, pause/resume, deletion, invalid-selection rejection, duplicate detection, ownership isolation, and empty-membership recovery pass acceptance checks in standalone and distributed deployments. Existing single-campground behavior passes its regression checks unchanged.
- **SC-007**: Browser checks complete both coverage-selection workflows using keyboard controls at mobile and desktop widths, including choices outside the first displayed page, a failed save with selections preserved, and a partially checked results view.

## Assumptions

- “Recreation area” means an existing provider-defined parent destination, not a radius, map boundary, or a name-based grouping spanning providers. Scope is one recreation area per area scan; custom collections across areas or providers are deferred.
- A selected subset may contain one campground or multiple campgrounds. Dates and preferences apply to the whole scan; per-campground dates, filters, exclusions from all-area mode, and automatic selection recommendations are outside this feature.
- The scope is persistent application monitoring and its existing management and notification surfaces. The CLI already supports recreation-area expansion for foreground searches under [feature 026](../20261110-005958-cli-parity/spec.md); new CLI flags, saved CLI scan management, and changes to that foreground behavior are outside this feature.
- Existing catalog synchronization supplies confirmed area membership and enabled/reservable status. Membership changes become known through that process; this feature does not introduce live catalog discovery on page views or promise to discover upstream changes before synchronization.
- Existing provider availability support, matching rules, booking links, notification settings, access rules, and polling configuration are dependencies. Providers without recreation-area membership continue to support individual campground scans only; this feature adds no provider integration or permit/tour monitoring.
- The existing 60-second detection-to-delivery objective and provider pacing constrain summary aggregation. The technical plan defines bounded notification windows without adding a user-facing setting or delaying alerts until a large area's full round completes.
