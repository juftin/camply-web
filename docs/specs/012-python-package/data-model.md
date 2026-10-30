# Data and Compatibility Invariants

This feature adds no entities, columns, indexes, or state machines. It changes
Python paths and distribution metadata.

- Preserve tables, constraints, provider IDs, target identity hashing, stored
  scans, and notification eligibility behavior.
- Preserve every Alembic revision/down-revision/merge point. Update historical
  imports only as required; never squash or regenerate the revision graph.
- Resolve migrations from installed resources. Verify fresh SQLite and a
  synthetic earlier-revision database, alongside existing PostgreSQL checks.
- Preserve explicit Celery `camply.*` task names, JSON serialization, queues,
  arguments, and notification DTO defaults; Python paths become `camply.worker.*`.
- Preserve API schemas/authentication. Missing optional distributed dependencies
  use existing unavailable fields or HTTP 503, never false dispatch success.
- Preserve configuration names, SQLite data location, and database settings.

Record pre-existing SQLite migration or Python support failures separately.
Do not redesign the database; implement the explicitly approved Python 3.11
support floor and 3.14 runtime defaults without changing application data.
