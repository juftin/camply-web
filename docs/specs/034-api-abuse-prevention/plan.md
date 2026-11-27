# Implementation Plan: API Abuse Prevention

**Feature** · 034 API Abuse Prevention | **Date** · 2026-11-24 | [Specification](spec.md)

## Summary

Use the existing Cloudflare Pages same-origin gateway as the hosted entry point and authenticate its HTTPS requests at the API boundary. Apply shared Valkey quotas to protected distributed deployments, with bounded in-process counters for standalone and single-worker direct development. Do the cheapest checks before parsing, database work, or third-party calls. Bound the request body in the same boundary layer. Keep existing user authorization and private monitoring topology.

## Technical Context

- **Language and runtime** · Python 3.11 minimum (3.14 default), TypeScript Pages Functions, Cloudflare edge and Linux backend.
- **Dependencies** · FastAPI and ASGI, Pages runtime bindings, existing optional Redis client and Valkey, pytest and Vitest. No database schema changes.
- **Performance** · One short, atomic shared-store operation per applicable budget. Bound shared-store failure latency and local counter cardinality. API body buffering cannot exceed the application ceiling by more than the current ASGI receive chunk.
- **Scope** · API-boundary checks, tested side-effect quotas, settings and deploy wiring. Keep standalone and existing Vite/Nginx direct paths. Existing worker cadence and providers stay independent.

## Constitution Check

- **I. Reliability & Precision** · Protective controls leave provider result matching, polling and notification timing unchanged. Exact probes preserve monitoring.
- **II. Type Safety & Static Analysis** · Run repository Python and frontend type and lint gates, including import contract checks.
- **III. Modern Workflow & Automation** · Use existing Task, uv, and Pages verification commands. Production uses runtime-managed secrets.
- **IV. Separation of Concerns** · The frontend server handles forwarding, the API validates provenance and quotas, and existing auth dependencies handle user access. Keep Valkey imports optional within the server boundary.
- **V. Automated Verification** · Use synthetic fixtures at gateway and API entry points, including shared accounting, auth boundaries, body handling and probe exemptions.

## Project Structure

```text
docs/specs/034-api-abuse-prevention/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── contracts/http.md
├── quickstart.md
└── tasks.md
src/camply/server/
├── app.py
├── config.py
├── auth.py
└── API protection and rate accounting
src/frontend/
├── functions/api/[[path]].ts
├── test/pages-proxy.test.ts
└── tooling/verify-pages.ts
tests/
docker-compose.yaml
deploy/helm/
```

## Phase 0 · Research

See [research](research.md) for the trust and deployment decisions.

## Phase 1 · Design

1. Make the Pages Function require a runtime-only, minimum 32-character secret and use a configured distinct HTTPS backend origin. Replace inbound proxy credential and client IP with trusted values. Preserve method, body, session credentials, same-origin redirects, and cache prevention. Reject explicit cross-origin browser context.
2. Have the backend enforce `CAMPLY_API_PROXY_REQUIRED` with `CAMPLY_API_PROXY_SECRET` and require session or Auth0 user authentication in that profile. Apply the check to `/api` and `/api/*` before CORS, authentication, and handlers, except exact `GET`/`HEAD` liveness and readiness. Use a constant-time credential comparison and validate the gateway client IP. Direct operation never accepts caller-provided private headers as rate identity.
3. Use closed route categories and normalized client network identity for public and pre-authentication quotas. Apply account quotas after verifying the current user and before mutation or external work. Do not key on a submitted login, a raw token, query string, or a resource ID. Account and IP policies may both apply to the same request.
4. Use short-lived atomic counters in Valkey for protected distributed mode and process-local bounded counters for single-worker deployments. On store outage respond temporarily unavailable and leave probes independent. Select quota storage using `CAMPLY_API_RATE_LIMIT_STORAGE` and the runtime profile.
5. Enforce a 128 KiB request body before parsing. Reject early from declared size when possible and enforce the same ceiling for streamed data. Keep actual response shapes in [HTTP contract](contracts/http.md) and counter semantics in [data model](data-model.md).
6. Supply the staged deployment, secret, monitoring, and test instructions in [quickstart](quickstart.md) and the operation guides. Complete tests and verify against the [tasks](tasks.md).
7. Keep Prometheus HTTP labels bounded using registered route templates and fallbacks for unmatched paths and unsupported methods.
8. Bound Explore's SQL offset to 50,000, return HTTP 422 before deeper queries, and cap the advertised page count to the accessible range. Match counts and map cursor pagination keep their current meaning.

The Phase 1 design satisfies the Constitution Check and introduces no exceptions.
