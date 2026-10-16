# Implementation Plan

Make the existing CI workflow callable while preserving its pull-request and manual entrypoints. A new `release` workflow owns pushes to `main`, calls the complete CI workflow, and publishes latest images before running semantic-release after success. Serialize release runs without cancelling active publication.

Use the template's Gitmoji analyzer and GitHub release plugin, with an exec preparation hook that invokes Task to stamp versions and publish both Docker images before semantic-release creates its tag. Disable automated issue/PR comments. Keep development version files uncommitted so release automation needs no protected-branch write or personal access token.

Build sdists for the four installable Python workspace packages via `task dist` after version stamping and before image publication. Attach `dist/*.tar.gz` with the GitHub plugin. The workspace root is virtual, so no root distribution or legacy CLI build is needed. Enable the already bundled `semantic-release-major-tag` success hook to maintain Git major aliases. Verify archive metadata/source contents and rebuild wheels from the sdists; remove the release fixture's offline-resolution assumption so it also works with CI's cold cache.

Replace the placeholder `task publish` with a Bake invocation that publishes full-version, major-alias, and `latest` tags, component-specific caches, and OCI version/revision/source labels. Use the same publishing command through `task publish:latest` for latest-only builds, identifying them by source revision. Add `task release:prepare` for workspace version stamping and `task release:test` for isolated behavioral checks. Remove the independent, ungated publisher.

Constitution check: preserve monorepo boundaries, route release operations through Task, use existing uv/pnpm/Docker tools, and introduce no application logic or deployment infrastructure. Verify version synchronization against an isolated fixture, inspect real Bake plans without pushing, check publication guards, lint workflow syntax with actionlint, and run the existing lint/type/test gates.
