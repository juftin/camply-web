# DESIGN_AGENTIC: Local Development & Agentic Tooling

This document outlines the local "Agentic" development environment for `camply`. These Model Context Protocol (MCP) servers allow AI agents (like Gemini CLI) to interact directly with the database, UI, and infrastructure for autonomous implementation and validation.

## 🎯 Philosophy

1. **Local-First**: All tools run locally to ensure privacy, speed, and reliability.
2. **Autonomous Validation**: The agent should be able to _prove_ a change works (e.g., query the DB or run a browser test) before finishing a task.
3. **Task-Driven**: Tools are integrated into the `spec-kit` workflow to automate the boring parts (issue tracking, documentation lookup).

---

## 🛠️ MCP Configuration (Local Dev)

The following MCP servers should be added to the local agent configuration (e.g., `gemini-cli` config or `claude_desktop_config.json`).

### 1. Database MCP (PostgreSQL)

**Capability**: Directly query the local `camply` database.

- **Connection**: `postgresql://postgres:postgres@localhost:5432/camply`
- **Use Case**:
  - Verify schema migrations.
  - Validate de-duplication logic (hashes).
  - Insert/Update whitelisted users for early access testing.

### 2. Browser MCP (Playwright)

**Capability**: Launch and control a local browser instance.

- **URL**: `http://localhost:5173` (Vite Frontend)
- **Use Case**:
  - "Visual Regression": Confirm Shadcn/UI components look correct.
  - "E2E Testing": Automate the "Search -> Create Scan -> Dashboard" flow.
  - "Auth Testing": Verify the Auth0 redirect and early access gate.

### 3. Docker MCP

**Capability**: Monitor and manage the local container stack.

- **Stack**: `backend-api`, `celery-worker`, `redis`, `postgres`.
- **Use Case**:
  - Check Celery logs for scan errors.
  - Restart specific services after a code change.
  - Monitor queue depth in Valkey.

### 4. GitHub MCP

**Capability**: Manage issues, PRs, and project boards.

- **Repository**: `juftin/camply`
- **Use Case**:
  - Synchronize `spec-kit` tasks with GitHub Issues.
  - Create PRs with detailed "Plan vs. Reality" descriptions.
  - Automate project board transitions.

### 5. DevDocs / Search MCP

**Capability**: Real-time documentation lookup.

- **Targets**: `FastAPI`, `Pydantic v2`, `Shadcn/UI`, `Tailwind`, `Celery`.
- **Use Case**:
  - Ensure idiomatic usage of Shadcn primitives.
  - Reference latest Pydantic validator syntax.

---

## 🚀 Workflow Integration

### Step 1: Research

When starting a feature, the agent uses **DevDocs MCP** to find the best implementation patterns and **GitHub MCP** to audit related existing issues.

### Step 2: Strategy

The agent uses **spec-kit** to generate the plan and **Postgres MCP** to check the current DB state for conflicts.

### Step 3: Execution & Validation

1. Agent writes code.
2. Agent uses **Docker MCP** to restart the worker.
3. Agent uses **Postgres MCP** to verify data was correctly inserted into `unique_targets`.
4. Agent runs `task snapshot` to generate and inspect UI snapshots, using the `view_file` tool to examine diff images and confirm visual correctness.
5. If changes are intended and verified, agent updates baselines via `task snapshot:update`.

### Step 4: Finalization

Agent uses **GitHub MCP** to update tasks and submit the PR.

---

## 📸 UI Snapshot & Visual Feedback Loop

Camply includes an automated snapshot and visual regression mechanism designed for both human reviewers and AI agents.

### Architecture

- **Engine**: Headless Playwright Chromium (`scripts/run-snapshots.ts`) running against the local Vite frontend.
- **Determinism**: Network routes (`/api/auth-config`, `/api/me`, `/api/scans`, etc.) are intercepted with mock data to guarantee zero network drift and immediate rendering. CSS animations/transitions and carets are frozen.
- **Coverage**:
  - Full pages (Home, Dashboard, Early Access, Auth, Ethos) across desktop (`1280x800`) and mobile (`390x844`) viewports.
  - Interactive states (e.g. Scan Form dialog modal open).
  - Both **Light** and **Dark** themes.
  - Component & state catalog (`/dev/preview`).

### Workflow for AI Agents

1. **Trigger Snapshots**: Run `task snapshot` (or `task snapshot:check`).
2. **Review Report**: Read `frontend/snapshots/REPORT.md` to see snapshot statuses (✅ UNCHANGED, ⚠️ MODIFIED, 🆕 NEW).
3. **Inspect Visual Diffs**: For any modified snapshot, call the `view_file` tool on the diff image (`frontend/snapshots/diffs/<name>-diff.png`) and current image (`frontend/snapshots/current/<name>.png`).
4. **Self-Correction**: Inspect the rendered image for layout shifts, clipping, color contrast issues, or misaligned elements. Iterate on the code until visually sound.
5. **Update Baselines**: Run `task snapshot:update` when visual changes are confirmed and deliberate.

### Workflow for Human Reviewers

- Check the generated `frontend/snapshots/REPORT.md` in PR descriptions.
- Open `frontend/snapshots/report.html` locally or in CI artifacts for an interactive side-by-side gallery.

---

## 🔒 Security & Local Config

- **Secrets**: Never store API keys in this documentation.
- **Auth0 Testing**: For local dev, we will use a dedicated "Dev" Auth0 Tenant or a mocked local Auth flow to avoid hitting production limits.
