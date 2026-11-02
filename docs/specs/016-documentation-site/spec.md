# Reader-focused documentation

## User stories

- A visitor learns what camply does and opens the hosted application from the README.
- A local user follows a short, accurate standalone setup and finds detailed hosting guidance.
- A contributor previews and builds a searchable VitePress site without starting the application stack.

## Requirements

- Keep the README concise, with the hosted app, local setup, self-hosting options, documentation links, and license.
- Use GitHub installation with `uv tool install` and `camply serve` in user guides; reserve Task commands for contributor workflows.
- Author the site under `docs/site`, with clear navigation for users, operators, and contributors.
- Preserve existing technical references and useful details removed from the README.
- Manage the documentation dependency with uv and expose local build/preview commands through Task.
- Keep generated output ignored and publish the built site to GitHub Pages after successful main-branch CI, following `juftin/cookiecutter-python`.
- Build and verify documentation on pull requests without deploying it; document the one-time GitHub Pages setup.
- Include the generated VitePress site under `docs/` in every production frontend bundle and Python distribution. VitePress is a build dependency, never a runtime dependency.
- Serve documentation pages, search, and assets at `/docs/` in standalone and Nginx deployments. Missing documentation must return 404 instead of the app's SPA entry point.
- Link to the bundled documentation from the app footer, respecting the frontend base path.
- Preserve prepared-sdist rebuilding without Node, pnpm, or documentation generation; include docs inputs in archive integrity checks.

## Acceptance

The local strict build succeeds, generated page links and assets resolve, and preview serves the site on a port separate from the application. CI verifies the docs on pull requests; successful pushes to `main` publish through the shared GitHub Pages action with the correct artifact directory, permissions, environment, and site URL.
