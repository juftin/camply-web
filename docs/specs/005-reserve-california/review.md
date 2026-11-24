# Provider integration review

Reviewed the adapter, shared retry transport, metadata/database/search lifecycle, API discovery and scan creation, frontend provider selection, heartbeat scheduling, scanner filtering, results persistence, and notification payloads.

## Confirmed and fixed

- **Application errors were successful empty scans.** A live invalid FacilityId request returned HTTP 200, a matching empty Facility object, and `NightsActual=0`. It now raises before the worker can replace cached results. A synthetic regression reproduces this response.
- **Hidden and unbookable records appeared in search.** Search index statements ignored enabled/reservable flags. Parks now require enablement, and campgrounds require both flags; hidden parks also make their campgrounds unreservable. Metadata tests include offline and hidden records. A shared search regression preserves discovery of nonreservable parks with bookable campgrounds, as park-level reservability has a different meaning on Recreation.gov.
- **Removed upstream records stayed active.** Successful catalog refreshes now disable provider records before reactivating those still present, preserving IDs and scan references.
- **Search failures left partially refreshed metadata.** Metadata and search originally committed in separate transactions. Injecting a search failure reproduced changed metadata with an old index. They now commit together; the rollback regression verifies the previous park name survives a failed refresh.
- **Client cleanup leaked the real connection pool.** RetryTransport delegated requests to an inner AsyncHTTPTransport but inherited cleanup closed only the unused outer transport. A failing lifecycle test confirmed this; cleanup now closes both.
- **Seed rollback could orphan SQLite data.** SQLite does not enable foreign keys in the existing database configuration. The old downgrade deleted provider identity even after ingestion. It now explicitly rejects dependent rows, with empty- and populated-catalog migration regressions.

## Remaining shared-system gaps

1. **Provider minimum-stay rules do not affect notification eligibility.** `worker/tasks/scanner.py::_matches_scan_filters` only uses the user's minimum. A synthetic DTO with one free night and provider `MinStay=3` still qualifies for a user requesting one night. Provider rules must be applied to consecutive arrival blocks, including across grid boundaries; blindly applying the largest minimum to every date would be incorrect.
2. **Provider request limits and filter caching do not span polls or workers.** Each scanner task constructs a new provider, resetting its limiter and filters cache. Concurrent targets can exceed one request per second collectively and repeatedly download identical filters. A shared provider request budget and persistent metadata cache need a separate worker design.
3. **Expired and disabled targets keep polling.** Heartbeat checks active subscriptions and cooldown only. It does not stop at check-out or inspect provider/campground enablement, so retired targets can keep retrying and expired scans keep making requests.
4. **Dashboard results lose campsite display names.** DTO names reach notifications, but ScanResult stores only IDs and dates; the detail endpoint leaves campsite_name empty. ReserveCalifornia unit IDs differ from displayed site numbers, so dashboard users see internal IDs. Persisting names requires a data-model/API follow-up.
5. **A complete individual-campsite catalog is not persisted.** Independent metadata sync imports parks and facilities only. DESIGN_DATA proposes a `campsites` table, but no such model or migration exists. Unit metadata is parsed during availability scans, and filter dictionaries are cached only in the provider instance. Supporting full site-level metadata ingestion requires that shared schema and a provider-specific catalog ingestion path.
6. **Worker startup does not bootstrap metadata.** The ingestion module previously documented startup refreshes, but worker initialization only starts metrics, and the container entrypoint only runs migrations. The automatic refresh is scheduled at midnight UTC by Celery Beat. A fresh database needs manual ingestion or the next scheduled run; the provider docs now reflect that behavior.

## Live scope

The current API was checked for ordinary campgrounds, invalid facility IDs, lodging inventory, pooled Oceano Dunes inventory, and requests beyond the booking horizon. Lodging and Oceano units also use `UseType=4`; no provider-specific frontend branching is required. Test fixtures remain synthetic. Production PostgreSQL, a real Celery/Valkey deployment, and notification delivery were not exercised during this review.
