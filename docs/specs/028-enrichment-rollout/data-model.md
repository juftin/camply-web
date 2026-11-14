# Existing persistence

No schema changes. Continue using `campgrounds.details`, `recreation_areas.details`, their embedded UTC `fetched_at`, and `details_attempted_at`.

Due work: enabled destinations with absent or older-than-seven-day snapshots and no attempt in the last hour; campgrounds must be reservable. Successful batches move snapshots to fresh; failed/missing source records retain prior data and enter the existing attempt cooldown.

Internal batch results contain provider ID/name, a success/skip/error status, and a boolean indicating successful work may continue. No public API fields change.
