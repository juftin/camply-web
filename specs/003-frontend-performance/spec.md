# Frontend tooling and route performance

## User stories

- Contributors run fast linting, formatting, type checks, builds, and tests through existing Task commands.
- Visitors download page-specific code when opening a route, with an accessible loading state and unchanged authentication/invitation behavior.
- Maintainers build the same application locally, in CI, in Docker, and on Cloudflare Pages.

## Requirements

- Replace ESLint and Prettier with Oxlint and Oxfmt while preserving existing lint rules and formatting conventions.
- Upgrade to Vite 8 and native TypeScript 7; retain compiler API compatibility for OpenAPI generation.
- Split secondary routes with React lazy loading and Suspense; keep the home page eager.
- If a route chunk fails to download, show an accessible error with a reload action and preserve navigation to other pages.
- Verify existing tests, new navigation regressions, static/Docker builds, and the reduction in initial JavaScript bytes.
- Keep backend behavior, public APIs, and authentication rules unchanged.
