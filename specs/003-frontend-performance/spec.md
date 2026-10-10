# Frontend tooling performance

## User stories

- Contributors run fast linting, formatting, type checks, builds, and tests through existing Task commands.
- Visitors retain the existing eager page loading, navigation, and authentication/invitation behavior.
- Maintainers build the same application locally, in CI, in Docker, and on Cloudflare Pages.

## Requirements

- Replace ESLint and Prettier with Oxlint and Oxfmt while preserving existing lint rules and formatting conventions.
- Upgrade to Vite 8 and native TypeScript 7; retain compiler API compatibility for OpenAPI generation.
- Keep all page imports eager and avoid route-level loading states or chunk recovery code.
- Verify existing tests, static/Docker builds, and tooling performance against the original baseline.
- Keep backend behavior, public APIs, and authentication rules unchanged.
