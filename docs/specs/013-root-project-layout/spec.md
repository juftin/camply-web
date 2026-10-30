# Feature Specification: Root Project Layout and Complete Application Distributions

**Feature Branch**: `innocent-lizard`
**Feature Directory**: `docs/specs/013-root-project-layout`
**Created**: 2026-10-29
**Status**: Specified; implementation planning complete; implementation not started
**Baseline**: `origin/main` at `25c9763`, fetched and matched before specification

**Input**: Consolidate the application into a root Python/JavaScript project, with Python in `src/camply` and frontend source in `src/frontend`. Standard Python builds must produce complete application artifacts. Use one Compose file, one Dockerfile, packaged Gunicorn configuration, nested frontend tooling/functions, a Wrangler configuration file, and specifications under `docs/specs`.

## User Scenarios & Testing

### User Story 1 - Build and install the complete application (Priority: P1)

As a package consumer, I can install a prepared application containing the UI and API without needing the original checkout or JavaScript build tools.

**Why this priority**: A simpler directory tree has limited value if normal distribution builds still omit the UI.

**Independent Test**: Build from a clean checkout, move the source archive outside the repository, rebuild and install it without JavaScript tooling, and use the installed UI and API.

**Acceptance Scenarios**:

1. **Given** a clean checkout and documented source-build prerequisites, **When** a maintainer runs `python -m build` at the root, **Then** it produces one source distribution and one wheel containing the complete frontend and existing runtime resources.
2. **Given** only the source distribution and Python build prerequisites, **When** a consumer rebuilds its wheel outside the checkout without Node or pnpm, **Then** it retains the bundled frontend and installed runtime resources.
3. **Given** a directly built or source-archive-rebuilt wheel with the existing server extra, **When** a consumer launches standalone mode, **Then** the UI, client-side deep links, static assets, and API work from one origin.
4. **Given** a checkout missing JavaScript tooling, a failed frontend build, or missing/corrupted bundled files, **When** a complete distribution is requested, **Then** the build fails with an actionable explanation rather than publishing an incomplete application.
5. **Given** stale previous build output, **When** frontend source or public build settings change, **Then** the next checkout build contains the new output and no removed assets.

### User Story 2 - Develop from one project root (Priority: P1)

As a contributor, I can install, run, test, and check both parts of the application from the root without selecting a nested project.

**Why this priority**: This is the primary structural simplification requested by maintainers.

**Independent Test**: Follow the root development instructions on a clean checkout and run the existing task entrypoints, API generation, and language-specific commands.

**Acceptance Scenarios**:

1. **Given** the reorganized checkout, **When** a contributor uses root Python or pnpm commands, **Then** they discover the canonical manifests, lockfiles, and configuration there.
2. **Given** only Python development prerequisites, **When** a contributor installs the package editably or runs Python-only checks, **Then** no frontend compilation or JavaScript installation is required.
3. **Given** the reorganized tests, **When** the existing task entrypoints run, **Then** they discover the same suites, cassettes, and approved visual baselines without collecting frontend tooling as browser application code.
4. **Given** frontend tooling, **When** a contributor generates types or snapshots, **Then** utilities run from their documented location and temporary output stays outside application source.
5. **Given** the migrated application, **When** installed consumers use existing imports, commands, configuration, optional extras, or stored data, **Then** public behavior and identities remain unchanged.

### User Story 3 - Maintain coherent deployment definitions (Priority: P2)

As an operator, I can use a single container build definition and service configuration, or deploy the frontend through its checked-in Pages configuration, without reconstructing paths manually.

**Why this priority**: Moving source without migrating deployment definitions would break supported delivery paths.

**Independent Test**: Render service/publication configuration, build both image targets, validate installed Gunicorn configuration, and exercise Pages locally without publishing.

**Acceptance Scenarios**:

1. **Given** the root Dockerfile and Compose file, **When** an operator builds and starts the existing distributed stack, **Then** API, frontend, workers, scheduler, database, broker, and monitoring retain existing service relationships and persistent data mappings.
2. **Given** an installed server package outside the checkout, **When** Gunicorn loads its packaged configuration, **Then** it resolves without a checkout-relative file.
3. **Given** the frontend's Wrangler configuration, **When** local Pages validation runs from the documented root task, **Then** it discovers the nested API Function and serves the compiled frontend.
4. **Given** production or preview Pages settings, **When** requests pass through the proxy, **Then** cookies, CSRF, redirect rewriting, cache controls, and configuration/backend error behavior remain intact.
5. **Given** a release or successful main build, **When** release preparation and publication planning run, **Then** package versions, image identities/tags, source selection, and artifact attachments preserve existing contracts.

### User Story 4 - Continue specification and documentation workflows (Priority: P2)

As a maintainer, I can create and resume features under `docs/specs`, and find current documentation without conflicting agent instructions.

**Why this priority**: The reorganization must remain compatible with the project's feature workflow and documentation links.

**Independent Test**: In a disposable checkout, create the next feature under `docs/specs`, resolve it through saved state and an explicit override, and run plan/task setup and prerequisite checks.

**Acceptance Scenarios**:

1. **Given** migrated specifications, **When** feature creation calculates the next number, **Then** it scans `docs/specs` and creates the feature there without recreating root `specs`.
2. **Given** a selected feature under `docs/specs`, **When** planning, tasking, or prerequisite checks run, **Then** they resolve the same documents through the existing active-feature mechanisms.
3. **Given** moved documentation and agent integrations, **When** contributors follow local links, **Then** links resolve and integrations refer to one canonical project instruction source.

### Edge Cases

- Direct wheel builds and ordinary source-first builds must agree on frontend completeness.
- Editable installations and their metadata preparation must not trigger JavaScript builds; an actual standard wheel build remains a complete distribution build.
- Modified frontend inputs or incomplete assets in a source archive must not silently reuse stale output.
- Dependency-install failures, lockfile drift, and missing lazy-loaded map workers must fail verification.
- GitHub build variables must not give Python-served assets an unintended repository URL prefix.
- Type checking must distinguish Python, browser, Node-tooling, and edge-runtime source.
- Nested Pages configuration must resolve root dependencies and output outside its directory.
- Introducing file-based Pages configuration must not silently discard environment-specific backend-origin bindings.
- Compose bind mounts, `.data` storage, entrypoint paths, and image build arguments must survive consolidation.
- Historical specification links must remain valid without rewriting historical descriptions of the old layout.
- Feature numbering must preserve existing duplicate-number directories and advance past the highest number.

## Requirements

### Functional Requirements

- **FR-001**: The repository MUST have one canonical root Python project and one canonical root JavaScript project, retaining dependency locks and supported language versions.
- **FR-002**: Python application source MUST live at `src/camply`; browser source MUST live directly at `src/frontend`, without an additional `src` layer.
- **FR-003**: Root `backend`, `frontend`, `scripts`, `functions`, and `specs` directories MUST be eliminated after migration; frontend utilities and Functions MUST live under `src/frontend/tooling` and `src/frontend/functions`.
- **FR-004**: Root `python -m build`, after documented setup, MUST produce one complete source distribution and wheel without Task, Docker, a running backend, or repository siblings.
- **FR-005**: Source distributions MUST include rebuildable frontend inputs and compiled assets; wheels MUST contain compiled frontend assets and existing runtime resources.
- **FR-006**: Rebuilding an unmodified source distribution MUST retain the frontend without Node or pnpm; installation and execution of prepared wheels MUST not require JavaScript tooling.
- **FR-007**: Standard checkout builds MUST install frontend dependencies from the frozen lockfile, regenerate assets, and fail rather than skip the frontend on missing prerequisites or errors.
- **FR-008**: Editable Python installations and Python-only checks MUST remain independent of JavaScript tooling.
- **FR-009**: Build output, temporary schemas/reports/screenshots, and compiler caches MUST remain outside tracked application source. Explicitly distributed generated assets are permitted inside release archives.
- **FR-010**: Root tasks MUST preserve useful existing commands, with Python and frontend definitions in `taskfiles/python.yaml` and `taskfiles/frontend.yaml`, both operating from the root unless a tool requires another working directory.
- **FR-011**: Python tests MUST move into root `tests`; React unit tests MUST remain colocated; visual baselines MUST live under `tests/frontend/snapshots/baselines`; live-test entrypoints MUST remain available.
- **FR-012**: Container builds MUST use exactly one root Dockerfile with backend and frontend runtime targets; service definitions MUST use exactly one root Compose file.
- **FR-013**: Container consolidation MUST preserve services, image names/tags, non-root runtime users, health checks, ports, build settings, dependencies, environment behavior, and persistent data locations.
- **FR-014**: Gunicorn configuration MUST be installed with the Python server package and usable outside the checkout; infrastructure-only configuration MUST live under `deploy`.
- **FR-015**: Checked-in `src/frontend/wrangler.jsonc` MUST define the existing Pages project identity, compiled output location, and explicit compatibility date, with root tasks for local serving and build validation.
- **FR-016**: The Pages proxy MUST preserve request, response, cookie, redirect, cache, and error behavior in production and preview environments; credentials MUST remain externally supplied.
- **FR-017**: Existing feature documents MUST move to `docs/specs`; Spec-Kit creation defaults, numbering, templates, active-feature handling, and integration guidance MUST support that location.
- **FR-018**: Current documentation MUST move under `docs/development`, `docs/architecture`, and `docs/operations`, with roadmap/checklist documents under `docs`; local links MUST remain valid.
- **FR-019**: `AGENTS.md` MUST be the canonical project instruction source, with Claude and Gemini integration files pointing to it.
- **FR-020**: Imports, CLI commands, public extras, HTTP contracts, database revision identities, provider identities, and Celery wire task names MUST remain compatible.
- **FR-021**: CI, formatting, linting, type checking, code generation, installed-artifact verification, snapshots, smoke tests, and release workflows MUST retain their existing coverage and gates.
- **FR-022**: Implementation MUST amend the obsolete constitution directory rule while preserving optional-dependency and component-boundary requirements.

### Key Entities

- **Checkout**: Authoritative source, dependency locks, tooling, and delivery configuration.
- **Source distribution**: Self-contained archive carrying frontend inputs and prepared UI assets.
- **Wheel**: Installable distribution carrying Python modules, runtime resources, and prepared UI.
- **Feature context**: Specification directory selected by an override or checkout-local state.
- **Deployment target**: Existing container or Pages path with its configuration and bindings.

## Success Criteria

### Measurable Outcomes

- **SC-001**: A clean checkout produces exactly one source archive and one installable archive through the standard root build, with no manual asset staging.
- **SC-002**: Directly built and source-archive-rebuilt applications each serve the home page, a deep link, an asset, and the API from a clean installation outside the checkout.
- **SC-003**: Rebuilding an unchanged source archive, installing prepared artifacts, and running the installed application require zero JavaScript tooling invocations.
- **SC-004**: Every existing automated quality/release gate remains represented, passes after migration, and discovers its expected suites and fixtures.
- **SC-005**: Existing deployment services, image identities, and storage mappings are preserved; Pages validation discovers the proxy without publishing externally.
- **SC-006**: Feature creation and resumed planning/tasking succeed under the documentation tree, with zero unintended root specification directories.
- **SC-007**: Moved local documentation links resolve, and tracked generated build/cache files are eliminated except intentional generated source definitions and approved test fixtures.

## Assumptions

- This deliverable specifies and plans the migration; it does not move application files, deploy services, or publish artifacts.
- One multi-stage Dockerfile may produce two runtime images; distributed services are not merged into one process or image.
- One Python distribution includes all modules and frontend assets; extras select dependencies rather than different wheel contents.
- Python >=3.11 support, Python 3.14 defaults, Node 24, and the package-manager pin remain. New build/deployment development dependencies use their owning package managers; unrelated upgrades are excluded.
- Checkout builds may access dependency registries. Rebuilding a prepared source archive needs Python build dependencies but no frontend dependency download.
- Existing `CAMPLY_FRONTEND_DIR` and supported static-hosting/base-path behavior remain available.
- Pages retains the documented `camply-81r` project. Its backend origin and credentials are operator-supplied, not inferred or committed.
- No database schema, scheduler architecture, authentication flow, provider behavior, or new public CLI feature changes are included.
