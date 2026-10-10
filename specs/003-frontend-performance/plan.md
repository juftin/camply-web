# Implementation plan

1. Record passing checks and bundle sizes before changes.
2. Migrate the existing ESLint rules with the Oxlint migration tool. Use Oxfmt with an 80-column print width and ignore generated artifacts.
3. Upgrade Vite, its React plugin, Vitest, and the native compiler. Align Node versions across development, CI, Docker, and Pages.
4. Lazy-load secondary route modules and show a status fallback while they load. Keep protected route gates outside the lazy content. Catch failed page loads with a reload action and reset the error when navigating to another route.
5. Add navigation/loading coverage and verify checks, code generation, both builds, and bundle sizes. Update contributor documentation and the global checklist.

## Constitution check

- Preserve strict type checking, lint rules, and automated verification.
- Keep every workflow accessible through Task and dependencies locked with pnpm.
- Limit implementation to frontend tooling and route loading; no database or backend changes.
