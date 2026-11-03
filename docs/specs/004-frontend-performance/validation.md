# Validation

## Local measurements

One before/after run on the same machine with installed dependencies and eager page imports. Task timings include dependency-install checks and process startup; they are indicative measurements, not performance guarantees.

| Measurement                  |        Before |         After |
| ---------------------------- | ------------: | ------------: |
| `task frontend:build:static` |        5.70 s |        3.14 s |
| Initial JavaScript           | 848,301 bytes | 829,895 bytes |
| Initial JavaScript, gzip     | 253,210 bytes | 243,795 bytes |

Initial JavaScript includes the entry module and every JavaScript preload in the generated HTML, rather than measuring only the entry chunk. Gzip totals sum each file's compressed size. The current eager build loads a single JavaScript entry file; its compressed initial payload is approximately 4% smaller than the original. The new build explicitly preserves Vite 6's browser targets.

## Verification

- `task fix`, `task lint`, and `task check` pass for the entire repository.
- `task test`: 273 backend tests and 99 frontend tests pass.
- Application routing tests also pass with `GITHUB_REPOSITORY=juftin/camply-web` to exercise repository-subpath URLs.
- Synthetic invalid code is rejected by Oxlint's undefined-variable, explicit-any, and React Hooks rules.
- OpenAPI generation succeeds against a synthetic HTTP schema using the retained compiler API.
- Static assets and the Node 24 Docker image build successfully.
- Production browser smoke testing covers home, providers, FAQ, and dashboard with mocked APIs, no page errors, and no additional JavaScript downloads on route navigation.
- Pre-commit hooks pass for all changed files.
- Both `task --dry` and plain `task` confirm the default command only lists available workflows.

## Compatibility audit

- All 27 direct application dependencies resolve to the versions in the original npm lockfile. This does not establish complete transitive dependency equivalence.
- Public backend APIs and database models are unchanged. Existing authentication, invitation, and routing tests remain passing.
- `npm run build` remains usable when pnpm is installed. Installation uses `pnpm install --frozen-lockfile`; `npm ci` is no longer supported because the npm lockfile was replaced.
- Node 24 is now required for development and builds. Direct ESLint/Prettier commands are replaced by Oxlint/Oxfmt; existing Task entrypoints remain available. Lint rule mapping is not a guarantee of identical diagnostics.
- The existing visual check matches 14 of 16 committed baselines. The two modified dashboard views differ only in relative timestamp text changing from `100d ago` to `101d ago`; baseline images were not updated. The snapshot command therefore reports a failure despite no observed layout differences.
- All page imports remain eager; application routing and authentication tests match the original implementation. There are no route-level Suspense fallbacks or page-chunk recovery components.

## Remaining release checks

- Deploy a Cloudflare preview with the production-equivalent Node/pnpm settings; exercise deep links, refreshes, API forwarding, and real authentication callbacks.
- Exercise the production build in Firefox and WebKit. Preserving the old compilation targets does not prove runtime compatibility in every previously supported browser.
