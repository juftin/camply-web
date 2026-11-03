# Documentation implementation plan

Use `docs/site/.vitepress/config.ts` with `docs/site` and generated output in `build/docs`. Manage VitePress via `package.json` and a `docs` Task namespace. Documentation tasks use pnpm and do not build or install camply.

Move the README's runtime and packaging reference into `docs/operations/RUNNING.md`, fixing relative links and inbound installation pointers. Write concise site guides that link to existing architectural and operational references on GitHub rather than copying them. Keep the existing reference paths stable.

User setup installs directly from GitHub with `uv tool install`, selects the `server` dependencies and Python 3.14, then starts with `camply serve`. Document Git/Node/pnpm as source-build prerequisites, use Docker Compose directly in hosting instructions, and keep Task commands in contributor documentation.

Use VitePress's built-in navigation, search, code blocks, and light/dark theme. Verify with a build, a generated HTML link/asset audit, and a local HTTP preview check.

Follow [cookiecutter-python's release workflow](https://github.com/juftin/cookiecutter-python/blob/main/.github/workflows/release.yaml): use pinned `juftin/actions/taskfile` and `juftin/actions/github-pages` actions, passing `build/docs` explicitly. Add a documentation CI job for pull requests and reusable main CI; publish the mirror only after that CI passes on `main`, independently of semantic-release output. Limit Pages/OIDC write permissions to the deployment job and serialize deployments through the `github-pages` environment. Set the canonical URL to the app's `https://camply.juftin.dev/docs/`.

Add `task docs:check` for strict builds plus standard-library unittest checks of publication boundaries and rendered links/assets. Update the release test fixture to include the new Taskfile include. A repository administrator must enable GitHub Actions as the Pages source once; this is documented rather than attempted with the current push-only credentials.

## Constitution review

Root manifests remain authoritative; docs dependencies are isolated from application extras. Task exposes all new workflows. Build and serving regressions verify generated assets, archive integrity, and runtime dependency isolation.

## Bundled web documentation

Extend the existing Vite build plugin to generate the VitePress site and copy it into `dist/docs` before synchronizing `build/frontend`. Frontend builds run VitePress directly via Node. No frontend build may silently omit documentation.

Include `docs/site` in sdists, hash it alongside frontend inputs, and update the asset recipe. Prepared archives retain generated docs and validate them without rerunning generators. Docker copies docs sources into its build stage. Keep the existing separate Pages publication as a mirror and use `https://camply.juftin.dev/docs/` as the primary documentation URL.

Cloudflare Pages and Docker frontend stages run VitePress via Node/pnpm directly with zero Python documentation dependencies.

Enable directory indexes in the Python static server and prevent missing `/docs/` routes from falling through to the SPA. Add a dedicated Nginx docs location with real 404s. The footer uses a normal anchor under Vite's base URL so the browser loads the separate static site. Verify directory redirects, nested pages/assets, unknown routes, wheel/sdist contents, dependency isolation, archive tampering, real Pages HTTP serving, and the footer link.
