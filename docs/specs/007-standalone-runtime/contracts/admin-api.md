# Admin API contract additions

Keep existing routes, authorization/CSRF, pagination, and generated OpenAPI types. These changes are implemented and covered by local and distributed regression checks.

## GET /api/admin/operations

Extend `AdminOperationsResponse` with:

| Field              | Type / behavior                                                                         |
| ------------------ | --------------------------------------------------------------------------------------- |
| `runtime_mode`     | `standalone` or `distributed`; default distributed for existing fixtures.               |
| `capabilities`     | Booleans `broker`, `historical_trends`, `persistent_job_history`; all false standalone. |
| `scheduler_status` | `running`, `stopping`, `failed`, or null; null distributed.                             |

Make `broker_connected` nullable: standalone returns null, not a false outage. `workers` identifies the local runner. Known active/pending work counts are actual values; unsupported Celery reserved/scheduled concepts remain null. `queue_depth` describes pending local work including due alerts, with corresponding UI labels. Keep `last_discovery` shape.

Selected-runtime inspection/history availability determine `inspection_available`, `telemetry_available`, `stale`, and errors. Real runner failure is unhealthy; absent capabilities are intentional. Unknown is not zero; measured empty is zero. Existing admin denial remains.

## Recent task endpoints

Keep `GET /api/admin/operations/tasks` and `GET /api/admin/operations/tasks/{task_id}` response shapes/filters. Local history follows [data-model.md](../data-model.md), with stable job IDs, distinct event IDs, and one-based attempts. Unknown/pruned job IDs return 404. UI explains 1,000-record/24-hour retention and clearing on restart. Durable pending alert state is independent.

## POST /api/admin/operations/sync-providers

Keep existing response status and `AdminSyncProvidersResponse` fields `task_id`, `status`, `message`. Return promptly with local job ID; repeated requests during refresh return that ID and an already-running message. Sync registered providers sequentially and record each failure while continuing. Dispatch errors use mode-appropriate text. Distributed keeps existing Celery dispatch.

## GET /api/admin/trends

Standalone returns HTTP 200 using existing `AdminTrendsResponse`: `available=false`, empty `metrics`, null last-success time, and fixed intentional-disabled explanation. Retain requested group/range and valid timing fields. No Prometheus query or invented successful cache. Frontend fetches capabilities before starting trend queries. Distributed trends/outage behavior stays unchanged.

## Health / security

`GET /api/ping` remains liveness. Standalone `/api/health` checks initialized storage and supervised runner: existing `ApiStatus` with actual HTTP/body 200 when ready or 503 when unhealthy, without leaking paths/errors. Distributed behavior stays unchanged.

Authentication selection remains independent. Same-origin login retains trusted-origin checks and signed-cookie/CSRF handling. Configure the exact frontend origin; HTTP-only local sessions need an explicit secure-cookie override.
