# Style Guide

All code and documentation in `camply` must follow these engineering standards.

## Python (backend)

- **Type hints:** Annotate every function and method signature, including tests and fixtures. Verify with `task backend:check` (`mypy`).
- **Validation:** Use Pydantic v2 `BaseModel` schemas and `pydantic-settings` for configuration instead of raw dicts.
- **Async I/O:** Keep database queries and upstream HTTP calls `async`.
- **Logging:** Use `structlog` for structured logging; never leave `print()` calls in application code.
- **Docstrings:** Use NumPy-style docstrings for public modules, classes, and functions.
- **Layer boundaries:** Keep imports respecting `cli | server | worker -> core -> providers -> db -> __about__` (`task backend:imports`).

## React and TypeScript (frontend)

- **Components:** Write functional arrow-function components with strict TypeScript types (never `any`).
- **Styling:** Use Tailwind CSS utility classes and Shadcn/UI primitives in `src/frontend/components/ui/` (wrap primitives instead of editing them directly).
- **Server state:** Use TanStack Query hooks backed by `src/frontend/lib/api.ts` and the OpenAPI-generated schema.
- **Formatting and linting:** Pass `oxlint` and `oxfmt` (`task frontend:lint`, `task frontend:check`).

## Testing

- **Test with changes:** Add or update unit and integration tests alongside behavior changes.
- **Mock upstream HTTP:** Record external provider API calls with `pytest-vcr`; never hit live booking APIs in unit tests.
- **Reproduce bugs first:** Write a failing regression test before fixing a bug.

## Documentation

Keep active documentation concise, direct, and free of filler:

- Use plain-text headings with no decorative emoji prefixes.
- Start pages with what the reader needs to know or do—avoid `"Welcome to..."` or `"This document defines..."` openers.
- Keep paragraphs short (2–4 sentences); prefer concrete commands and compact tables over walls of text.
- Use relative Markdown links between pages inside `docs/`.
