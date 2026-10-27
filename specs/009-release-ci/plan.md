# Implementation Plan

Keep CI callable, with pull-request and manual entrypoints. `release.yaml` owns pushes to main, gates semantic-release on the entire CI suite, stamps application versions, builds sdists, and creates the GitHub release and Git major alias. Mint a repository-scoped installation token using the existing Renovate App credentials so release creation triggers native GitHub events. Keep npm 10 compatibility for the pinned shared action.

`publish.yaml` handles stable `release: published` events. Validate the exact `vMAJOR.MINOR.PATCH` tag, check out that tag, stamp its version again, and publish both GHCR images through Task using `GITHUB_TOKEN`. The publish workflow is also reusable: when semantic-release completes without a release, call it at the successful main SHA for latest-only images. An exec success marker distinguishes the two paths, avoiding duplicate image builds for release commits. Serialize image publication across both entrypoints.

Attach the four installable Python workspace sdists through the GitHub release plugin, and retain semantic-release-major-tag for Git aliases. Preserve full-version, major, and latest image tags, OCI labels, separate caches, and the frontend same-origin API configuration. Version changes remain uncommitted.

Constitution check: preserve monorepo boundaries, use Task and existing uv/pnpm/Docker tools, and introduce no application or deployment infrastructure. Verify release source selection, rejection of malformed tags, no-release fallback, cold-cache stamping, sdist contents and wheel rebuilds, Bake plans, and publication guards. Validate workflow syntax and run the required lint/type/test gates. Document App credential availability and independent publisher recovery.
