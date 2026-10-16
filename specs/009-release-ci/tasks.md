# Tasks

- [x] Add behavioral checks for version stamping, Bake tags/labels, and publication preconditions; verify failure before implementation.
- [x] Connect complete CI to serialized semantic releases using the existing shared action.
- [x] Implement version preparation and GHCR publishing through Task.
- [x] Publish `latest` for successful main builds without a semantic release, and advance the matching major alias (`v1`, `v2`, etc.) only for stable releases; verify both publication plans and CI/source-revision guards.
- [x] Build version-stamped workspace sdists, attach them as GitHub release assets, verify archive contents and wheel rebuilds, and enable the bundled major-tag plugin for Git aliases. Exercise version preparation with a fresh uv cache to cover hosted CI.
- [x] Validate workflow syntax, release checks, and application quality gates.
- [x] Document release operations and update the global feature checklist.

Verification: `task fix`, `task lint`, `task check`, `task test` (551 backend tests passed/12 opt-in tests skipped, 297 frontend tests passed), `task build` (both images), changed-file pre-commit hooks, and actionlint with ShellCheck passed. `task release:test` passes all 7 release checks, including cold-cache preparation and stamped sdists that match the release asset glob and rebuild into wheels. `task dist` builds the four workspace sdists. The pinned shared action's dependency installation and signature audit passed with Node 24/npm 10.9.9; its plugins load this project's configuration and verify Gitmoji bump rules. The actual major-tag plugin was exercised against a local bare repository, creating and advancing `v1`, then creating `v2` while preserving `v1`. Hosted publication remains to be exercised after merge.
