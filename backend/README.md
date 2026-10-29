# camply Python package

The backend builds one `camply` distribution from `src/camply/`. Python >=3.11
is supported; development, primary CI, Docker, and release tooling default to
Python 3.14. Ruff and mypy retain the 3.11 compatibility floor.

## Modules and optional dependencies

| Installation          | Capability                                                                                 |
| --------------------- | ------------------------------------------------------------------------------------------ |
| `camply`              | Providers, database models, SQLite persistence, Alembic resources, and `populate-database` |
| `camply[server]`      | Existing FastAPI application and HTTP serving dependencies                                 |
| `camply[distributed]` | Existing Celery worker/beat and Redis client dependencies                                  |
| `camply[postgres]`    | Psycopg PostgreSQL driver                                                                  |
| `camply[sentry]`      | Optional error reporting SDK                                                               |

Extras are additive dependency selections; every wheel contains all modules.
They do not provision databases, brokers, or processes. For the existing full
stack, select `camply[server,distributed,postgres,sentry]`; a worker-only
installation can select `camply[distributed,postgres,sentry]` without FastAPI.

These examples describe locally built artifacts; this migration does not
publish to PyPI. Build from the repository root with `task dist`, then install
the wheel with the desired extras:

```bash
uv pip install 'dist/camply-0.1.0-py3-none-any.whl[server]'
uvicorn camply.server.app:app --host 127.0.0.1 --port 8000
```

Substitute the actual artifact version. For Python API use, import
`camply.providers` and `camply.db`. The existing population utility is retained:

```bash
populate-database --help
populate-database --provider-id all
python -m camply.db.migration
```

The migration command upgrades the configured database to its current head
using installed package resources, independently of the working directory.
`CAMPLY_DB_*` configuration names and SQLite defaults are unchanged. Missing
PostgreSQL or Sentry dependencies produce installation hints when configured.

The future local Camply CLI is not implemented: there is no new `camply`
command. An API-only installation can serve browsing and scan-management
routes, but does not execute scheduled scans. Worker/beat and Valkey/Redis
remain required for polling. Without `distributed`, operations reads report
unavailable; task detail and provider dispatch return HTTP 503 while retaining
authorization. The frontend is built and hosted separately.

## Development and verification

From the repository root:

```bash
task install
task backend:test
task backend:packaging:test
task backend:packaging:test PACKAGING_PYTHON=3.11
task backend:lint
task backend:imports
task backend:check
```

Development sync selects all extras. Tests live under `tests/{db,providers,
server,worker}`. The dedicated packaging suite builds a wheel and sdist,
rebuilds a wheel from the standalone sdist, and installs each into temporary
uv environments without development dependencies or editable source paths.
It checks base and independent optional capabilities using synthetic data and
mocked external integrations. `task test` includes this suite once.

Import Linter contracts in `pyproject.toml` enforce independent server/worker
layers above providers, persistence, and shared metadata. Base code cannot
import optional runtime dependencies, and workers cannot import server-only
dependencies. The root initializer stays lightweight. Only the existing
guarded operations service may import Celery/Redis from the server; unused
exceptions fail the check. Sentry imports stay in the two guarded runtime
initialization modules. New top-level modules require explicit layer
placement. Keep `__init__.py` markers in source directories so they are scanned.

Run `task backend:imports` directly, or use `task lint`/`task backend:lint`, which
include it. CI's existing lint job and the local pre-commit import architecture
hook enforce the same contracts. Static checks complement the installed-extra
tests, which verify conditional imports and actual dependency installation.

## Import migration and deployment

Old top-level imports are removed: `backend.*` becomes `camply.server.*`,
`db.*` becomes `camply.db.*`, `providers.*` becomes `camply.providers.*`, and
`worker.*` becomes `camply.worker.*`. Update direct Python consumers and custom
Uvicorn/Celery commands. Celery wire names, database revision identities, API
contracts, provider IDs, and configuration keys remain unchanged.

Before deploying, stop beat, drain active tasks, back up the database, then
replace API, worker, and beat together. Apply the existing migration chain;
do not squash or recreate it. Rollback restores code/images without rewriting
database history. See [release operations](../docs/agents/RELEASES.md).
