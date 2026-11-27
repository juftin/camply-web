# Verification

## Automated checks

- `task fix` & `task check`: Ruff formatting/linting, Import Linter boundaries, Oxlint/Oxfmt, strict `mypy`, and native TypeScript 7 checks passed.
- `task docs:check`: VitePress documentation build and rendered HTML link/anchor validation passed across all docs and specs.
- `task test`: Backend pytest suite (including 22 new synthetic GoingToCamp HTTP/model/CLI/VCR/database regressions and 4 new Alembic seed migration regressions), isolated packaging tests (`test_base_install.py`), release checks, and frontend tests passed.

## Migration lifecycle

The complete Alembic chain was exercised against an isolated temporary SQLite database (`c2f84b9d1a3e`):

- Upgrade to `head` (`c2f84b9d1a3e`): provider IDs `1`–`12` exist, including `Washington State Parks` (`id=12`, `https://washington.goingtocamp.com`).
- Downgrade `-1` (`4d64e0e4ae18`) on an empty catalog: provider `12` is cleanly removed while `1`–`11` remain.
- Re-upgrade to `head`: provider `12` is restored.
- Attempt downgrade `-1` after populating Washington State Parks metadata: rollback fails with `RuntimeError: Washington State Parks has dependent data`, preserving provider `12` and catalog rows.

The temporary database was deleted immediately after verification.

## Live adapter checks

On 2026-11-04, `WashingtonStateParksProvider` ran `sync_metadata()` and `find_availabilities()` against live `https://washington.goingtocamp.com` using an isolated temporary SQLite database outside the repository:

| Provider               | Parks saved (`reservable`) | Campgrounds saved (`reservable`) | Search rows (`Campground`) | Sampled facility          | Window                   | Available units (`electric` / `accessible`) |
| ---------------------- | -------------------------- | -------------------------------- | -------------------------- | ------------------------- | ------------------------ | ------------------------------------------- |
| Washington State Parks | 116 (83)                   | 167 (92)                         | 208 (92)                   | Deception Pass State Park | 2026-11-18 .. 2026-11-20 | 58 (44 / 2)                                 |

- Dynamic overnight category resolution cleanly separated the 92 overnight camping/lodging facilities (`reservable=True`, indexed as searchable campgrounds) from the 75 day-use shelters, marinas/moorage slips, and unmapped locations (`reservable=False`).
- Live `/api/attribute/filterable` (`dict[str, AttributeDefinition]` with `displayName` localization) decoded 33 site-level attributes on sampled Deception Pass sites/cabins (`Electrical Service`, `Service Type`, `ADA Accessible`, `ADA Only`, `Adjacent To`, `Max RVs`, etc.), accurately distinguishing the 2 ADA-accessible units from units merely adjacent to an ADA restroom.
- No live API payloads or reservation identifiers are stored in the repository; all committed tests and VCR cassettes are synthetic.
