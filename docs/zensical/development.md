# Develop camply

For application development, install Python 3.14, uv, Node.js 24, the pnpm version pinned in `package.json`, Docker Compose, and Task. The [developer guide](https://github.com/juftin/camply-web/blob/main/docs/development/DEVELOPER_GUIDE.md) covers setup and detailed workflows.

From the repository root:

```bash
task install
cp docs/examples/.env.example .env
task compose:infra
UV_ENV_FILE=.env task dev
```

If you want to use the Compose PostgreSQL database, enable the PostgreSQL settings in `.env` before starting the backend. The default database is SQLite. Vite serves the frontend at <http://localhost:5173> and proxies `/api` to the backend at port 8000.

Use [standalone setup](self-hosting/standalone.md) when you just want to run the complete app locally. For distributed polling, also run `UV_ENV_FILE=.env task backend:worker:all` in a separate terminal. Import the catalog through **Sync Providers** in Admin Operations.

## Quality checks

```bash
task lint
task check
task test
```

Run `task` to list workflows. See the [style guide](https://github.com/juftin/camply-web/blob/main/docs/development/STYLE_GUIDE.md) for contribution standards and the [reference directory](reference.md) for architecture and feature plans.

## Working on the docs

The documentation only needs [uv](https://docs.astral.sh/uv/) and [Task](https://taskfile.dev/installation/). Run these commands from the repository root:

```bash
task docs:install
task docs:serve
```

Open <http://127.0.0.1:8001>. Zensical rebuilds as you edit Markdown under `docs/zensical`. Navigation and theme settings live in root `zensical.toml`.

`docs:serve` and `docs:build` automatically sync the locked documentation dependency group, so `docs:install` is optional. These tasks select only the docs group in the shared uv environment; run `task install` again when returning to application development.

```bash
task docs:build
```

The strict build writes the static site to ignored `build/docs`. Run `task docs:check` to also verify generated links, assets, and the publishing configuration. To preview it on another port, run `task docs:serve -- --dev-addr 127.0.0.1:8002`.

## Documentation in the web app

Every production frontend build generates the docs and includes them under `docs/` in the static bundle. The footer links to `/docs/` on the same instance. Python standalone, Nginx, and Cloudflare Pages serve the generated pages and assets directly, including nested documentation URLs.

Frontend-only builds use uv to run the locked documentation dependencies in an isolated environment. Cloudflare Pages installs the build-only `src/frontend/requirements.txt` and can use `python3 -m zensical` when uv is unavailable. Python wheel/sdist builds declare Zensical as a build dependency and pass their isolated build interpreter to Vite. Docker copies the documentation sources into its build stage. Zensical is not installed as an application runtime dependency.

Prepared wheels and source distributions include the generated docs. Rebuilding a prepared sdist validates the documentation inputs and assets without running Vite or Zensical; Node and pnpm are not needed for that rebuild. Vite's development server serves the React app; use the separate docs preview above when editing documentation.

## Publishing the docs

Pull requests build and verify the documentation in CI. The app hosts its docs at <https://camply.juftin.dev/docs/>. After all CI checks pass on `main`, the release workflow also publishes `build/docs` as a GitHub Pages mirror using the same [shared Pages action as cookiecutter-python](https://github.com/juftin/cookiecutter-python/blob/main/.github/workflows/release.yaml). The mirror updates even when no new application version is released.

The mirror URL is <https://juftin.com/camply-web/>. Self-hosted instances serve their own bundled documentation at `/docs/`.

For the first mirror deployment, a repository administrator must open **Settings → Pages → Build and deployment** and choose **GitHub Actions** as the source. The deployment job uses the `github-pages` environment with `pages: write` and `id-token: write`; it uses the standard `GITHUB_TOKEN` and needs no additional publishing secret. If Pages is not enabled, configure it before the next push to `main`, or rerun the failed documentation job after enabling it. Bundled app documentation works independently of this setting.

Use relative Markdown links between site pages. Link to the existing GitHub references when a document lives outside `docs/zensical`, so those links also work in the built site. See [Zensical's authoring guide](https://zensical.org/docs/authoring/markdown/) for supported Markdown.
