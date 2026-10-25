# Local screenshot comparison gallery

- Generate an HTML report that opens through `file://` without a server or network access and uses relative links to adjacent PNG files.
- Compare each snapshot's baseline and current screenshot side by side, with a keyboard-accessible reveal slider and highlighted diff as alternative views.
- Search snapshot names/descriptions and filter changed, unchanged, or new views. Identify screenshots without a baseline explicitly.
- Preserve the actual before/after images and change metrics in the generated report even when accepting new baselines.
- Support rebuilding a report from existing baseline/current captures without starting Vite or Chromium.
- Keep generated HTML local and in CI artifacts; commit the viewer source and keep PNGs as separate local files.

Acceptance: automated synthetic-image tests cover comparison, dimension changes, missing baselines, relative image links, filename encoding and escaping. A browser test opens an exported report from a temporary directory through `file://`, checks controls and local image loading, and records desktop/mobile evidence.
