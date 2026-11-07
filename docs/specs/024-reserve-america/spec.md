# ReserveAmerica provider

Users can discover native ReserveAmerica overnight campgrounds, select dates, and receive site-level availability through the existing worker and notifications. Catalog ingestion must exclude external listings and day-use-only facilities, preserve stable contract-scoped IDs, and refresh search atomically. Scans must paginate every site and aggregate daily AVAILABLE statuses across bounded windows with exclusive checkout. HTTP, auth, schema, and pagination failures must raise rather than publish partial availability or catalog data.

Acceptance: synthetic HTTP integration tests cover pagination, date clipping, filtering, failures, attributes, session refresh, database refresh, registry, and migration lifecycle. No account credentials or session tokens enter fixtures.
