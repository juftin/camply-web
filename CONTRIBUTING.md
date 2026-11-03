# Contributing to Camply ⛺️

Thank you for your interest in contributing to **Camply**! We are building a modern, community-facing campsite finder web application.

---

## 📋 Prerequisites

Before contributing, ensure your machine has:

- **Python >= 3.11** (development and primary CI default to 3.14) managed by [uv](https://docs.astral.sh/uv/)
- **Node.js 24+** and **pnpm 12+**
- **Docker & Docker Compose** (for backing PostgreSQL & Valkey services)
- **go-task** ([Taskfile](https://taskfile.dev/)) runner

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

To keep feature development isolated and clean, we strongly recommend working in git worktrees located in `.worktrees/`:

```bash
# Create a new branch and isolated worktree:
task worktree:add -- feature-name

# Navigate into the worktree:
cd .worktrees/feature-name

# When finished:
task worktree:remove -- feature-name
```

---

## 🎨 Commit Conventions (Gitmoji)

We use [semantic-release](https://semantic-release.gitbook.io/) and [Gitmoji](https://gitmoji.dev/). Every commit message **MUST** begin with a valid Gitmoji representing the intent:

| Gitmoji | Code          | Purpose                                |
| :------ | :------------ | :------------------------------------- |
| ✨      | `:sparkles:`  | New feature                            |
| 🐛      | `:bug:`       | Bug fix                                |
| 🔨      | `:hammer:`    | Developer tooling / refactor / scripts |
| 📝      | `:memo:`      | Documentation updates                  |
| 🧪      | `:test_tube:` | Adding or improving tests              |
| 🎨      | `:art:`       | UI / visual style tweaks               |
| 🔒      | `:lock:`      | Security or auth fixes                 |

Example commit:

```bash
git commit -m "✨ (search): Add campsite amenity filters to Explore view"
```

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

## 🤖 Feature Lifecycle & Spec-Kit

Non-trivial features follow the formal **Spec-Kit** engineering lifecycle:

1. **Specify**: Define stories and acceptance criteria in `docs/specs/<number>-<name>/spec.md`.
2. **Design**: Detail technical architecture and database models in `plan.md`.
3. **Tasking**: Create granular, test-backed implementation steps in `tasks.md`.
4. **Implement & Check**: Tick off tasks in `tasks.md` and update `docs/CHECKLIST.md` before opening your PR.

---

## 📬 Submitting a Pull Request

1. Ensure all tests (`task test`) and type checks (`task check`) pass locally.
2. Push your branch to GitHub:
   ```bash
   git push origin feature-name
   ```
3. Open a Pull Request referencing any associated issues and specs.
4. CI will validate your branch across Python versions (`3.11`–`3.14`), linters, and integration smoke gates.
