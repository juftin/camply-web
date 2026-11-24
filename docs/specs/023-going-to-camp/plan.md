# Implementation plan

1. Audit legacy `going_to_camp` assumptions against live GoingToCamp deployments (`washington.goingtocamp.com` and cross-deployment checks) to verify catalog endpoints (`/api/transactionlocation`, `/api/resourceLocation`), dynamic booking/resource category enums, bulk resource metadata (`/api/resourcelocation/resources`), daily map availability (`/api/availability/map`), equipment/attribute schemas, and booking deep links.
2. Add permanent provider identity `WashingtonStateParks` (`id=12`) in `camply.db.data.providers` and create an immutable Alembic seed migration with dependent-data downgrade protection on SQLite and PostgreSQL.
3. Implement Pydantic v2 metadata and inventory models in `camply.providers.going_to_camp.models` (`metadata.py` and `api.py`) for localized text extraction, coordinate/region normalization, dynamic overnight category resolution, multi-category equipment lookup, filterable attribute decoding, and `CampsiteDTO` translation.
4. Implement `GoingToCampProvider(BaseProvider, ABC)` in `camply.providers.going_to_camp.provider` with paced async requests over the shared retry/circuit-breaker transport, per-instance metadata caching, bounded 60-day map availability traversal with loop-map pruning and cycle guards, and transactional park/campground/search ingestion.
5. Implement `WashingtonStateParksProvider` in `camply.providers.going_to_camp.variations`, register ID `12` in `camply.providers.PROVIDERS`, and record remaining GoingToCamp deployments in [provider TODOs](TODO.md).
6. Add synthetic unit, database, CLI, VCR replay, packaging, and Alembic migration tests; verify live metadata sync and availability scanning against an isolated temporary SQLite database outside the repository; run all Task quality gates and update architecture/checklist documentation.

## Constitution check

- Shared provider logic is re-engineered async-first (`httpx.AsyncClient`) with zero imports from legacy synchronous CLI modules or optional server/worker extras.
- Strict Pydantic v2 models, `CampsiteDTO` boundaries, numpy docstrings, Import Linter boundaries, and `Taskfile.yaml` workflows are preserved.
- Multi-deployment GoingToCamp mechanics live once in `GoingToCampProvider`; concrete variations declare only deployment identity, host URLs, and location fallbacks.
- Specifications and synthetic behavior tests drive implementation, while live probes validate upstream contract realities without committing live reservation payloads.
