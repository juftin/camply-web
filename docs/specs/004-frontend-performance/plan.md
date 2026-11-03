# Implementation plan

1. Record passing checks and bundle sizes before changes.
2. Migrate the existing ESLint rules with the Oxlint migration tool. Use Oxfmt with an 80-column print width and ignore generated artifacts.
3. Upgrade Vite, its React plugin, Vitest, and the native compiler. Align Node versions across development, CI, Docker, and Pages.
4. Preserve eager page imports and the existing routing/authentication behavior.
5. Verify checks, code generation, both builds, navigation, and tooling performance. Update contributor documentation and the global checklist.

## Constitution check

- Preserve strict type checking, lint rules, and automated verification.
- Keep every workflow accessible through Task and dependencies locked with pnpm.
- Limit implementation to frontend tooling; no database or backend changes.
