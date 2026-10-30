# Artifact and Feature State Model

This refactor adds no database tables, columns, migrations, or domain entities. Existing database revision IDs, provider IDs, and persisted application data remain unchanged. The relevant state is filesystem/build state.

## Project checkout

- Root Python/JavaScript manifests, locks, language pins, and build configuration are authoritative inputs.
- `src/camply` owns Python modules/runtime resources; `src/frontend` owns browser source, public files, Functions, and tooling.
- Compiled output is disposable and ignored. Its presence does not permit a checkout standard build to skip compilation.

## Prepared frontend inventory

- Generated at `build/frontend-manifest.json`; schema version is private build metadata, not a public API.
- Records distribution version, build-recipe identity, digest of enumerated frontend build inputs/public settings, and a sorted mapping of relative asset paths to content digests.
- Input enumeration includes frontend source/public files, referenced root build/TypeScript configuration, package metadata, and lock/manager settings. It excludes dependencies, caches, reports, and the generated output itself.
- Inventory paths must be relative, normalized, unique, and confined to the UI root. Every recorded file must exist with its expected digest; unexpected files invalidate the exact inventory. It must include `index.html` and emitted assets, including map worker chunks.
- Only explicit public frontend build settings enter the recipe digest; secrets or arbitrary process environment contents are not serialized.

## Distribution relationships

```text
checkout inputs
    -> frozen frontend install/build
    -> build/frontend + frontend-manifest.json
    -> sdist: source inputs + src/camply/server/static + manifest
    -> extracted sdist: validate inputs/assets, reuse prepared UI
    -> wheel: camply modules/resources + camply/server/static
    -> clean installed application
```

Direct checkout wheels use the same frontend build and inventory validation before mapping the assets into the wheel. The inventory is an integrity/freshness check for a local build, not a cryptographic authenticity guarantee for untrusted archives.

| State                           | Allowed transition                                                        | Failure behavior                                                       |
| ------------------------------- | ------------------------------------------------------------------------- | ---------------------------------------------------------------------- |
| Editable checkout               | Install editable Python metadata/package                                  | Never probe or invoke JavaScript tooling.                              |
| Standard checkout build         | Compile from frozen inputs and publish complete artifact                  | Missing tool/install/build/output fails.                               |
| Valid extracted sdist           | Verify root archive metadata, inputs, and prepared inventory; build wheel | No JavaScript invocation.                                              |
| Changed/corrupt extracted sdist | Request a fresh complete source build                                     | Actionable failure; do not silently drop or reuse inconsistent assets. |
| Installed wheel                 | Load package-owned resources or explicit frontend override                | Existing runtime validation remains in effect.                         |

## Spec-Kit feature context

- Canonical feature identity is the complete directory name, not its numeric prefix alone.
- Features live under `docs/specs`; existing duplicate prefixes retain distinct identities.
- Resolution remains explicit `SPECIFY_FEATURE_DIRECTORY`, then `.specify/feature.json`'s relative `feature_directory`.
- Migrating `specs/<feature>` to `docs/specs/<feature>` changes location, not feature identity.
- Saved pointers are machine-local. Read-only/no-persist operations must not rewrite them.

## Deployment configuration

Wrangler's project identity/output/date are versioned configuration. Production/preview backend-origin bindings and credentials are externally managed runtime state. Container service names, image identities, volume names, and environment-variable names remain stable while configuration source paths move.
