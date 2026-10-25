# Local screenshot comparison gallery

- Generate a standalone HTML report that opens through `file://` without a server, network access, or adjacent image files.
- Compare each snapshot's baseline and current screenshot side by side, with a keyboard-accessible reveal slider and highlighted diff as alternative views.
- Search snapshot names/descriptions and filter changed, unchanged, or new views. Identify screenshots without a baseline explicitly.
- Preserve the actual before/after images and change metrics in the generated report even when accepting new baselines.
- Support rebuilding a report from existing baseline/current captures without starting Vite or Chromium.
- Keep generated HTML local and in CI artifacts; commit the viewer source rather than embedded image payloads.

Acceptance: automated synthetic-image tests cover comparison, dimension changes, missing baselines, embedding and escaping. A browser test opens an exported report from a temporary directory through `file://`, checks controls and offline images, and records desktop/mobile evidence.
