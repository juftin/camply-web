# Feature Specification: Checklist Data Layer

**Feature Branch**: `001-checklist-data-layer`
**Created**: 2026-03-22
**Status**: Draft
**Input**: User description: "@docs/agents/CHECKLIST.md Data Layer"

## User Scenarios & Testing _(mandatory)_

### User Story 1 - Early Access User Identification (Priority: P1)

As a system administrator, I want to flag specific users as "early access" so that I can control who has access to the campsite poller features during the beta phase.

**Why this priority**: High priority as it governs access control for the entire platform's initial rollout.

**Independent Test**: Can be tested by creating a user and verifying the `is_early_access_user` flag can be set and retrieved independently.

**Acceptance Scenarios**:

1. **Given** a new user record, **When** they are created with `is_early_access_user=true`, **Then** the database should persist this flag correctly.
2. **Given** an existing user record, **When** their `is_early_access_user` flag is updated, **Then** the new value should be reflected in subsequent queries.

---

### User Story 2 - Efficient De-duplicated Polling (Priority: P1)

As the system, I want to track unique scan targets (combinations of provider, campground, and dates) so that I only perform one API request per target, regardless of how many users are watching that same campground for those dates.

**Why this priority**: Essential for system efficiency and to avoid being throttled or banned by campsite provider APIs.

**Independent Test**: Can be tested by attempting to create multiple scan targets for the same campground and dates and verifying that only one unique record is maintained via hashing and constraints.

**Acceptance Scenarios**:

1. **Given** a request to monitor a specific campground for a specific date range, **When** no such record exists, **Then** a new `UniqueTarget` record with a unique hash should be created.
2. **Given** a request to monitor a specific campground for a specific date range, **When** a record already exists for those exact parameters, **Then** the system should reuse the existing `UniqueTarget` record.

---

### User Story 3 - User-Specific Search Filtering (Priority: P2)

As a camper, I want to specify my own preferences for a scan (like minimum stay length or electric hookup requirements) so that I only get notified when a site matching my exact needs is found by the global poller.

**Why this priority**: Critical for user value, ensuring notifications are relevant to the individual user's needs.

**Independent Test**: Can be tested by creating `UserScan` records with different filters for the same `UniqueTarget` and verifying they persist correctly.

**Acceptance Scenarios**:

1. **Given** a `UniqueTarget` being monitored, **When** a user creates a scan for it, **Then** their specific filters (min stay, equipment types, electric) should be saved in the `UserScan` record.
2. **Given** multiple users watching the same `UniqueTarget`, **When** their scan records are retrieved, **Then** each record should contain that user's specific filter criteria.

---

### User Story 4 - Availability Result Caching (Priority: P2)

As the system, I want to cache specific campsite availability findings so that I can track changes over time and efficiently notify users when new sites become available.

**Why this priority**: Necessary for the notification logic and providing a history of found sites.

**Independent Test**: Can be tested by saving and retrieving `ScanResult` records for a `UniqueTarget`.

**Acceptance Scenarios**:

1. **Given** a `UniqueTarget` poll just finished, **When** specific campsites are found to be available, **Then** those findings should be persisted in the `ScanResult` table with a timestamp.

---

## Requirements _(mandatory)_

### Functional Requirements

- **FR-001**: System MUST implement a `User` model with `is_early_access_user` (boolean) and `auth0_id` (string) fields.
- **FR-002**: System MUST implement a `UniqueTarget` model that represents a unique combination of `provider_id`, `campground_id`, `start_date`, and `end_date`.
- **FR-003**: System MUST enforce uniqueness for `UniqueTarget` using a SHA256 hash of its composite parameters.
- **FR-004**: System MUST implement a `UserScan` model linking a `User` to a `UniqueTarget`.
- **FR-005**: `UserScan` MUST support filters: `min_stay_length` (integer), `preferred_types` (array of strings), and `require_electric` (boolean).
- **FR-006**: System MUST implement a `ScanResult` model to store individual availability findings for a `UniqueTarget`.
- **FR-007**: All models MUST use composite primary keys (`id` + `provider_id`) where appropriate for provider-sourced entities, as defined in the data architecture.
- **FR-008**: System MUST provide an Alembic migration to create the `users`, `unique_targets`, `user_scans`, and `scan_results` tables.

### Key Entities _(include if feature involves data)_

- **User**: A system user, identified by Auth0, with early access status and notification tokens.
- **UniqueTarget**: A de-duplicated "what" to scan (Campground + Date Range).
- **UserScan**: The "who" wants to scan a target and "how" they want to filter results (User + Target + Filters).
- **ScanResult**: The cached findings from a scan execution (Target + Campsite + Available Dates).

## Success Criteria _(mandatory)_

### Measurable Outcomes

- **SC-001**: 100% of new models have unit tests covering basic CRUD operations and constraint validation.
- **SC-002**: Database schema for new tables matches the blueprint in `DESIGN_DATA.md` with 100% accuracy.
- **SC-003**: Unique Target hashing ensures 0 duplicate records are created for the same campground and date range.
- **SC-004**: Alembic migration script completes successfully on a clean PostgreSQL environment.
