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

## Publishing the docs

Pull requests build and verify the documentation in CI. After all CI checks pass on `main`, the release workflow publishes `build/docs` to GitHub Pages using the same [shared Pages action as cookiecutter-python](https://github.com/juftin/cookiecutter-python/blob/main/.github/workflows/release.yaml). Documentation updates publish even when no new application version is released.

The documentation URL is <https://juftin.com/camply-web/>. The app remains at <https://camply.juftin.dev>.

For the first deployment, a repository administrator must open **Settings → Pages → Build and deployment** and choose **GitHub Actions** as the source. The deployment job uses the `github-pages` environment with `pages: write` and `id-token: write`; it uses the standard `GITHUB_TOKEN` and needs no additional publishing secret. If Pages is not enabled, configure it before the next push to `main`, or rerun the failed documentation job after enabling it.

Use relative Markdown links between site pages. Link to the existing GitHub references when a document lives outside `docs/zensical`, so those links also work in the built site. See [Zensical's authoring guide](https://zensical.org/docs/authoring/markdown/) for supported Markdown.
