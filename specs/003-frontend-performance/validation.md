# Validation

## Local measurements

One before/after run on the same machine with installed dependencies, recorded before adding the failed-route recovery guard. Task timings include dependency-install checks and process startup; they are indicative measurements, not performance guarantees.

| Measurement                  |        Before |         After |
| ---------------------------- | ------------: | ------------: |
| `task frontend:lint`         |        2.47 s |        2.01 s |
| `task frontend:check`        |        3.24 s |        1.31 s |
| `task frontend:test`         |        4.03 s |        2.93 s |
| `task frontend:build:static` |        5.70 s |        2.42 s |
| Initial JavaScript           | 848,301 bytes | 528,657 bytes |
| Initial JavaScript, gzip     | 253,210 bytes | 167,862 bytes |

Initial JavaScript includes the entry module and every JavaScript preload in the generated HTML, rather than measuring only the entry chunk. Gzip totals sum each file's compressed size. The compressed initial payload fell by approximately 34%. The new build explicitly preserves Vite 6's browser targets.

## Verification

- `task fix`, `task lint`, and `task check` pass for the entire repository.
- `task test`: 273 backend tests and 102 frontend tests pass.
- Application routing tests also pass with `GITHUB_REPOSITORY=juftin/camply` to exercise repository-subpath URLs.
- Synthetic invalid code is rejected by Oxlint's undefined-variable, explicit-any, and React Hooks rules.
- OpenAPI generation succeeds against a synthetic HTTP schema using the retained compiler API.
- Static assets and the Node 24 Docker image build successfully.
- Production browser smoke testing covers home, providers, FAQ, and dashboard with mocked APIs, no page errors, and secondary chunks fetched only on navigation.
- Pre-commit hooks pass for all changed files.

## Compatibility audit

- All 27 direct application dependencies resolve to the versions in the original npm lockfile. This does not establish complete transitive dependency equivalence.
- Public backend APIs and database models are unchanged. Existing authentication, invitation, and routing tests remain passing.
- `npm run build` remains usable when pnpm is installed. Installation uses `pnpm install --frozen-lockfile`; `npm ci` is no longer supported because the npm lockfile was replaced.
- Node 24 is now required for development and builds. Direct ESLint/Prettier commands are replaced by Oxlint/Oxfmt; existing Task entrypoints remain available. Lint rule mapping is not a guarantee of identical diagnostics.
- The existing visual check matches 14 of 16 committed baselines. The two modified dashboard views differ only in relative timestamp text changing from `100d ago` to `101d ago`; baseline images were not updated. The snapshot command therefore reports a failure despite no observed layout differences.
- A production browser failure simulation reproduced a blank screen when a secondary chunk was unavailable. Page error boundaries now preserve the shared navigation and offer a reload action; an integration regression covers the failure and navigation to another route. A production Chromium check confirms the error screen preserves the shell, navigating home clears it, and reload succeeds once the chunk is available again, without uncaught page errors.

## Remaining release checks

- Deploy a Cloudflare preview with the production-equivalent Node/pnpm settings; exercise deep links, refreshes, API forwarding, and real authentication callbacks.
- Exercise the production build in Firefox and WebKit. Preserving the old compilation targets does not prove runtime compatibility in every previously supported browser.
- Check an already-open browser tab across deployment changes to validate asset caching and recovery from stale chunks.
