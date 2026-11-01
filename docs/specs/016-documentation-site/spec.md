# Reader-focused documentation

## User stories

- A visitor learns what camply does and opens the hosted application from the README.
- A local user follows a short, accurate standalone setup and finds detailed hosting guidance.
- A contributor previews and builds a searchable Zensical site without starting the application stack.

## Requirements

- Keep the README concise, with the hosted app, local setup, self-hosting options, documentation links, and license.
- Author the site under `docs/zensical`, with clear navigation for users, operators, and contributors.
- Preserve existing technical references and useful details removed from the README.
- Manage the documentation dependency with uv and expose local build/preview commands through Task.
- Keep generated output ignored and publish the built site to GitHub Pages after successful main-branch CI, following `juftin/cookiecutter-python`.
- Build and verify documentation on pull requests without deploying it; document the one-time GitHub Pages setup.

## Acceptance

The local strict build succeeds, generated page links and assets resolve, and preview serves the site on a port separate from the application. CI verifies the docs on pull requests; successful pushes to `main` publish through the shared GitHub Pages action with the correct artifact directory, permissions, environment, and site URL.
