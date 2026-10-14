# Runtime and launch contract

Proposed interfaces for implementation; standalone commands are not available yet.

## Configuration

| Setting                     | Contract                                                                    |
| --------------------------- | --------------------------------------------------------------------------- |
| `CAMPLY_RUNTIME_MODE`       | `distributed` (default) or `standalone`; independent of auth/environment.   |
| `CAMPLY_DB_DRIVERNAME`      | Standalone requires `sqlite+aiosqlite`; reject PostgreSQL/in-memory SQLite. |
| `CAMPLY_DB_HOST`            | Preserve existing SQLite path config; test absolute file paths.             |
| `CAMPLY_FRONTEND_DIR`       | Optional absolute built-asset directory; otherwise packaged assets.         |
| `CAMPLY_HEARTBEAT_INTERVAL` | Existing 300-second default; validate > 0.                                  |
| `CAMPLY_TARGET_COOLDOWN`    | Existing 55-second default; validate > 0.                                   |
| Auth/session settings       | Existing meaning/secure defaults; configure frontend origin explicitly.     |

Standalone does not construct broker/Prometheus clients. Missing `index.html`, unreadable assets, unwritable database, invalid settings, and conflicting worker settings fail before serving. Supported launch uses one Uvicorn worker without production reload. A second instance sharing the database is unsupported.

## Task / launcher

- `task standalone:install`: Install backend core and frontend build tools without infrastructure extras or all-workspace sync.
- `task standalone:build`: Build root assets with relative `/api`, stage in `backend/packages/backend/backend/static`, and build existing workspace package wheels into `backend/dist` without Docker. Include assets in the backend wheel.
- `task standalone:run`: Select standalone, apply Alembic, validate resources, and invoke `python -m backend.standalone` on port 8000.
- `task standalone:test`: Verify an isolated core install and service-free browser flow; development tools are test-only.
- `python -m backend.standalone`: Prepared-artifact launch without Task/Node, with equivalent migrations/lifecycle, one worker, and loopback bind by default. Owners can explicitly configure another host.

Core dependencies: backend → worker/db/providers; worker → db/providers; providers → db. Root distributed extras activate backend/worker Celery/Redis/Prometheus and db psycopg extras. Existing install/tasks/Compose explicitly select distributed extras; installed wheels cannot rely on workspace paths.

## Static routing

- `/api` and `/api/...` retain API routing/errors.
- `/metrics` and descendants return 404 standalone, never SPA fallback.
- Actual assets serve files inside the built directory only; missing assets return 404.
- GET/HEAD HTML navigation deep links receive `index.html` after reserved routes. Non-navigation requests do not receive SPA HTML; unsupported methods retain 405. Reject traversal outside assets.
- Fingerprinted assets cache immutably; entry HTML revalidates.
- Distributed retains separate hosting and metrics.

## Common engine boundary

Typed async functions receive explicit sessions/configuration and return typed results or classified failures. No broker, decorators, locks, or metrics imports. Standalone persists intents with results; Celery adapters dispatch existing tasks. Adapters own locking/retry/operational recording.
