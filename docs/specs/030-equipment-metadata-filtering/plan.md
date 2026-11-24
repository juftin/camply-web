# Implementation Plan: Equipment Metadata and Filtering

**Branch**: `030-equipment-metadata-filtering` | **Date**: 2026-11-16 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from [docs/specs/030-equipment-metadata-filtering/spec.md](spec.md)

## Summary

Populate normalized campground amenity and RV-length capabilities during provider catalog ingestion so Explore filters (`electric`, `pets`, `rv`, plus new `ada_accessible` parity) return accurate campground and aggregated recreation-area results (`T3.2.1b`), and add site-level equipment/vehicle-length and ADA accessibility filtering across saved scans, shared-target polling, API responses, alert revalidation, and the React UI (`T3.2.2`).

## Technical Context

**Language/Version**: Python >=3.11 (default 3.14) backend; TypeScript (React 18 + Vite 8) frontend
**Primary Dependencies**: FastAPI, Pydantic v2, SQLAlchemy 2 (async) + Alembic, TanStack Query, React Hook Form + Zod, Shadcn/UI
**Storage**: SQLite (base/standalone) and PostgreSQL (distributed `postgres` extra) via shared SQLAlchemy models & Alembic migrations
**Testing**: `pytest` + `pytest-vcr` / synthetic `httpx2.MockTransport` (backend), `vitest` + Testing Library + Playwright visual snapshots (frontend)
**Target Platform**: Linux/macOS/Windows base Python package, Docker/Kubernetes distributed deployment, Cloudflare Pages frontend
**Project Type**: Full-stack web application (`src/camply/` + `src/frontend/`)
**Performance Goals**: Zero additional per-subscriber upstream provider polls; catalog metadata ingestion remains atomic per provider with bounded network calls
**Constraints**: Base package (`camply.providers`, `camply.db`, `camply.cli`) must remain free of `server`, `distributed`, `postgres`, and `sentry` dependencies (enforced by Import Linter); SQLite and PostgreSQL schemas/queries must stay portable
**Scale/Scope**: 26 registered providers across 4 provider families (`RecreationGovProvider`, `UseDirectProvider`, `GoingToCampProvider`, `ReserveAmericaProvider`)

## Constitution Check

_GATE: Must pass before Phase 0 research. Re-check after Phase 1 design._

1. **I. Reliability & Precision**: PASS — Equipment length and accessibility filters fail closed on unknown metadata (`max_vehicle_length is None` or `is_accessible is not True`) and floor fractional/metric upstream lengths conservatively so users never receive false-positive alerts. Pending outbox notifications re-check current scan preferences before send.
2. **II. Type Safety & Static Analysis**: PASS — All new DTO/model/schema fields are strictly typed in Python (`mypy`) and regenerated into TypeScript (`task api:generate` / `tsc`), with `ruff`, `oxlint`, and `oxfmt` enforced.
3. **III. Modern Workflow & Automation**: PASS — All verification runs through `task` entrypoints (`task check`, `task api:check`, `task test`, `task docs:check`, `task snapshot:check`).
4. **IV. Monorepos & Separation of Concerns**: PASS — Normalization and ingestion stay inside `camply.providers` and `camply.db`; `worker` and `server` share `camply.db.availability.matches_scan_filters`; Import Linter contracts remain intact.
5. **V. Automated Verification**: PASS — TDD regressions required for migrations (SQLite + PostgreSQL), all 4 provider families, `matches_scan_filters`, API validation/PATCH semantics, worker outbox revalidation, frontend components, and visual baselines.

## Project Structure

### Documentation (this feature)

```text
docs/specs/030-equipment-metadata-filtering/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── checklists/
│   ├── requirements.md
│   └── filtering.md
├── contracts/
│   └── equipment-filtering.md
└── tasks.md
```

### Source Code (affected areas)

```text
src/camply/
├── db/
│   ├── availability.py                        # Shared filter matching (min_rv_length, require_accessible)
│   ├── migrations/versions/                   # Additive Alembic migration for campgrounds, scan_results, user_scans
│   └── models/
│       ├── campgrounds.py                     # Discovery capability columns
│       ├── scan_results.py                    # permitted_equipment, max_vehicle_length
│       ├── search.py                          # ada_accessible filter on Search.search()
│       └── user_scans.py                      # min_rv_length, require_accessible preferences
├── providers/
│   ├── base.py                                # populate_search_table copying & area aggregation
│   ├── dto.py                                 # CampsiteDTO.permitted_equipment, max_vehicle_length
│   ├── utils.py                               # Shared length parsing/flooring & equipment helpers
│   ├── recreation_gov/                        # RIDB campsite/attribute/equipment aggregation + site length
│   ├── usedirect/                             # AvailabilityUnit.VehicleLength + facility enrichment promotion
│   ├── going_to_camp/                         # Resource equipment/length extraction + category/attribute discovery
│   └── reserve_america/                       # Site attribute length/equipment extraction + facility amenities
├── server/
│   ├── routers/scans.py                       # Persist/update min_rv_length & require_accessible; invalidate stale intents
│   ├── routers/search.py                      # Expose ada_accessible filter across explore list/map endpoints
│   └── schemas.py                             # Request/response schemas & validation (1..200 ft)
└── worker/engine/
    ├── alerts.py                              # Pass is_accessible, max_vehicle_length in matching_opening
    ├── area_alerts.py                         # Carry site capability fields in area summary/direct candidates
    └── scanner.py                             # Persist permitted_equipment & max_vehicle_length on ScanResult

src/frontend/
├── lib/
│   ├── api.ts                                 # Explore ada_accessible param + generated schema wiring
│   ├── api/generated/schema.ts                # Regenerated via task api:generate
│   └── structs.ts                             # Scan/Search/Result types
├── components/
│   ├── FoundCampsites.tsx                     # Display permitted equipment & max vehicle length on site rows
│   ├── ScanCard.tsx                           # Preference badges for RV length & ADA requirement
│   └── ScanForm.tsx                           # RV length (1-200 ft) & ADA accessible controls + validation
└── pages/
    ├── ScanDetail.tsx                         # Preference summary & capability details
    └── SearchPage.tsx                         # ADA filter chip/toggle synced with URL & map
```

## Architecture & Phase Design

### Phase 0: Research & Provider Mapping

Completed in [research.md](research.md). Key takeaways:

- Explore (`search` table + `SearchPage.tsx`) already has schema/UI for `electric`, `pets`, and `rv`, but `BaseProvider.populate_search_table` inserts defaults because `Campground` has no capability columns.
- `CampsiteDTO` and `ScanResult` already carry `campsite_type`, `is_electric`, and `is_accessible`, requiring only `max_vehicle_length` and `permitted_equipment` additions plus consistent extraction across all four provider families.
- `UserScan` preferences (`min_rv_length`, `require_accessible`) stay outside `definition_hash` and `UniqueTarget.hash`, preserving shared polling deduplication.

### Phase 1: Design & Contracts

Completed in [data-model.md](data-model.md), [contracts/equipment-filtering.md](contracts/equipment-filtering.md), and [quickstart.md](quickstart.md).

**Post-Design Constitution Check**: Re-verified all five principles after finalizing `data-model.md` and `contracts/equipment-filtering.md` — no optional dependency leaks (`camply.db` / `camply.providers` stay base-only), no dialect-only SQL in `BaseProvider.populate_search_table` (aggregation works identically on SQLite and PostgreSQL), and full OpenAPI/TypeScript contract alignment.
