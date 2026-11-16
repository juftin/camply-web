# Feature Specification: Documentation Rework

**Feature Branch**: `030-docs-rework`

**Created**: 2026-11-16

**Status**: Draft

**Input**: User description: "Let's write a spec to re-work the camply documentation. It should be focused on four perspectives: User Documentation, Self-Hosting, Technical and Architectural Documentation, and Technical Reference. The audience for the technical documentation is smaller so the docs should default to showing user and maintainer documentation. The docs should focus on readability, more is less. Focus on the docs not sounding like they're complete ai slop - they're meant to be read by humans."

## Clarifications

### Session 2026-11-16

- Q: How should the two default perspectives (User Documentation and Self-Hosting) be separated from the two secondary perspectives (Technical and Architectural Documentation and Technical Reference) in site navigation? → A: Scoped sidebars with a secondary navigation menu—the default landing page and sidebar show only User Documentation and Self-Hosting, while Technical and Architectural Documentation and Technical Reference sit behind a secondary navigation entry and switch to their own scoped sidebar when opened.
- Q: Should internal engineering artifacts (feature specifications, roadmaps, checklists, and agent-workflow guides) be published as pages on the documentation site or kept repository-only on GitHub? → A: Publish all existing specifications, roadmaps, checklists, and agent guides as pages inside **Technical Reference**, and exclude or deprioritize them in site search so User Documentation and Self-Hosting results remain primary.
- Q: How deeply should the prose rewrite apply to **Technical and Architectural Documentation** and **Technical Reference** compared to **User Documentation** and **Self-Hosting**? → A: Apply the full "more is less" human-prose rewrite to User Documentation, Self-Hosting, and active Technical and Architectural Documentation guides; clean up structure, headings, and links in Technical Reference while preserving exact setting tables and keeping historical feature specs intact.
- Q: When overlapping pages are consolidated into the four perspectives, how should legacy documentation page URLs be handled? → A: Preserve `/docs/`, `/docs/using-camply`, and repo-governed paths (feature specs, roadmap, checklist); reorganize and rename other documentation page paths cleanly to match the four perspectives without maintaining redirects for retired subpages.

## User Scenarios & Testing

### User Story 1 - Default Documentation View for Users and Self-Hosters (Priority: P1)

A visitor opens the documentation site (or repository README) and immediately sees the two primary tracks: **User Documentation** and **Self-Hosting**. Navigation, default sidebar groups, and landing actions focus on those two audiences without exposing architectural deep dives, exhaustive reference tables, or internal planning/agent documents by default.

**Why this priority**: Most readers are campers or instance maintainers looking for practical steps. Putting smaller-audience engineering, architecture, and reference materials into the default navigation creates noise and buries everyday workflows.

**Independent Test**: Open the documentation landing page and repository README as a new visitor, inspect the top navigation, default sidebar, and landing links, and verify that only User Documentation and Self-Hosting sections are shown by default while Technical and Architectural Documentation and Technical Reference sit behind separate secondary entry points.

**Acceptance Scenarios**:

1. **Given** a reader opens the documentation home page, **When** they scan the page and default sidebar, **Then** they see clear paths for **User Documentation** (web app and command line) and **Self-Hosting**, with no architecture blueprints, planning checklists, or reference catalogs expanded in the default sidebar.
2. **Given** a reader is browsing any User Documentation or Self-Hosting page, **When** they inspect the navigation bar and sidebar, **Then** technical architecture and reference sections do not crowd or expand alongside user and self-hosting guides.
3. **Given** a visitor opens the repository README, **When** they read from top to bottom, **Then** they find a brief explanation of what camply does, links to the hosted app and User Documentation, a concise Self-Hosting pointer, and concise secondary pointers to Technical and Architectural Documentation and Technical Reference.

---

### User Story 2 - Clear User Documentation for Web App and CLI (Priority: P1)

A camper wants to monitor a campground—either through the web app or from their terminal—and looks up how to search, set dates and weekday filters, understand stay-length behavior, and receive Pushover alerts. Every user page gets straight to the point with short paragraphs, concrete examples, and clear distinctions between web and terminal workflows.

**Why this priority**: Helping campers find and watch campsites is the core purpose of camply. Current user docs mix in implementation caveats, deferred-feature inventories, and dense prose that slow readers down.

**Independent Test**: Have a reader follow User Documentation to (a) create a weekend-only web scan with Pushover alerts and (b) run an equivalent terminal search, verifying that every step is self-contained without needing to read Self-Hosting, Technical and Architectural Documentation, or Technical Reference pages.

**Acceptance Scenarios**:

1. **Given** a camper using the web app, **When** they read User Documentation, **Then** they can find a campground, configure a scan (dates, minimum nights, weekday/weekend filters, site preferences), and connect Pushover notifications without encountering self-hosting or backend terminology.
2. **Given** a terminal user reading the command-line guide, **When** they look up installation, location discovery, and availability watching, **Then** they see concise command examples, plain-English rules (such as how nights, weekends, and stay length work), and expected output without spec-status commentary or deferred-feature checklists interrupting the workflow.
3. **Given** an updated web or CLI user workflow, **When** a reader checks any User Documentation page, **Then** each topic appears in one authoritative place rather than being repeated across the overview, user guide, and standalone setup guide.

---

### User Story 3 - Focused Self-Hosting Documentation for Maintainers (Priority: P1)

A maintainer wants to run their own camply instance—on a single machine, with containers, or on a cluster—and configure authentication, alerts, storage, and updates. The **Self-Hosting** track presents one clear path per deployment size, explains required vs. common settings in plain tables, and leaves exhaustive configuration catalogs and source-build details out of operator quickstarts.

**Why this priority**: Self-hosters need reliable, unambiguous setup and upgrade steps without jumping across overlapping quickstarts, operations references, and developer guides.

**Independent Test**: Follow each documented Self-Hosting path (single-machine standalone, container stack, and cluster deployment) from start to first working scan and notification, verifying that all required settings, initial catalog sync steps, security warnings, and backup instructions are complete within Self-Hosting.

**Acceptance Scenarios**:

1. **Given** a maintainer choosing how to self-host, **When** they open Self-Hosting, **Then** they can compare the single-machine, container-stack, and cluster options at a glance and jump straight to the matching guide.
2. **Given** a maintainer setting up authentication and notifications, **When** they read the Self-Hosting configuration guide, **Then** every required setting, safe default, and security warning (such as replacing default admin login before sharing an instance) is stated once in a scannable layout without duplicating a separate operations reference page.
3. **Given** a maintainer upgrading or backing up an instance, **When** they check Self-Hosting maintenance guidance, **Then** backup, restore, migration, and troubleshooting steps are concise, actionable, and free of contributor-only packaging details.

---

### User Story 4 - Scoped Technical & Architectural Documentation and Technical Reference (Priority: P2)

A contributor or advanced operator wants either conceptual/engineering guidance (local development setup, testing/quality gates, polling/provider/notification/API/frontend architecture, and release flows) or lookup material (complete environment variable reference, runtime/packaging details, specifications catalog, and project planning/agent references). They reach **Technical and Architectural Documentation** and **Technical Reference** via clearly separated secondary entry points without those sections spilling into the default User and Self-Hosting view.

**Why this priority**: The audience for deep technical, architectural, and reference docs is smaller than for User Documentation and Self-Hosting. Keeping both tracks well structured—but separated from the default experience—serves engineers and advanced maintainers without overwhelming everyday readers.

**Independent Test**: Navigate from the documentation site's secondary entry points into (a) Technical and Architectural Documentation (development setup, quality gates, system architecture) and (b) Technical Reference (exhaustive configuration reference, runtime/packaging reference, specifications catalog), verifying that topics do not overlap across the two tracks and remain isolated from the default User and Self-Hosting sidebar.

**Acceptance Scenarios**:

1. **Given** a contributor looking to understand the system or set up a dev environment, **When** they open **Technical and Architectural Documentation**, **Then** they find one consolidated path for local development, coding and testing standards, system architecture blueprints, and release workflows—without overlapping quickstarts copied between contributing and developer guides.
2. **Given** an engineer or advanced maintainer looking up exact settings, packaging rules, or specifications, **When** they open **Technical Reference**, **Then** they find scannable reference material (full environment-variable catalog, runtime/packaging specs, and specifications/planning indexes) separated from conceptual architecture narratives.
3. **Given** internal planning, specification, or agent-oriented files retained in the repository for contributor workflows, **When** the documentation site is built, **Then** those files are published inside **Technical Reference** and excluded or deprioritized in site search rather than appearing in User Documentation, Self-Hosting, primary navigation, or top everyday search results.

---

### User Story 5 - Human-Readable, Low-Noise Writing Style (Priority: P1)

Every page across all four perspectives follows a strict "more is less" editorial standard so the documentation reads as if written by a careful human engineer rather than generated boilerplate. Pages are short, direct, and scannable, cutting filler intros, repetitive callouts, emoji-decorated headings, and narration of code internals.

**Why this priority**: Readability and human tone are explicit project goals. Reorganizing navigation without rewriting bloated, repetitive prose would leave the underlying reading experience broken.

**Independent Test**: Audit every rewritten page against an explicit editorial checklist (paragraph length, absence of banned filler/boilerplate patterns, no cross-page duplication, consistent terminology, and working examples) and confirm all pages pass before publication.

**Acceptance Scenarios**:

1. **Given** any page across all four tracks, **When** a reader scans the page, **Then** headings are plain text without decorative emoji clutter, opening sentences state directly what the page helps the reader do, and paragraphs stay brief and concrete.
2. **Given** a technical detail that only matters to code contributors or exhaustive lookup, **When** authoring User Documentation or Self-Hosting guides, **Then** that detail is omitted or placed in Technical and Architectural Documentation or Technical Reference rather than padded into user-facing paragraphs.
3. **Given** a reader searching the documentation site for common tasks (like "notifications", "weekends", "login", or "backup"), **When** results appear, **Then** User Documentation and Self-Hosting pages appear clearly at the top rather than outdated specs or internal checklists.

---

### Edge Cases

- **Existing inbound links and core entrypoints**: Links from the web application footer and packaged app routes (`/docs/` and `/docs/using-camply`), as well as repository-governed paths (such as feature specs, roadmap, and checklist), MUST continue to resolve cleanly. Other consolidated or renamed documentation subpages MAY adopt new paths aligned with the four perspectives without keeping legacy redirects, provided all internal site links are updated.
- **Bundled vs. standalone docs mirror**: Documentation must remain accurate whether viewed inside a self-hosted instance, on the hosted site, or directly as Markdown files in the GitHub repository—links between published pages must not needlessly kick readers out to external repository blob URLs when the target page is part of the same site.
- **CLI vs. Web terminology**: Pages covering features shared by the web app and CLI (such as night/weekday selection and stay length) must explain the shared mental model once and call out interface differences explicitly without forcing readers to infer them.
- **Boundary between Technical & Architectural Docs and Technical Reference**: Architectural explanations (how polling, providers, notifications, APIs, and development workflows work) belong in **Technical and Architectural Documentation**, while exhaustive tables, exact contracts, and specification/planning indexes belong in **Technical Reference**, avoiding cross-track duplication.
- **Repository-required internal files**: Engineering workflow files that repository tooling or contributors depend on in their current locations (such as feature specs, the project checklist, or repository agent instructions) must keep working in-repo without polluting the default reader experience on the docs site.
- **Broken or stale references**: References to obsolete directory names, superseded setup commands, or deleted pages must be caught automatically during documentation verification.

## Requirements

### Functional Requirements

- **FR-001 — Four-perspective structure with two-perspective default**: Documentation MUST be organized around four distinct perspectives:
  1. **User Documentation**
  2. **Self-Hosting**
  3. **Technical and Architectural Documentation**
  4. **Technical Reference**
     The documentation site MUST default to presenting **User Documentation** and **Self-Hosting** in its landing content, primary navigation, and default sidebar.
- **FR-002 — Scoped sidebars and secondary navigation for technical and reference tracks**: **Technical and Architectural Documentation** and **Technical Reference** MUST be placed behind a secondary navigation entry (such as a compact secondary menu or header/footer links) rather than appearing in the default User Documentation and Self-Hosting sidebar. When a reader opens either secondary track, the sidebar MUST scope to that track's own pages rather than mixing all four perspectives into one long sidebar.
- **FR-003 — Internal artifact containment & search hygiene**: Internal planning, tracking, specification, and agent-workflow documents (such as feature specs, checklists, roadmaps, and agent-specific troubleshooting/tooling notes) MUST remain published inside **Technical Reference**, MUST NOT appear in User Documentation or Self-Hosting navigation, and MUST be excluded from or strictly deprioritized in default site search so everyday user and self-hosting queries surface User Documentation and Self-Hosting pages first.
- **FR-004 — Single canonical home per topic**: Overlapping documents MUST be consolidated so each topic has one authoritative page in its appropriate perspective:
  - **User Documentation**: Web app usage (finding campgrounds, creating/editing scans, receiving alerts) and CLI usage (installation, discovery, availability watching, night/stay filters).
  - **Self-Hosting**: Choosing a deployment path, standalone single-machine hosting, container/cluster hosting, everyday configuration (auth, notifications, storage, public URL), and backups/upgrades/troubleshooting.
  - **Technical and Architectural Documentation**: Contributor onboarding & local development workflow, coding & testing standards, system architecture (polling, data model, providers, notifications, API/security, frontend), and release operations.
  - **Technical Reference**: Exhaustive environment-variable catalog, runtime/packaging specifications, feature specifications catalog, and project planning/agent references.
- **FR-005 — Editorial standard ("More Is Less" & Anti-AI-Slop)**: All active documentation MUST adhere to a documented editorial standard. The full "more is less" prose rewrite MUST apply to **User Documentation**, **Self-Hosting**, and active **Technical and Architectural Documentation** guides; **Technical Reference** pages MUST receive structural, heading, and link cleanup without stripping exact setting tables, and historical feature specifications MUST remain intact. The editorial standard MUST enforce:
  - Plain, direct opening sentences (no "Welcome to...", "Thank you for your interest...", or meta-narration about what the document does).
  - Plain-text headings free of decorative emoji prefixes.
  - Short, scannable paragraphs (typically 2–4 sentences), concrete commands/examples, and structured tables for multi-option settings instead of wall-of-text prose.
  - Active voice, second person ("you") for task guides, and zero speculative or redundant filler.
  - Audience-appropriate depth: no internal database migration histories, spec caveats, or contributor-only workflows inside User Documentation or Self-Hosting guides.
- **FR-006 — Consistent internal linking**: Links between pages within the documentation site MUST use relative site links rather than external repository URLs, while links to repository-only assets (such as license files or chart directories outside the site) MUST use valid repository links.
- **FR-007 — README alignment**: The repository README MUST be concise, mirror the default User Documentation + Self-Hosting focus, and link cleanly into the reworked User Documentation, Self-Hosting, Technical and Architectural Documentation, and Technical Reference entry points without duplicating multi-step guides.
- **FR-008 — Accuracy against current camply behavior**: Every command, environment variable, default value, authentication mode, notification setting, provider note, and CLI flag documented in the reworked pages MUST match current application behavior, with stale references (such as obsolete directory layouts or retired tooling instructions) removed.
- **FR-009 — Existing site integration preserved**: Reworking the documentation MUST preserve all existing entry points from the application (the footer link, bundled `/docs/` serving, and `/docs/using-camply`), local search functionality, light/dark readability, and existing build/link verification checks. Consolidated or renamed subpages outside those preserved entry points and repo-governed paths MAY move to cleaner four-perspective URLs.

### Key Entities

- **Documentation Perspective**: One of the four audience-oriented tracks (`User Documentation`, `Self-Hosting`, `Technical and Architectural Documentation`, or `Technical Reference`), with its own tone, assumed prerequisites, and scoped navigation.
- **Canonical Guide**: The single authoritative page for a user task, hosting workflow, architectural topic, or reference catalog, replacing fragmented or duplicated pages.
- **Editorial Checklist**: The set of human-readability and anti-slop rules used to review rewritten pages before considering the rework complete.
- **Internal Reference**: Engineering planning, specification, or agent-workflow documents kept in the repository for development governance, published inside Technical Reference, and excluded from or deprioritized in default site search.

## Success Criteria

### Measurable Outcomes

- **SC-001 — Clean default navigation**: On initial load of the documentation site, 100% of visible top-level sidebar groups and landing-page primary actions belong to **User Documentation** or **Self-Hosting**; **Technical and Architectural Documentation** and **Technical Reference** each require at most 1 click to reach from a secondary navigation entry.
- **SC-002 — Eliminated duplication**: Total redundant overlap across all four perspectives is eliminated so that core topics (quickstarts, authentication, Pushover setup, database backup, CLI usage, local dev setup, architecture overviews, and configuration lookups) each have exactly 1 canonical page.
- **SC-003 — Concise, scannable pages**: Every rewritten page in **User Documentation**, **Self-Hosting**, and active **Technical and Architectural Documentation** passes an editorial audit with zero emoji-prefixed headings, zero filler/welcome boilerplate, no prose paragraphs exceeding 5 lines in standard view, and at least a 30% net reduction in redundant prose across consolidated guides while keeping all required instructions intact (historical feature specs and exhaustive reference tables are exempt from prose condensation).
- **SC-004 — Zero broken links or stale paths**: Automated documentation verification passes with 0 broken internal links, 0 missing anchors, 0 broken assets, and 100% resolution of preserved entry routes (`/docs/` and `/docs/using-camply`) and repo-governed paths.
- **SC-005 — Task completion by perspective**: A reader following only **User Documentation** can complete web scan setup and CLI monitoring without consulting other tracks; a maintainer following only **Self-Hosting** can deploy, secure, configure alerts, and back up an instance without consulting Technical and Architectural Documentation; a contributor can locate development setup, architecture, and reference specs from their respective secondary tracks.

## Assumptions

- **Existing publishing pipeline stays intact**: The documentation site continues to be built into static HTML, bundled inside application releases and container images under `/docs/`, and published via the existing CI/Pages workflow; this rework changes information architecture, navigation scoping, and page content rather than replacing the documentation platform.
- **Primary hosted app remains first-class**: User Documentation treats `camply.rocks` (and any self-hosted web instance) alongside the `camply` CLI as the primary ways people use camply.
- **Specs and internal docs remain in-repo**: Existing feature specifications (`docs/specs/`), `docs/PLAN.md`, `docs/CHECKLIST.md`, and repository agent rules remain in the repository so Spec-Kit and existing engineering governance continue to function without breaking historical links.
- **English-only scope**: Documentation remains in English; localization/i18n is outside the scope of this rework.
- **Code behavior is unchanged**: This specification covers documentation structure, navigation, and prose; it does not alter application features, CLI flags, or configuration keys (though it corrects any documentation that is out of sync with current behavior).
