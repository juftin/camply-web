# Feature Specification: Full Mobile-Responsive UI Audit & Polish

**Feature Branch**: `034-mobile-responsive-audit`

**Created**: 2026-11-26

**Status**: Draft

**Input**: User description: "Write a spec for #6: 4.1.6 (Full mobile-responsive UI audit and polish — Phase 4 T4.1.6)"

## Clarifications

### Session 2026-11-26

- Q: How should the mobile navigation header and menu behave across smartphone screens? → A: Replace the inline dropdown with a slide-over navigation drawer (dimmed backdrop, focus containment, Escape/outside-tap dismissal) and keep the mobile header consistently sticky.
- Q: How should administrative data tables adapt on smartphone screens? → A: Hybrid approach—use stacked mobile cards for action-heavy management lists (Users, Invitations, Scans) and self-contained horizontal-scroll tables for dense telemetry, log, and detail tables (Operations task history, Audit Log, trend and detail tables).
- Q: How should complex modal dialogs present on small smartphone screens? → A: Use viewport-bounded dialogs on mobile with a scrollable body, pinned header and footer actions (so Save/Cancel remain visible while scrolling), and viewport-clamped calendar popovers.
- Q: How broad should the new automated mobile visual snapshot baselines be across previously desktop-only routes? → A: Add one representative mobile visual baseline (covering both light and dark themes across the suite) for every previously desktop-only route and key dialog/picker, plus automated zero-overflow verification across all 26 routes.

## User Scenarios & Testing _(mandatory)_

### User Story 1 - Complete core camper discovery and monitoring journeys on phones (Priority: P1)

As a camper using a smartphone to search for campgrounds and monitor cancellations, I want every discovery, destination detail, dashboard, and scan detail screen to fit cleanly on my phone with clear hierarchy, comfortable tap targets, and no clipped or overflowing layouts, so I can find campsites and jump to book openings while away from a computer.

**Why this priority**: Campers frequently react to real-time availability alerts and browse destinations directly from their phones. Layout breakage, overlapping controls, or horizontal page overflow on core journeys directly prevents users from creating scans or booking scarce openings in time.

**Independent Test**: Walk through the complete camper journey on both compact (375 px wide) and standard (390 px wide) smartphone viewports in light and dark modes: open Home and select a search suggestion, filter and browse Explore (with map expanded and collapsed, and a destination marker selected), open a Campground and Recreation Area detail page (browsing photos, map, and practical details), manage grouped scans on Dashboard (populated and empty states), and inspect openings on Scan Detail (calendar, campsite cards, availability grid, and booking links). Verify zero unintended page-level horizontal scroll, legible text, and reachable controls on every view.

**Acceptance Scenarios**:

1. **Given** a visitor on a smartphone (375 px or 390 px wide) opens Home and types into the destination search bar, **When** search suggestions appear, **Then** the suggestion list stays within the screen bounds, displays clear destination names and locations without awkward truncation or overlapping badges, and allows comfortable single-tap selection.
2. **Given** a camper opens Explore on a smartphone, **When** they apply search text, amenity, accessibility, or vehicle-length filters, toggle the map open or closed, and select a map pin, **Then** filter controls wrap or stack cleanly without clipping, the map and destination preview remain fully visible and dismissible, and pagination controls stay easy to tap.
3. **Given** a camper opens a Campground or Recreation Area detail page on a smartphone, **When** they scroll through the header, action buttons, photo gallery, map, and practical details, **Then** long destination titles, provider badges, and monitoring actions wrap cleanly without pushing the page wider than the screen, and photo viewing controls remain reachable.
4. **Given** an authenticated camper opens Dashboard or Scan Detail on a smartphone, **When** they expand campground groups, pause/resume/delete scans, switch between calendar/card/grid views, or tap a booking link, **Then** every status badge, metadata pill, and action button remains readable, non-overlapping, and comfortably tappable without causing document-level horizontal overflow.

---

### User Story 2 - Complete forms, pickers, dialogs, and account flows comfortably on small screens (Priority: P1)

As a camper or account holder creating scans or configuring notifications on my phone, I want every form, confirmation modal, date picker, and account settings screen to fit within the mobile viewport with clear labels, reachable primary actions, and touch-friendly inputs, so I never lose access to buttons or struggle to pick dates on a small screen.

**Why this priority**: Modal dialogs, nested calendar popovers, and multi-field forms are the most failure-prone surfaces on small screens. If a submit button is pushed off-screen or a date popover clips past the screen edge, users cannot create scans or configure alerts on mobile.

**Independent Test**: On 375×667 and 390×844 mobile viewports in light and dark modes, open and complete: creating a new scan (selecting check-in and check-out dates from calendar popovers, duration presets, weekday-night preferences, equipment/accessibility filters, and recreation-area campground selection), editing an existing scan, triggering delete confirmation and delete-error states, signing in / signing up / completing a forced password change, requesting invite-only access, and updating Profile (notification provider switching, test notification, copy actions, and revoking active sessions). Verify every field, popover, error banner, and submit/cancel action remains fully accessible.

**Acceptance Scenarios**:

1. **Given** a camper opens the Create Scan or Edit Scan dialog on a compact smartphone (375×667), **When** they scroll through the form and open the check-in or check-out date picker, **Then** the dialog stays within the viewport with a scrollable body and pinned header/footer actions (keeping close, cancel, and save visible at all times), and the date picker stays clamped inside the visible viewport.
2. **Given** a camper configures a recreation-area scan with selected campgrounds on a smartphone, **When** they filter and toggle campgrounds in the picker, **Then** campground names, checkboxes, and selection summaries remain readable without horizontal overflow.
3. **Given** a user visits Sign In, Sign Up, Invite-Only access, or forced password-change screens on a smartphone, **When** they fill out credentials and submit, **Then** inputs, password visibility/copy controls, validation errors, and submit buttons stack cleanly with adequate spacing and never trigger unintended viewport zoom.
4. **Given** an authenticated user opens Profile on a smartphone, **When** they configure Pushover or ntfy settings (including long custom server URLs or access tokens), copy their topic, send a test notification, or inspect and revoke active sessions, **Then** long values wrap or truncate safely inside their containers, copy/test/save buttons remain clear and tappable, and session rows remain legible.

---

### User Story 3 - Navigate consistently across all public, informational, and authenticated views on mobile (Priority: P2)

As a mobile visitor moving between pages, I want predictable navigation, a clean and accessible mobile menu, and well-proportioned public and informational pages, so the entire application feels cohesive and polished rather than desktop-first.

**Why this priority**: First-time visitors frequently land on public pages (Providers, How It Works, FAQ, Contact, legal pages) before signing up, and every mobile user relies on the header menu and footer across every session. Inconsistent spacing, awkward mobile menu behavior, or cramped informational pages undermine trust and usability.

**Independent Test**: On 375 px, 390 px, and 768 px viewports in light and dark modes, open and close the slide-over mobile navigation drawer (via button tap, selecting a route, tapping the dimmed backdrop, and pressing Escape), verify the header remains consistently sticky while scrolling, verify footer layout, and visit Providers, How It Works, FAQ, Contact, Privacy Policy, Terms of Service, and enabled community pages (Ethos, Contribute). Confirm consistent spacing, readable line lengths, accessible navigation states, and zero horizontal overflow.

**Acceptance Scenarios**:

1. **Given** a visitor on a smartphone scrolls down any page and taps the mobile menu trigger in the sticky header, **When** the slide-over navigation drawer opens, **Then** a dimmed backdrop frames the drawer, focus stays contained inside the drawer while open, assistive technologies observe accurate expanded/collapsed state, and selecting a link, tapping the backdrop, or pressing Escape closes the drawer cleanly and restores focus.
2. **Given** a visitor browses Providers, How It Works, FAQ, Contact, Privacy Policy, Terms of Service, or enabled community pages on a smartphone, **When** they scroll from header to footer, **Then** headings, provider cards, accordion questions, external links, and footer links wrap with consistent padding and hierarchy without overflow or colliding elements.
3. **Given** a user views the application at an intermediate tablet width (768 px), **When** navigation switches between compact mobile controls and expanded desktop controls, **Then** no links wrap awkwardly onto overlapping lines or clip off the right edge of the header.

---

### User Story 4 - Inspect and administer the platform effectively on mobile devices (Priority: P2)

As an instance administrator checking system health, approving invitations, or troubleshooting scans from my phone, I want every administrative screen—including tables, charts, filter bars, and account-management dialogs—to remain legible, navigable, and usable on small screens, so I can respond to operational issues without waiting to reach a desktop.

**Why this priority**: Self-hosters and operators often receive invitation or outage alerts on their phones and need to approve access, trigger a provider sync, suspend scanning, or inspect recent worker tasks immediately. Today, admin tables, filter toolbars, and detail pages have the largest gap in mobile layout polish and verification.

**Independent Test**: On 375 px and 390 px viewports in light and dark modes, navigate via the admin navigation bar through Overview (KPIs and metric trend charts/tables), Users (list, Create User dialog with generated password reveal/copy, Reset Password dialog), User Detail, Invitations (pending approval/revocation), Scans, Scan Detail, Shared Target Detail, Operations (worker/queue health, recent tasks, sync trigger), and Audit Log. Verify every screen has zero page-level horizontal overflow, legible data presentation, and reachable row/dialog actions.

**Acceptance Scenarios**:

1. **Given** an administrator opens any Admin page on a smartphone, **When** they use the admin section navigation bar, **Then** all admin sections are reachable, the active section is clearly highlighted, and the navigation bar does not push the overall page wider than the viewport.
2. **Given** an administrator views action-heavy management lists (Users, Invitations, Scans) on a smartphone, **When** records render below desktop table width, **Then** each record adapts into a readable stacked mobile card keeping primary identifiers, status badges, and row actions comfortably tappable without horizontal scrolling; **And Given** an administrator views dense telemetry, log, or detail tables (Operations task history, Audit Log, trend tables, and detail breakdowns) on a smartphone, **Then** each table scrolls smoothly inside a self-contained horizontal scroll region with zero document-level overflow.
3. **Given** an administrator opens Create User or Reset Password dialogs on a smartphone, **When** they generate and reveal a temporary password and copy it, **Then** the revealed credential wraps or scrolls safely within the dialog without stretching the modal off-screen, and the copy and confirmation buttons remain easy to tap.
4. **Given** an administrator inspects Operations or Overview trend charts on a smartphone, **When** charts, legends, time-window selectors, and status badges render, **Then** labels and legends do not overlap, controls wrap cleanly, and degraded/outage callouts remain clear.

---

### User Story 5 - Guard mobile quality continuously across routes and key states (Priority: P3)

As a maintainer shipping ongoing changes, I want automated mobile layout and visual verification covering all major routes, dialogs, and states across light and dark appearances, so future UI changes cannot silently introduce mobile overflow, clipping, or broken responsive styling.

**Why this priority**: A one-time manual audit decays quickly as new features ship. Expanding automated mobile verification to cover previously desktop-only routes locks in the audit gains permanently while keeping verification fast.

**Independent Test**: Run the full automated visual and responsive verification suite and confirm that every previously desktop-only route and key interactive overlay (mobile navigation drawer, scan form, date pickers, search dropdown, admin password dialogs) has at least one representative mobile visual baseline (covering both light and dark themes across the suite), and that all 26 application routes pass automated zero-overflow checks at smartphone viewports.

**Acceptance Scenarios**:

1. **Given** the automated visual verification suite runs across all audited mobile scenarios, **When** any audited page or overlay renders at its configured smartphone viewport, **Then** document-level horizontal overflow is verified to be zero and visual output matches the approved baselines.
2. **Given** previously desktop-only routes (such as Sign In, Providers, How It Works, FAQ, Profile, Scan Form & date pickers, Dashboard empty state, and Admin Users/Invitations/Scans/Audit/Detail pages), **When** the audit concludes, **Then** each route and key overlay has at least one representative mobile baseline (balancing light and dark coverage across the suite) and all 26 routes have automated zero-overflow verification so regressions are caught automatically before merge.

---

### Edge Cases

- **Very narrow phone screens (360 px wide) and short phone screens (375×667)**: Dialogs, sticky headers, date pickers, and bottom action bars must remain usable without trapping scroll or hiding primary buttons.
- **Long unbroken strings**: Long email addresses, custom notification URLs, destination names, UUIDs, and generated temporary passwords must wrap or scroll inside their own container rather than forcing page-wide horizontal scroll.
- **High-density data states**: Pages with 10+ found campsites, multi-campground recreation-area coverage lists, multiple active user sessions, or dense admin tables with multiple action buttons per row must maintain readable spacing and separation.
- **Nested overlays on touch screens**: Calendar popovers inside modal dialogs, full-screen photo viewers, and confirmation dialogs must layer cleanly, respect viewport edges, and dismiss cleanly without leaving the page scroll-locked.
- **Mobile header scroll & drawer interaction**: The mobile header must stay consistently sticky across vertical scrolling, opening the slide-over drawer mid-page must prevent background scroll bleed and align cleanly with the viewport, and navigating to a new route must always reset the drawer to closed.
- **Reduced motion & theme parity**: Transitions (drawer slide-in/out, carousels, dialogs) must honor reduced-motion preferences, and all responsive adjustments must preserve clear visual contrast in both light and dark appearance modes.
- **Desktop preservation**: Responsive polish and mobile adaptations must not regress layout balance, information density, or visual baselines on desktop viewports (1280 px and wider).

## Requirements _(mandatory)_

### Functional Requirements

- **FR-001**: Every user-facing route in the application (public, informational, authentication, camper dashboard/discovery, account profile, and administrator views) MUST render with zero unintended document-level horizontal overflow at smartphone widths of 375 px and 390 px, as well as tablet width of 768 px.
- **FR-002**: All primary interactive controls on mobile (navigation triggers, buttons, links in navigation/menus, form switches, pagination controls, dialog close buttons, and table row actions) MUST provide comfortable touch ergonomics (minimum 44×44 px effective tap area or clear spacing preventing accidental adjacent taps) and unambiguous focus/active states.
- **FR-003**: The mobile header MUST remain consistently sticky during vertical scrolling, and mobile navigation MUST open as a slide-over drawer with a dimmed backdrop, focus containment while open, accurate expanded/collapsed accessibility state, and reliable dismissal via route selection, backdrop tap, or keyboard Escape.
- **FR-004**: All modal dialogs and popovers (including scan creation/editing, check-in/check-out date pickers, delete confirmation, destination photo viewer, admin user creation, and password reset) MUST stay within visible mobile viewport bounds; multi-field dialogs MUST use a scrollable body with pinned header and footer actions so close, cancel, and submit remain visible while scrolling, and nested popovers MUST clamp cleanly within the viewport without zooming or horizontal scrolling.
- **FR-005**: All form inputs on mobile MUST prevent unintended browser auto-zoom on focus, display clear labels and validation messages without clipping, and stack multi-column field groups cleanly on narrow viewports.
- **FR-006**: Discovery and destination workflows (Home search suggestions, Explore filter bar, collapsible map, map marker previews, Campground details, and Recreation Area details) MUST maintain clear visual hierarchy, responsive media sizing, and unobstructed map/list interaction on smartphones.
- **FR-007**: Camper monitoring views (Dashboard grouped scan cards, empty states, Scan Detail header, availability calendar, deduplicated campsite cards, availability grid, and recreation-area coverage breakdown) MUST keep status badges, criteria pills, stay windows, and booking actions legible and free of overlapping text or clipped controls on mobile.
- **FR-008**: Account and access views (Sign In, Sign Up, forced password change, Invite-Only access request, and User Profile including notification settings, copy controls, test alerts, and Active Sessions) MUST handle long strings (emails, URLs, topics, tokens, session metadata) without breaking layout width or hiding actions.
- **FR-009**: All administrator views (Overview, Users, User Detail, Invitations, Scans, Scan Detail, Shared Target Detail, Operations, and Audit Log) MUST provide usable mobile navigation, legible charts/metrics without overlapping axis/legend text, stacked mobile card layouts for action-heavy management lists (Users, Invitations, Scans), and self-contained horizontally scrollable tables for dense telemetry, log, and detail tables (Operations, Audit Log, trend and detail tables) with zero document-level horizontal overflow.
- **FR-010**: Public and informational pages (Providers, How It Works, FAQ, Contact, Privacy Policy, Terms of Service, and optional Ethos/Contribute pages when enabled) MUST present consistent mobile padding, readable typography scale, and clean multi-column-to-single-column stacking.
- **FR-011**: The site footer MUST wrap cleanly across smartphone and tablet widths with consistent spacing and comfortably tappable links.
- **FR-012**: All responsive layout fixes and visual polish MUST preserve clear visual hierarchy, consistent component styling, and readable contrast across both light and dark appearance modes.
- **FR-013**: Desktop layouts (1280 px and wider) MUST remain unregressed in structure, density, and visual appearance except where an intentional cross-viewport component polish improves both mobile and desktop consistently.
- **FR-014**: Automated mobile verification MUST add at least one representative mobile visual baseline (balancing light and dark appearances across the suite) for every previously desktop-only route and critical interactive overlay (including the mobile navigation drawer, Auth, Providers, How It Works, FAQ, Profile, Scan Form with calendar pickers, Dashboard empty state, and all remaining Admin pages) and MUST enforce automated zero document-level horizontal overflow verification across all 26 application routes.
- **FR-015**: The audit MUST produce a concise route-by-route audit summary documenting findings found and resolved across all routes so completion of roadmap item `T4.1.6` is transparent and traceable.

### Audit Scope Inventory

- **Viewport Tiers**:
  - **Compact Smartphone**: 375 px wide (e.g., 375×667 / 375×812) — minimum primary target width; graceful usability down to 360 px.
  - **Standard Smartphone**: 390 px wide (e.g., 390×844) — baseline modern phone target.
  - **Tablet / Transition Breakpoint**: 768 px wide — validates responsive breakpoint handoff between mobile and desktop layouts.
  - **Desktop Regression Guard**: 1280×800 — ensures desktop views remain intact.
- **Route Groups Audited**:
  - **Shell & Navigation**: Header, mobile menu, theme toggle, footer, dismissible banners, route-level loading/error fallbacks.
  - **Public & Informational**: Home (with search dropdown), Providers, How It Works, FAQ, Contact, Privacy Policy, Terms of Service, Ethos, Contribute.
  - **Discovery & Destinations**: Explore (map expanded/collapsed, filters, marker selection, pagination), Campground detail, Recreation Area detail (including photo viewer).
  - **Camper Monitoring**: Dashboard (populated, expanded groups, empty state), Scan Detail (single campground & recreation area, calendar, cards, grid, paginated results), Create/Edit Scan dialog & date pickers, Delete confirmation & error feedback.
  - **Account & Access**: Sign In / Sign Up, Forced Password Change, Invite-Only access request, User Profile (Pushover, ntfy, test notifications, Active Sessions).
  - **Administration**: Admin navigation bar, Overview (KPIs & trend charts/tables), Users (list, Create User, Reset Password), User Detail, Invitations, Scans, Scan Detail, Shared Target Detail, Operations, Audit Log.

## Success Criteria _(mandatory)_

### Measurable Outcomes

- **SC-001**: 100% of audited routes and interactive overlays (all 26 application routes plus primary dialogs, pickers, and menus) exhibit zero unintended document-level horizontal overflow at 375 px, 390 px, and 768 px viewport widths.
- **SC-002**: 100% of primary interactive controls across audited mobile screens meet comfortable touch-target ergonomics (at least 44×44 px effective tap target or non-crowded spacing) with no overlapping or clipped labels.
- **SC-003**: 100% of modal dialogs and nested date/campground pickers fit within a 375×667 viewport with pinned header/footer actions on multi-field dialogs, unobstructed body scrolling, and viewport-clamped popovers.
- **SC-004**: 100% of action-heavy admin management lists (Users, Invitations, Scans) render as readable stacked mobile cards and 100% of dense admin telemetry/log/detail tables and metric charts remain legible on 375 px and 390 px screens without pushing the page horizontally or producing overlapping axis/legend text.
- **SC-005**: Automated mobile visual verification includes at least one representative mobile baseline (covering both light and dark appearances across the suite) for every previously desktop-only route and key dialog/picker, and automated zero-overflow checks cover 100% of the 26 application routes with 100% passing.
- **SC-006**: Zero unintended visual or functional regressions occur across existing desktop views and automated verification suites.
- **SC-007**: A completed route-by-route audit record confirms every route in the Audit Scope Inventory was inspected, remediated where needed, and verified before closing roadmap item `T4.1.6`.

## Assumptions

- **Web application scope**: This feature covers responsive mobile web usability and visual polish for the existing web application; a native iOS/Android app or offline PWA mode is out of scope.
- **User-interface-only changes**: All fixes are achieved within the web user interface without changing server behavior, data contracts, or persisted data schemas.
- **Existing visual design system preserved**: Polish refines spacing, wrapping, touch targets, overflow containment, and responsive composition within the existing visual language and light/dark themes rather than introducing a new brand theme or desktop redesign.
- **Builds on recent mobile work**: Recent features (such as the reworked Found Campsites calendar/cards/grid views, Explore map interaction, and destination photo carousel) already include mobile layouts; this audit verifies them alongside older and previously desktop-only routes to ensure uniform quality across the entire application.
- **Minimum supported viewport**: Primary layout perfection is guaranteed at 375 px and above (covering modern iOS and Android devices), with graceful usability down to 360 px; legacy sub-320 px screens are out of scope.
- **Documentation site excluded**: The separately generated documentation portal served under `/docs/` is managed by its own documentation theme and is out of scope for this application UI audit.
