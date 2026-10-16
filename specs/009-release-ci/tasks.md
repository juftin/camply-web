# Tasks

- [x] Add behavioral checks for version stamping, Bake tags/labels, and publication preconditions; verify failure before implementation.
- [x] Connect complete CI to serialized semantic releases using the existing shared action.
- [x] Implement version preparation and GHCR publishing through Task.
- [x] Publish `latest` for successful main builds without a semantic release, and advance the matching major alias (`v1`, `v2`, etc.) only for stable releases; verify both publication plans and CI/source-revision guards.
- [x] Validate workflow syntax, release checks, and application quality gates.
- [x] Document release operations and update the global feature checklist.

Verification: `task fix`, `task lint`, `task check`, `task test` (551 backend tests passed/12 opt-in tests skipped, 297 frontend tests passed), `task build` (both images), changed-file pre-commit hooks, and actionlint with ShellCheck passed. After adjusting tag policies, `task release:test` passed all 6 release checks and workflow/hook validation passed again. The pinned shared action's dependency installation and signature audit passed with Node 24/npm 10.9.9; its plugins loaded this project's configuration and verified the documented Gitmoji bump rules. Hosted publication remains to be exercised after merge.
