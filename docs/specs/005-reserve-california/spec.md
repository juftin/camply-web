# ReserveCalifornia provider

## User stories

- Campers discover California state parks and their campgrounds in the existing search.
- Campers monitor available overnight campsites and receive links to the correct booking page.
- Operators refresh provider metadata through the existing ingestion worker.

## Requirements

- Implement the async BaseProvider interface without importing the legacy CLI.
- Use the current Tyler-hosted ReserveCalifornia RDR API, not the retired calirdr.usedirect.com host.
- Preserve upstream place, facility, and unit IDs as strings; register provider ID 2.
- Interpret scan end_date as check-out, excluding that night; bound grid requests and aggregate dates across responses.
- Return only online-bookable, free overnight inventory; exclude blocked, walk-in, locked, and lottery inventory.
- Translate provider models to CampsiteDTO, preserving equipment, minimum stays, and raw classification metadata without inventing capacity or electrical hookups.
- Refresh parks, campgrounds, and search rows idempotently and keep provider IDs isolated when upstream IDs overlap.
- Retire missing records without deleting scans, omit hidden/unbookable records from search, and commit metadata with its search index atomically.
- Surface HTTP 200 application rejections as failures and release the actual HTTP connection pool on client shutdown.
- Include deterministic synthetic regression fixtures and verify the public API separately; never store reservation identifiers or personal data in fixtures.
- Seed the provider through an Alembic data migration and document usage and validation.
- Refuse seed rollback while dependent metadata, search rows, or scan targets exist.
