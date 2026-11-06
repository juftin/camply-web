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

The docs site uses [VitePress](https://vitepress.dev/), Node 24, and pnpm. Run these commands from the repository root:

```bash
task docs:install
task docs:serve
```

Open <http://127.0.0.1:8001>. VitePress rebuilds as you edit Markdown under `docs`. Navigation and theme settings live in `docs/.vitepress/config.ts`.

```bash
task docs:build
```

The build writes the static site to ignored `build/docs`. Run `task docs:check` to also verify generated links, assets, and the publishing configuration. To preview the built site, run `task docs:preview`.

## Docs in the web app

Every production frontend build generates the docs and includes them under `docs/` in the static bundle. The footer links to `/docs/` on the same instance. Python standalone, Nginx, and Cloudflare Pages serve the generated pages and assets directly, including nested docs URLs.

Frontend builds run VitePress directly through Node, eliminating separate Python docs dependencies. Cloudflare Pages, Docker frontend builds, and local development use the pinned frontend toolchain. Python wheel/sdist builds bundle the generated static site into application assets. Vite's development server serves the React app; use the separate docs preview above when editing docs.

## Publishing the docs

Pull requests build and verify the docs in CI. The app hosts its docs at <https://camply.rocks/docs/>. After all CI checks pass on `main`, the release workflow also publishes `build/docs` as a GitHub Pages mirror using the same [shared Pages action as cookiecutter-python](https://github.com/juftin/cookiecutter-python/blob/main/.github/workflows/release.yaml). The mirror updates even when no new application version is released.

The mirror URL is <https://juftin.com/camply-web/>. Self-hosted instances serve their own bundled docs at `/docs/`.

For the first mirror deployment, a repository administrator must open **Settings → Pages → Build and deployment** and choose **GitHub Actions** as the source. The deployment job uses the `github-pages` environment with `pages: write` and `id-token: write`; it uses the standard `GITHUB_TOKEN` and needs no additional publishing secret. If Pages is not enabled, configure it before the next push to `main`, or rerun the failed docs job after enabling it. Bundled app docs work independently of this setting.

Use relative Markdown links between site pages. Link to the existing GitHub references when a document lives outside `docs/site`, so those links also work in the built site. See the [VitePress docs](https://vitepress.dev/) for supported Markdown features.
