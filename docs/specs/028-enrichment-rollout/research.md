# Rollout diagnosis

Read-only public production checks on 2026-11-14 confirmed backend version 2.20.0 and the destination-details schema. Many Glacier (`251869`), Upper Pines (`232447`), Yosemite (`2991`), and Anza-Borrego (`2`, provider 2) returned `details: null`. Earlier Recreation.gov IDs (`10000305`, `10001419`, `10004152`) had successful snapshots from the same startup sync; California campground `335` had a photo. No production credentials or database access were used.

The previously downloaded RIDB archive contains eight `Asset` image records for Many Glacier and 4,969 enabled/reservable campground records. Existing selection sorts never-attempted campground IDs first, takes at most 100 combined destinations, and exits after that batch. Only daily/full catalog sync called enrichment, leaving many thousands of destinations waiting days or weeks. This reproduces the symptom without an API, migration, or gallery error.

**Decision**: Discover enrichment independently each heartbeat and continue successful batches, preserving existing limits and claims. Both worker runtimes need the fix. Query due work before creating a provider client so fresh/unsupported providers need no network request.

**Alternatives rejected**: Increasing the batch cap violates the original resource bound; repeatedly syncing whole catalogs wastes network and database work; fetching details during page reads couples public requests to provider availability; a one-time migration backfill cannot maintain seven-day freshness or recover later failures.

**Limits**: No cluster context is configured, so worker logs and production administration are unavailable. Public checks establish the missing-backfill defect and partial rollout; they do not establish every provider's current coverage.
