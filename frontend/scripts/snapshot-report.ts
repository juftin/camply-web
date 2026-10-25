/** Compare screenshot captures and generate an HTML gallery of local PNG files. */
import fs from "node:fs";
import path from "node:path";
import pixelmatch from "pixelmatch";
import { PNG } from "pngjs";

export interface SnapshotResult {
  name: string;
  description: string;
  viewport: string;
  theme: "light" | "dark";
  status: "UNCHANGED" | "MODIFIED" | "NEW";
  diffPixels: number;
  diffPercentage: number;
  baselinePath: string | null;
  currentPath: string;
  diffPath: string | null;
  beforeImage: string | null;
  afterImage: string;
  diffImage: string | null;
  width: number;
  height: number;
  beforeWidth: number;
  afterWidth: number;
}

type SnapshotMetadata = Pick<
  SnapshotResult,
  "name" | "description" | "viewport" | "theme"
>;

/** Pad both screenshots to a common canvas without rescaling their contents. */
function normalizeImage(source: PNG, width: number, height: number): PNG {
  if (source.width === width && source.height === height) return source;
  const target = new PNG({ width, height });
  PNG.bitblt(source, target, 0, 0, source.width, source.height, 0, 0);
  return target;
}

/** Link to an image beside the report, preserving special filename characters. */
function imageUrl(snapshotsDir: string, imagePath: string): string {
  return path
    .relative(snapshotsDir, imagePath)
    .split(path.sep)
    .map(encodeURIComponent)
    .join("/");
}

/** Preserve the before image before optionally accepting the current baseline. */
export function recordSnapshot(
  snapshotsDir: string,
  metadata: SnapshotMetadata,
  currentBuffer: Buffer,
  {
    update = false,
    createBaseline = true,
  }: { update?: boolean; createBaseline?: boolean } = {},
): SnapshotResult {
  const baselinePath = path.join(
    snapshotsDir,
    "baselines",
    `${metadata.name}.png`,
  );
  const currentPath = path.join(
    snapshotsDir,
    "current",
    `${metadata.name}.png`,
  );
  const beforePath = path.join(snapshotsDir, "before", `${metadata.name}.png`);
  const diffPath = path.join(
    snapshotsDir,
    "diffs",
    `${metadata.name}-diff.png`,
  );
  for (const directory of ["baselines", "current", "before", "diffs"]) {
    fs.mkdirSync(path.join(snapshotsDir, directory), { recursive: true });
  }
  const baselineBuffer = fs.existsSync(baselinePath)
    ? fs.readFileSync(baselinePath)
    : null;
  const current = PNG.sync.read(currentBuffer);
  const result: SnapshotResult = {
    ...metadata,
    status: baselineBuffer ? "UNCHANGED" : "NEW",
    diffPixels: 0,
    diffPercentage: 0,
    baselinePath: baselineBuffer ? beforePath : null,
    currentPath,
    diffPath: null,
    beforeImage: null,
    afterImage: imageUrl(snapshotsDir, currentPath),
    diffImage: null,
    width: current.width,
    height: current.height,
    beforeWidth: 0,
    afterWidth: current.width,
  };
  if (baselineBuffer) {
    fs.writeFileSync(beforePath, baselineBuffer);
    const baseline = PNG.sync.read(baselineBuffer);
    const width = Math.max(current.width, baseline.width);
    const height = Math.max(current.height, baseline.height);
    const before = normalizeImage(baseline, width, height);
    const after = normalizeImage(current, width, height);
    const diff = new PNG({ width, height });
    const pixels = pixelmatch(
      after.data,
      before.data,
      diff.data,
      width,
      height,
      {
        threshold: 0.1,
        alpha: 0.5,
        diffColor: [255, 0, 80],
      },
    );
    const percentage = (pixels / (width * height)) * 100;
    result.beforeImage = imageUrl(snapshotsDir, beforePath);
    result.width = width;
    result.height = height;
    result.beforeWidth = baseline.width;
    if (
      (percentage > 0.05 && pixels > 10) ||
      current.width !== baseline.width ||
      current.height !== baseline.height
    ) {
      const diffBuffer = PNG.sync.write(diff);
      fs.writeFileSync(diffPath, diffBuffer);
      result.status = "MODIFIED";
      result.diffPixels = pixels;
      result.diffPercentage = percentage;
      result.diffPath = diffPath;
      result.diffImage = imageUrl(snapshotsDir, diffPath);
    }
  } else {
    fs.rmSync(beforePath, { force: true });
  }
  if (!result.diffPath) fs.rmSync(diffPath, { force: true });
  fs.writeFileSync(currentPath, currentBuffer);
  if (update || (!baselineBuffer && createBaseline))
    fs.writeFileSync(baselinePath, currentBuffer);
  return result;
}

/** Generate a local HTML viewer with relative links to the comparison images. */
export function generateHtmlReport(results: SnapshotResult[]): string {
  const template = fs.readFileSync(
    new URL("./snapshot-gallery.html", import.meta.url),
    "utf8",
  );
  const comparisons = results.map(
    ({
      name,
      description,
      viewport,
      theme,
      status,
      diffPercentage,
      beforeImage,
      afterImage,
      diffImage,
      width,
      height,
      beforeWidth,
      afterWidth,
    }) => ({
      name,
      description,
      viewport,
      theme,
      status,
      diffPercentage,
      beforeImage,
      afterImage,
      diffImage,
      width,
      height,
      beforeWidth,
      afterWidth,
    }),
  );
  const data = JSON.stringify(comparisons).replace(
    /[<>&\u2028\u2029]/g,
    (character) =>
      `\\u${character.charCodeAt(0).toString(16).padStart(4, "0")}`,
  );
  return template.replace("__SNAPSHOT_DATA__", () => data);
}
