# Release CI/CD

## User story

As a maintainer, merging a release-worthy Gitmoji commit to `main` should produce a GitHub release and matching backend/frontend images on GHCR after all existing CI checks pass.

## Requirements

- Reuse `juftin/actions/semantic-release@v1` and the Gitmoji configuration from `juftin/cookiecutter-python`.
- Release only trusted pushes to `juftin/camply-web` on `main`, after the complete CI workflow succeeds. Pull requests must never publish.
- Publish `ghcr.io/juftin/camply-backend` and `ghcr.io/juftin/camply-frontend` with matching full semantic versions and moving major aliases such as `v1`. Update `latest` after every successful `main` build, including commits that do not warrant a semantic release.
- Stamp all backend workspace packages, the backend lockfile, and frontend package metadata in the release workspace before building. Leave version changes uncommitted; Git tags identify releases.
- Use the repository's `GITHUB_TOKEN`; do not depend on a second workflow triggered by a bot-created release.
- Preserve the frontend's same-origin `/api` configuration and existing Docker build contexts.
- Document setup, version rules, initial release behavior, verification, and failure recovery. Application hosting and legacy CLI/PyPI publishing are outside this feature.

## Acceptance scenarios

1. A successful `main` build containing `✨` publishes a minor release (the initial release is `1.0.0` when no release tags exist).
2. Failed or cancelled CI, pull requests, and forks cannot publish artifacts. Successful `main` builds without release-worthy changes publish only `latest`.
3. Both image tags and installed application metadata match the selected release version.
4. A failed image build prevents creation of the release tag and GitHub release, allowing the run to be retried.
5. A `1.2.3` release updates the `1.2.3`, `v1`, and `latest` image tags; a subsequent `2.0.0` release updates `2.0.0`, `v2`, and `latest` while preserving `v1`.
