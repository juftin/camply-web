# Shared camply container

## Requirements

- Publish one application image, `ghcr.io/juftin/camply`, containing Python, Nginx, the complete installed wheel, and all runtime extras.
- Run API, frontend, Celery worker, and beat as separate containers from this image using command overrides. Preserve the API default command.
- Add `camply frontend dir` to print the absolute installed static directory without server dependencies or startup side effects. Report missing bundled assets clearly.
- Configure Nginx to serve that directory directly, preserving SPA fallback, asset caching, health checks, and the API proxy.
- Nginx and CLI roles must start without database migrations. Preserve API migrations and the existing worker/beat skip setting.
- Preserve external PostgreSQL, Valkey, and Prometheus services, application storage, frontend build settings, and release tag/version rules.
- Publish each release under four image tags: the major version (`v1`), full version (`v1.2.3`), seven-character release commit SHA, and `latest`.

## Acceptance

Render Compose and publication plans to verify one application image and build configuration across roles. Verify CLI behavior in clean base-package installations, entrypoint dispatch, and real Nginx HTTP responses from the shared runtime. The final image runs as `camply` and contains no Node tooling.
