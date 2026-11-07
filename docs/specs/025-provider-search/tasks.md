# Tasks

- [x] Add validated shared search contract and independent result DTO.
- [x] Implement each API family and inherited regional providers.
- [x] Verify synthetic upstream responses, invalid input, pagination and failures.
- [x] Run provider tests, lint, typing and import boundary checks.
- [x] Document API and update global checklist.
- [x] Resolve both independent review findings with regressions: upstream parent filtering and District of Columbia normalization.
- [x] Replace the combined selector with default None and accept string enum members or plain strings; reject the removed selector.
- [x] Add typed recreation-area results and campground/area/both selection, including entity ID collisions and area-only catalog requests.

Verification: `task test` passed the release, backend, packaging, frontend, and
Pages build/HTTP suites. After review fixes, `task backend:test` passed with
1,093 tests and 23 environment-dependent skips; the search suite separately
passed all 175 regressions. `task check` passed full Python/frontend formatting,
linting, type checks, and all six import contracts. `git diff --check` passed.
Independent review found two issues (DC state normalization and missing upstream
parent filters); both were fixed with regressions and independently re-reviewed
with no remaining actionable findings. Live read-only Recreation.gov checks
verified all entity modes and Yosemite's 16 campgrounds in a single scoped request.
