# API Abuse Prevention Research

## Authenticate the existing same-origin gateway

**Decision** · Store a credential in the Pages runtime and the backend runtime. Enforce it for all hosted API paths except health infrastructure probes.

**Rationale** · The application already uses a Pages Function to preserve host-only cookies and CSRF. Verifying a server-held credential makes the gateway a transport boundary. The gateway overwrites caller-supplied forwarding values and supplies the visitor identity from its inbound Cloudflare request, because Cloudflare can rewrite its built-in IP fields for Worker subrequests. Use a backend HTTPS host distinct from the frontend even when the latter uses a custom domain. [Cloudflare Pages secrets](https://developers.cloudflare.com/pages/functions/bindings/#secrets) · [Cloudflare request and subrequest headers](https://developers.cloudflare.com/fundamentals/reference/http-headers/#cf-connecting-ip-in-worker-subrequests).

**Alternatives considered** · CORS and fetch metadata only govern browser behavior. A value embedded in the frontend bundle is public. A Cloudflare account network rule or tunnel can add an infrastructure layer and depends on deployment access beyond this change. Public anonymous discovery must remain available through the frontend entry point.

## Use deployment-aware quota storage

**Decision** · Enforce expiring windows by a fixed category and IP or verified account. Use Valkey for distributed protected mode. Single-worker development and standalone can use bounded memory without adding a runtime service.

**Rationale** · Gunicorn and Kubernetes run multiple independent processes. Using the existing Valkey deployment allows a request handled by any worker to debit the same counter. Count and expiry are one atomic operation so concurrent admissions are coherent and failed callers cannot leave counter keys without a TTL. A failed shared store yields a temporary service error instead of bypassing protected work. [Redis window counter pattern](https://redis.io/docs/latest/commands/incr/#pattern-rate-limiter).

**Alternatives considered** · IP-only throttling cannot contain accounts across networks. User-only throttling leaves anonymous search, unsuccessful login, and authentication work unprotected. A single quota is simpler but treats a cheap catalog read like an operation that sends alerts or schedules work.

## Keep infrastructure access private

**Decision** · Retain exact ping and health routes for the existing probe callers. Keep database readiness private at both Pages and backend ingress. Use ingress restrictions for metrics exposure.

**Rationale** · Both Helm Ingress and Gateway API leave backend metrics on internal Services. Helm liveness uses `/api/ping`, readiness and startup use `/api/health`, and some workload init containers depend on the latter. Existing Nginx forwards only `/api/`; its root serves the UI and static documentation. Published development Compose ports need host, firewall or ingress restrictions when reused for production. The Pages Function only forwards API traffic.

## Bound inbound body processing

**Decision** · Limit API request bodies to 128 KiB including bodies without a valid size declaration.

**Rationale** · Current API mutations accept JSON and have no file uploads. A boundary limit constrains request buffering and parser work while preserving existing field validation. Existing public discovery already caps query strings per field and page size.

## Bound Explore offsets

**Decision** · Reject Explore offsets greater than 50,000 before database search. Advertise the browsable page count within this window and preserve the matching catalog count.

**Rationale** · Explore uses SQL offsets and reports an exact match count with each page. The catalog contains thousands of locations, so a 50,000-row offset allows ordinary browsing while bounding the cost of arbitrary pages. A visitor who reaches the limit can filter a large result set. Map membership already uses a cursor.

**Alternatives considered** · A fixed page-number ceiling would allow callers to vary the database offset by changing page size. Cursor pagination would require changes to the Explore sorting contract and frontend navigation.
