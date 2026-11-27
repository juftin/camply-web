# Validation Quickstart: Documentation Rework

**Feature**: `20261116-171913-docs-rework` | **Date**: 2026-11-16

Run these checks from the repository root after implementing the documentation rework to verify build health, link integrity, navigation scoping, search hygiene, and packaging integration.

## 1. Local Preview & Navigation Walkthrough

```bash
task docs:serve
```

Open `http://127.0.0.1:8001/docs/` and verify:

- The landing page and sidebar show **User Documentation** and **Self-Hosting** expanded by default, with **Technical & Architectural** and **Technical Reference** visible in the sidebar and collapsed until opened.
- Opening **Technical -> Architecture & Contributing** navigates to `/docs/technical/` and auto-expands **Technical & Architectural**.
- Opening **Technical -> Technical Reference** navigates to `/docs/reference` and auto-expands **Technical Reference**.
- Visiting `/docs/license` opens the dedicated AGPL-3.0 license page; opening `/docs/architecture/ARCHITECTURE_DEEP_DIVE` or `/docs/operations/RELEASES` renders Mermaid diagrams cleanly without raw code fences.
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
