# Installation Contract

These contracts are verified by isolated installation tests. No new Camply
CLI is introduced.

## Python Compatibility

Published metadata declares `Requires-Python: >=3.11`. Development, primary
CI, Docker, and release fixtures default to Python 3.14. Explicit compatibility
jobs run backend tests and artifact checks on 3.11; the isolated installation
matrix also runs on 3.14. These jobs must select their intended interpreter
explicitly so the development pin does not override minimum-version checks.
Ruff and mypy retain the Python 3.11 language/API floor.

| Selection     | Must work                                                                        | Must not require                                     |
| ------------- | -------------------------------------------------------------------------------- | ---------------------------------------------------- |
| Base          | Root/providers/db imports, migration resources, SQLite, existing population help | FastAPI, Uvicorn, Celery, Redis, psycopg, Sentry     |
| `server`      | ASGI/OpenAPI, API startup and SQLite-backed routes                               | Celery, Redis, PostgreSQL, Sentry, broker at startup |
| `distributed` | Celery import, existing task registration and worker tests                       | FastAPI, Uvicorn, Gunicorn, PostgreSQL, Sentry       |
| `postgres`    | Configured PostgreSQL connection with psycopg                                    | Server or worker packages                            |
| `sentry`      | Existing integrations when combined with appropriate runtime extras              | Unselected runtime dependencies                      |
| Combined      | Existing distributed API/worker/beat behavior                                    | Old generic sibling distributions                    |

## Existing Entry Points

- `populate-database`: `camply.providers.cli:populate_database`, same flags.
- ASGI: `camply.server.app:app`.
- Celery: `camply.worker.celery_app:celery_app`; use this explicit path in tooling.
- OpenAPI: `python -m camply.server.openapi`, same options.
- Admin provisioning: `python -m camply.server.provision`, same options.
- No `camply` console script, scan command, or serve command is added.

## Missing Optional Capabilities

Server-only starts/generates OpenAPI. Operations overview/task lists report
unavailable through existing fields; task detail and provider-sync dispatch
return HTTP 503 with a distributed-installation hint. Authorization remains
enforced. Full installations retain existing service-outage handling.

Selecting PostgreSQL without its driver or a Sentry DSN without its SDK gives
a precise installation hint at feature use/startup, without breaking base
imports. Do not catch unrelated import failures inside installed packages.

Server-only means API serving, not a local scanning scheduler or bundled site.
Scheduled scans still need workers/beat. Extras neither start services nor
select an execution mode.

## Artifacts

`task dist` produces `camply-<version>.tar.gz` and a matching wheel; GitHub
releases attach both. The sdist rebuilds without other repository directories.
Both wheel paths include code, `py.typed`, migrations/templates, license
metadata, and accurate extra metadata. Old top-level import packages disappear.
