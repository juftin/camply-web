# Implementation plan

1. Derive horizontal, stacked, and icon-only SVGs from the supplied camply artwork, outline the embedded lettering, and add dark-theme colors. Keep the supplied PNG and provider logo locally. Verify that all SVGs are self-contained and icon-only assets omit the title.
2. Update `CamplyLogo` to select a layout and app theme while preserving proportions and the deployment URL prefix. Apply the component to existing branding surfaces and the preview catalog. Verify with component tests and browser checks at mobile and desktop sizes in both themes.
3. Replace the placeholder in Meet Justin with the supplied portrait and update SVG/ICO favicons. Verify that the portrait and provider logos load and that the pages do not overflow.
4. Review and refresh DOM and browser snapshots, update frontend branding documentation and the global checklist, and run formatting, lint, type, test, production build, and pre-commit checks before opening the PR.

Constitution check: frontend-only changes retain existing routing, authentication, Shadcn components, and theme state. No API, dependency, database, or migration changes are needed. Browser fixtures use synthetic account data.
