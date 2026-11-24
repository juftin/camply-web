# Contract: Editorial Standard ("More Is Less" & Anti-AI-Slop)

**Feature**: `030-docs-rework` | **Date**: 2026-11-16

All rewritten documentation in **User Documentation**, **Self-Hosting**, and active **Technical and Architectural Documentation** MUST satisfy every rule below. **Technical Reference** pages MUST satisfy Heading, Linking, and Deduplication rules while preserving exact configuration tables; historical `docs/specs/` artifacts are exempt.

## 1. Headings & Openings

- **No decorative emoji prefixes in headings**: Use plain text (`## Authentication`, not `## ⚙️ Authentication` or `## 🚀 Quickstart`).
- **Direct opening**: The first sentence states what the page covers or helps the reader accomplish.
  - _Banned_: `"Welcome to..."`, `"Thank you for your interest..."`, `"This document defines..."`, `"In today's..."`, `"Let's dive into..."`.
- **Consistent title case**: Sentence case for page/section headings (preserving proper nouns like `Pushover`, `Docker Compose`, `Auth0`).

## 2. Brevity & Structure ("More Is Less")

- **Short paragraphs**: Keep prose paragraphs to 2–4 sentences (at most 5 lines in standard Markdown width). Split long explanations into a short lead paragraph plus a command block, list, or table.
- **Show, don't narrate**: Prefer a concrete command or example followed by 1–2 sentences on non-obvious behavior over describing every flag in prose.
- **Tables for multi-option settings**: Present environment variables, deployment comparisons, and auth modes in concise tables rather than multi-paragraph prose.
- **Cut hedging and filler**: Remove redundant transitions (`"Additionally, it is important to note that..."`, `"In order to ensure..."`, `"It should be noted that..."`) and obvious truisms.

## 3. Audience Isolation

- **User Documentation**: No backend module names, database tables, environment variables, Celery/Valkey terms, or spec-deferral jargon. Explain constraints in plain camper terms (e.g., list unsupported legacy features briefly if relevant, without linking to internal task TODO registries).
- **Self-Hosting**: No contributor `task` commands, source-build instructions, or internal PR/migration history. Point maintainers to `Technical Reference` only when an exhaustive table is genuinely needed.
- **Technical & Architectural Documentation**: Explain how subsystems interact and why key tradeoffs exist; avoid copying user quickstarts or listing every single env var already tabulated in `CONFIGURATION.md`.

## 4. Voice & Linking

- **Voice**: Active voice, direct second person (`you`) for instructions, present tense for system behavior.
- **Internal site links**: Use relative Markdown paths (`self-hosting/standalone.md`, `../operations/CONFIGURATION.md`) for pages inside `docs/` rather than `https://github.com/juftin/camply-web/blob/main/docs/...`.
- **Repository-only links**: Use GitHub URLs only for files outside `docs/` (such as `LICENSE` or `deploy/helm/README.md`).
