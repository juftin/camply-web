# Contributing to Camply ⛺️

Thank you for your interest in contributing to **Camply**! We are building a modern, community-facing campsite finder web application.

---

## 📋 Prerequisites

Before contributing, ensure your machine has:

- **Python >= 3.11** (development and primary CI default to 3.14) managed by [uv](https://docs.astral.sh/uv/)
- **Node.js 24+** and **pnpm 12+**
- **Docker & Docker Compose** (for backing PostgreSQL & Valkey services)
- **go-task** ([Taskfile](https://taskfile.dev/)) runner
- **GitHub CLI** ([gh](https://cli.github.com/)) for pull request and review operations

---

## 🚀 Quickstart

1. **Clone the repository**:

   ```bash
   git clone https://github.com/juftin/camply-web.git
   cd camply-web
   ```

2. **Install all dependencies** (Backend + Frontend):

   ```bash
   task install
   ```

3. **Verify your local toolchain**:

   ```bash
   task doctor
   ```

4. **Start the local development stack**:
   ```bash
   # Option A: Backing services in Docker, API + Frontend running locally
   task compose:infra
   task dev

   # Option B: Run everything in Docker Compose
   task compose:up
   ```
   - Frontend: `http://localhost:5173`
   - Backend API Docs: `http://localhost:8000/api/docs`

---

## 🌳 Branching & Git Worktrees

To keep feature development isolated and clean, work in git worktrees located in `.worktrees/`:

```bash
# Create a new branch and isolated worktree:
task worktree:add -- feature-name

# Navigate into the worktree:
cd .worktrees/feature-name

# When finished and merged:
task worktree:remove -- feature-name
```

---

## 🏷️ Commit & PR Title Conventions

Titles follow the unified format:

```
<type> [scope?][:?] <summary>
```

> [!TIP]
> If your title needs **"and"** in the summary, the PR is too broad — narrow the scope.

### Gitmoji Mode (Default in this repo / `GITMOJI=1`)

| Prefix | Intent                                    |
| :----- | :---------------------------------------- |
| ✨     | New feature                               |
| 🐛     | Bug fix                                   |
| 💥     | Breaking change                           |
| ♻️     | Refactor                                  |
| 🔨     | Developer tooling / task runner / scripts |
| 📝     | Documentation                             |
| ⚡     | Performance                               |
| 🧪     | Tests                                     |
| 🔧     | Configuration                             |
| ⬆️     | Dependency bump                           |
| 🎨     | UI / style tweaks                         |

**Examples**:

- `✨ (search): Add campsite amenity filters to Explore view`
- `🐛 (maps): Fix bounds calculation on mobile viewports`
- `🔨 (taskfile): Streamline CI and Taskfile configuration`

### Conventional Commit Mode

When `GITMOJI` is unset or `0`:

- `feat: [scope]: <summary>`
- `fix: [scope]: <summary>`
- `refactor: [scope]: <summary>`
- `docs: [scope]: <summary>`
- `chore: [scope]: <summary>`

---

## 🧪 Local Quality Gates

Run quality checks before opening a pull request:

```bash
# Auto-fix code formatting and linting:
task fix

# Verify code formatting (Ruff + Oxfmt):
task check:format

# Run linters (Ruff, Oxlint, Import Linter):
task check:lint

# Run static type checkers (MyPy, TypeScript):
task check:types

# Run test suites:
task test
```

---

## 📬 Pull Request Workflow

We use the GitHub CLI (`gh`) for opening and refining pull requests.

### 1. PR Body Structure

Every pull request should adhere to the following structure:

```markdown
## Summary

[Concise summary of what this PR achieves.]

## Context

[The "why" behind this work — feature, bugfix, or chore reasoning.]

## Changes

[Detailed description of code changes, ideally organized by file or feature area.]

<details><summary>Code Changes</summary>
<p>

- **`path/to/file`**
  - Detailed description of changes.

</p>
</details>

## Test Plan

- [x] `task check:format` passed
- [x] `task check:lint` passed
- [x] `task check:types` passed
- [x] `task test` passed
- [ ] Manual verification step

## Behavior Diagram

[Optional Mermaid diagram explaining architecture or workflow changes]
```

### 2. Creating the PR with `gh`

Prepare the body in a temporary file and create the PR:

```bash
BODY_FILE="$(mktemp "${TMPDIR:-/tmp}/pr-body.XXXXXX")"
cat > "${BODY_FILE}" <<'EOF'
## Summary
...
EOF

gh pr create \
  --title "<type> [scope?]: <summary>" \
  --body-file "${BODY_FILE}"
```

### 3. PR Rules & Best Practices

- **Final State**: Describe the PR's final state (what it achieves and why). Omit intermediate attempts, discarded approaches, and internal reasoning loops.
- **Prose Formatting**: Remove hard line breaks within prose paragraphs so they render cleanly on GitHub. Preserve blank lines and structural line breaks in lists, tables, and code blocks.
- **Up-to-Date Metadata**: Keep the title and description up to date whenever newly pushed code materially changes the PR.
- **No Force-Pushes**: Make requested changes in a new commit — do not force-push or amend unless explicitly requested to squash.
- **Never Force-Push to Main**: Protected branches must remain linear and safe.

---

## 🔄 Refining & Responding to Reviews

1. **Inspect Review Feedback**:
   ```bash
   gh pr view --comments
   ```
2. **Make Updates**:
   Commit changes in a new commit and push:
   ```bash
   git push origin HEAD
   ```
3. **Monitor CI**:
   ```bash
   gh pr checks --watch
   ```
4. **Thread Resolution**:
   Never resolve review threads yourself — let the reviewer confirm and resolve them.

---

## 🔒 Security & Privacy

- **No Secrets**: Never commit credentials, tokens, or private keys. Use environment variables.
- **No PHI / PII**: Ensure logs, tests, cassettes, and code do not include sensitive personal data.
- **Environment Files**: Never commit `.env` or decrypt secrets into repository context.
