// @vitest-environment node
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { afterEach, describe, expect, it } from "vitest";
import { PNG } from "pngjs";
import { generateHtmlReport, recordSnapshot } from "./snapshot-report";

const directories: string[] = [];
const scenario = {
  name: "sample",
  description: "Synthetic campsite view",
  viewport: "375x812",
  theme: "light" as const,
};

function image(red: number, width = 20, height = 20): Buffer {
  const png = new PNG({ width, height });
  for (let offset = 0; offset < png.data.length; offset += 4) {
    png.data[offset] = red;
    png.data[offset + 3] = 255;
  }
  return PNG.sync.write(png);
}

function directory(): string {
  const result = fs.mkdtempSync(path.join(os.tmpdir(), "camply-gallery-unit-"));
  directories.push(result);
  return result;
}

afterEach(() => {
  for (const value of directories.splice(0))
    fs.rmSync(value, { recursive: true, force: true });
});

describe("portable screenshot reports", () => {
  it("retains the old baseline and comparison after accepting an update", () => {
    const root = directory();
    const before = image(0);
    const after = image(255);
    recordSnapshot(root, scenario, before);
    const result = recordSnapshot(root, scenario, after, { update: true });
    expect(result.status).toBe("MODIFIED");
    expect(result.diffPercentage).toBeGreaterThan(0);
    expect(fs.readFileSync(path.join(root, "baselines/sample.png"))).toEqual(
      after,
    );
    expect(fs.readFileSync(result.baselinePath!)).toEqual(before);
    expect(result.beforeImage).not.toBe(result.afterImage);
    expect(result.diffImage).toMatch(/^data:image\/png;base64,/);
    const html = generateHtmlReport([result]);
    fs.rmSync(root, { recursive: true, force: true });
    expect(html).toContain(result.beforeImage!);
    expect(html).toContain(result.afterImage);
    expect(html).not.toContain(root);
    expect(html).not.toMatch(/(?:src|href)="https?:/);
  });

  it("identifies new snapshots without pretending there was a before image", () => {
    const result = recordSnapshot(directory(), scenario, image(0));
    expect(result.status).toBe("NEW");
    expect(result.baselinePath).toBeNull();
    expect(result.beforeImage).toBeNull();
    expect(result.diffImage).toBeNull();
  });

  it("keeps unchanged screenshots free of stale diff files", () => {
    const root = directory();
    recordSnapshot(root, scenario, image(0));
    recordSnapshot(root, scenario, image(255));
    const result = recordSnapshot(root, scenario, image(0));
    expect(result.status).toBe("UNCHANGED");
    expect(result.diffPixels).toBe(0);
    expect(result.diffPath).toBeNull();
    expect(fs.existsSync(path.join(root, "diffs/sample-diff.png"))).toBe(false);
  });

  it("does not accept new baselines while rebuilding a report", () => {
    const root = directory();
    const result = recordSnapshot(root, scenario, image(0), {
      createBaseline: false,
    });
    expect(result.status).toBe("NEW");
    expect(fs.existsSync(path.join(root, "baselines/sample.png"))).toBe(false);
  });

  it("aligns changed image sizes without stretching either screenshot", () => {
    const root = directory();
    recordSnapshot(root, scenario, image(0, 20, 20));
    const result = recordSnapshot(root, scenario, image(255, 30, 40));
    expect(result.status).toBe("MODIFIED");
    for (const value of [result.beforeImage!, result.afterImage]) {
      const png = PNG.sync.read(Buffer.from(value.split(",")[1], "base64"));
      expect([png.width, png.height]).toEqual([30, 40]);
    }
  });

  it("escapes metadata so it cannot break out of the embedded JSON", () => {
    const result = recordSnapshot(
      directory(),
      { ...scenario, description: '</script><img src=x onerror="alert(1)">' },
      image(0),
    );
    const html = generateHtmlReport([result]);
    expect(html).not.toContain(result.description);
    const embedded = html.match(
      /<script id="snapshot-data" type="application\/json">([\s\S]*?)<\/script>/,
    )![1];
    expect(JSON.parse(embedded)[0].description).toBe(result.description);
  });
});
