# Release CI/CD

## User story

As a maintainer, merging a release-worthy Gitmoji commit to `main` should produce a GitHub release and matching backend/frontend images on GHCR after all existing CI checks pass.

## Requirements

- Reuse `juftin/actions/semantic-release@v1` and the Gitmoji configuration from `juftin/cookiecutter-python`.
- Release only trusted pushes to `juftin/camply-web` on `main`, after the complete CI workflow succeeds. Pull requests must never publish.
- Publish `ghcr.io/juftin/camply-backend` and `ghcr.io/juftin/camply-frontend` with matching full semantic versions and moving major aliases such as `v1`. Update `latest` after every successful `main` build, including commits that do not warrant a semantic release.
- Stamp all backend workspace packages, the backend lockfile, and frontend package metadata in the release workspace before building. Leave version changes uncommitted; Git tags identify releases.
- Attach version-stamped sdists for all four installable backend workspace packages to each GitHub release. Build the distributions before creating the release; do not publish packages to PyPI.
- Enable `semantic-release-major-tag` to advance matching Git major aliases such as `v1` after release success, in addition to the existing Docker aliases.
- Separate release creation from image publishing: `release.yaml` creates the GitHub release with the existing Renovate GitHub App; `publish.yaml` handles native `release: published` events using the exact full-version tag. Use the repository's `APP_ID` and `APP_PRIVATE_KEY` secrets directly. Use `GITHUB_TOKEN` only for GHCR publishing.
- Preserve the frontend's same-origin `/api` configuration and existing Docker build contexts.
- Document setup, version rules, initial release behavior, verification, and failure recovery. Application hosting and PyPI publishing are outside this feature.

## Acceptance scenarios

1. A successful `main` build containing `✨` publishes a minor release (the initial release is `1.0.0` when no release tags exist).
2. Failed or cancelled CI, pull requests, and forks cannot publish artifacts. Successful `main` builds without release-worthy changes publish only `latest`.
3. Both image tags and installed application metadata match the selected release version.
4. A failed image publication leaves the GitHub release intact; rerunning its publish workflow retries the same tagged version without another semantic release.
5. A `1.2.3` release updates the `1.2.3`, `v1`, and `latest` image tags; a subsequent `2.0.0` release updates `2.0.0`, `v2`, and `latest` while preserving `v1`.
6. Each GitHub release includes `backend`, `db`, `providers`, and `worker` sdists with matching metadata versions and required source/configuration files; a failed source build prevents publication.
7. After a successful `1.2.3` release, Git tag `v1` points to the released commit; later releases advance their own major alias without changing other majors.
8. A release-producing main build publishes images once via the release event; a successful main build without a release calls the same publisher for `latest` only. Missing App credentials fail release creation rather than silently suppressing the publish event.
