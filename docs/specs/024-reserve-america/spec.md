# ReserveAmerica provider

Users can discover native ReserveAmerica overnight campgrounds, select dates, and receive site-level availability through the existing worker and notifications. Catalog ingestion must exclude external listings and day-use-only facilities, preserve stable contract-scoped IDs, and refresh search atomically. Scans must paginate every site and aggregate daily AVAILABLE statuses across bounded windows with exclusive checkout. HTTP, auth, schema, and pagination failures must raise rather than publish partial availability or catalog data.

Acceptance: synthetic HTTP integration tests cover pagination, date clipping, filtering, failures, attributes, session refresh, database refresh, registry, and migration lifecycle. No account credentials or session tokens enter fixtures.

Session reliability: every API request must mirror only applicable, unexpired token cookies into authentication headers. Cookie rotation/deletion must take effect on the next request. Refresh once on HTTP 401; if the retry is still unauthorized, invalidate the session so the next operation bootstraps first. Serialize concurrent callers. No proactive expiry timer or generic 403 refresh is required without provider evidence.
