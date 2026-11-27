# Research: Checklist Data Layer

**Date**: 2026-03-22
**Status**: Complete

## Decision 1: `preferred_types` Storage Strategy

- **Decision**: Use `ARRAY(String)` for `preferred_types` in `UserScan` and `JSONB` for general `filters`.
- **Rationale**: `preferred_types` is a simple list of campsite types (e.g., ["TENT", "RV"]). PostgreSQL `ARRAY` allows for efficient native filtering using the `&&` or `@>` operators. Other filters (like `min_stay_length`) will be separate columns for direct access, but any highly dynamic filters will use `JSONB`.
- **Alternatives Considered**: `JSONB` for everything was considered, but separate columns for core filters provide better indexing and type safety.

## Decision 2: `UniqueTarget` Hashing Strategy

- **Decision**: Hash = `SHA256(provider_id + campground_id + start_date.isoformat() + end_date.isoformat())`.
- **Rationale**: This combination uniquely identifies a "pollable unit". Using ISO format strings for dates ensures consistency regardless of input format.
- **Alternatives Considered**: Composite primary key on all four fields. SHA256 is preferred because it's a single, fixed-length string that's easy to index and reference.

## Decision 3: User Authentication Integration

- **Decision**: Implement the `User` model with `auth0_id` as an optional/nullable field for now, with a `username` or `email` as the primary identifier for local development.
- **Rationale**: Phase 1 (current focus) includes "Local-Only" auth mode. By making `auth0_id` nullable, we can support both modes without breaking the schema later.
- **Alternatives Considered**: Requiring Auth0 IDs from the start. This was rejected to ensure developers can run the stack offline/locally without an Auth0 tenant.

## Decision 4: Result Caching (ScanResult)

- **Decision**: `ScanResult` will store `found_at` as a timestamp and `available_dates` as a `JSONB` array of ISO date strings.
- **Rationale**: Availability data from providers often comes as a list of dates. `JSONB` allows us to store these flexibly while maintaining the ability to query them if needed.
- **Alternatives Considered**: Separate rows for every available date. Rejected due to row-explosion concerns (one poll could return 30+ dates for 100+ sites).
