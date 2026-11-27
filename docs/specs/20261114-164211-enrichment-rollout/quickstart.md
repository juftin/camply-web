# Verification

Run `task backend:test -- tests/providers/test_enrichment_refresh.py tests/worker/test_ingestion.py tests/worker/test_celery_app.py tests/worker/test_runtime.py` for focused regression coverage, then `task fix`, `task lint`, `task check`, and `task test`.

After deployment, restart/update both worker and scheduler roles. Periodic enrichment should start within one heartbeat (normally five minutes) and continue through the backlog without repeated catalog syncs. Existing snapshots remain usable during processing. Confirm Many Glacier's public cached detail response gains `details` and photo URLs once its source batch completes; check task/log outcomes if the source is unavailable.

No additional migration or operator database write is needed. The existing `camply db metadata` CLI remains a one-batch invocation when no background runtime is running.
