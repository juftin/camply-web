# Validation Quickstart: Documentation Rework

**Feature**: `030-docs-rework` | **Date**: 2026-11-16

Run these checks from the repository root after implementing the documentation rework to verify build health, link integrity, navigation scoping, search hygiene, and packaging integration.

## 1. Local Preview & Navigation Walkthrough

```bash
task docs:serve
```

Open `http://127.0.0.1:8001/docs/` and verify:

- The landing page and default sidebar show only **User Documentation** and **Self-Hosting**.
- Opening **Technical -> Architecture & Contributing** switches to the scoped Technical & Architectural sidebar.
- Opening **Technical -> Technical Reference** switches to the scoped Technical Reference sidebar.
- Searching for `"weekends"`, `"notifications"`, `"standalone"`, and `"login"` returns User Documentation and Self-Hosting pages without spec/checklist noise.

## 2. Automated Docs Build & Link/Hygiene Verification

```bash
task docs:check
```

Runs `vitepress build docs` into `build/docs/` and executes `tests/docs/test_docs.py`, verifying:

- Every Markdown page renders cleanly with zero broken links, anchors, or assets.
- Default sidebar items and search exclusions match [the site navigation contract](contracts/site-navigation.md).
- Rewritten User Documentation, Self-Hosting, and active Technical & Architectural pages have zero emoji-prefixed headings and no banned AI-slop openers.

## 3. Frontend Bundle, Pages & Packaging Verification

```bash
task frontend:build
task frontend:test
uv run pytest tests/test_frontend_build.py tests/packaging/test_frontend_artifacts.py
```

Confirms `/docs/`, `/docs/using-camply`, `/docs/assets/camply.svg`, and `/docs/404.html` remain intact in the frontend bundle and Python wheel/sdist artifacts.

## 4. Repo-Wide Quality Gates

```bash
task lint
task check
```

Ensures formatting (`oxfmt`, `ruff`) and type checks (`tsc`, `mypy`) pass on modified VitePress TypeScript configuration and Python test files.
