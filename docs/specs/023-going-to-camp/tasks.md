# Tasks

- [x] Specify `GoingToCampProvider` architecture, Washington State Parks scope, and remaining deployment TODOs.
- [x] Seed `WashingtonStateParks` (`id=12`) in `camply.db.data.providers` and add an immutable Alembic seed migration with downgrade protection.
- [x] Add migration, packaging, and synthetic `GoingToCamp` provider/model/CLI/VCR regression tests.
- [x] Implement `camply.providers.going_to_camp` Pydantic v2 models (`metadata.py`, `api.py`), shared `GoingToCampProvider` ABC, and `WashingtonStateParksProvider` variation.
- [x] Register `WashingtonStateParksProvider` in `camply.providers.PROVIDERS` and verify provider isolation and metadata CLI integration.
- [x] Validate live Washington State Parks metadata ingestion and availability scanning in an isolated temporary SQLite database and record [verification evidence](validation.md).
- [x] Update `DESIGN_PROVIDERS.md`, `PLAN.md`, and `CHECKLIST.md`, and pass all lint, type, test, packaging, and documentation quality gates.
- [x] Decode scalar enum attributes, correct PostgreSQL upgrade expectations, and disclose booking restrictions in results.
