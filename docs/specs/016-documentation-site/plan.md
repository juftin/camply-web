# Documentation implementation plan

Use root `zensical.toml` with `docs_dir = "docs/zensical"` and generated output in `build/docs`. Add a dedicated uv `docs` dependency group and a `docs` Task namespace. Documentation tasks install only this group and do not build or install camply.

Move the README's runtime and packaging reference into `docs/operations/RUNNING.md`, fixing relative links and inbound installation pointers. Write concise site guides that link to existing architectural and operational references on GitHub rather than copying them. Keep the existing reference paths stable.

Use Zensical's built-in navigation, search, code blocks, and light/dark theme. Verify with a strict build, a generated HTML link/asset audit, and a local HTTP preview check.

Follow [cookiecutter-python's release workflow](https://github.com/juftin/cookiecutter-python/blob/main/.github/workflows/release.yaml): use pinned `juftin/actions/taskfile` and `juftin/actions/github-pages` actions, passing `build/docs` explicitly. Add a documentation CI job for pull requests and reusable main CI; publish only after that CI passes on `main`, independently of semantic-release output. Limit Pages/OIDC write permissions to the deployment job and serialize deployments through the `github-pages` environment. Set the site's canonical URL to `https://juftin.com/camply-web/`, following the owner's existing Pages domain.

Add `task docs:check` for strict builds plus standard-library unittest checks of publication boundaries and rendered links/assets. Update the release test fixture to include the new Taskfile include. A repository administrator must enable GitHub Actions as the Pages source once; this is documented rather than attempted with the current push-only credentials.

## Constitution review

Root manifests remain authoritative; docs dependencies are isolated from application extras. Task exposes all new workflows. The strict build and generated-output audit directly verify this documentation change; runtime tests remain unchanged.
