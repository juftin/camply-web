/** Verify screenshot comparisons load local PNG files through file://. */
import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { pathToFileURL } from "node:url";
import { chromium, expect } from "@playwright/test";
import { generateHtmlReport, recordSnapshot } from "./snapshot-report";

/** Render a deterministic example UI for a before/after fixture. */
function samplePage(found: boolean): string {
  return `<!doctype html><html lang="en"><style>
    body { margin: 0; padding: 28px; font: 16px system-ui; background: #f3f7f6; color: #102d28; }
    h1 { font-size: 25px; margin: 0 0 8px; } p { color: #526b66; }
    section { padding: 20px; margin-top: 22px; background: white; border: 1px solid #bfd3cb; border-radius: 12px; }
    strong { color: #087f5b; } .site { padding: 12px 0; border-top: 1px solid #dbe7e0; }
  </style><body><h1>Camply campsite results</h1><p>Synthetic campground · July 2027</p><section>
    ${found ? '<strong>2 matching campsites</strong><p>Check-in – check-out</p><div class="site">Site 042 · Jul 1 – Jul 3 · 2 nights</div><div class="site">Site 048 · Jul 5 – Jul 8 · 3 nights</div>' : "<strong>Waiting for the first check</strong><p>New matching openings will appear here.</p>"}
  </section></body></html>`;
}

async function main(): Promise<void> {
  const temporary = fs.mkdtempSync(
    path.join(os.tmpdir(), "camply-gallery-browser-"),
  );
  const output = path.resolve(
    import.meta.dirname,
    "../../../tmp/snapshot-gallery",
  );
  fs.mkdirSync(output, { recursive: true });
  const browser = await chromium.launch({ headless: true });
  try {
    const page = await browser.newPage({
      viewport: { width: 620, height: 360 },
    });
    page.setDefaultTimeout(10000);
    await page.setContent(samplePage(false));
    const before = await page.screenshot();
    await page.setViewportSize({ width: 580, height: 400 });
    await page.setContent(samplePage(true));
    const after = await page.screenshot();
    const source = path.join(temporary, "source");
    const metadata = {
      name: "campsite-results",
      description: "Review newly found campsites and available stays.",
      viewport: "620x360",
      theme: "light" as const,
    };
    recordSnapshot(source, metadata, before);
    const changed = recordSnapshot(source, metadata, after, { update: true });
    const stable = { ...metadata, name: "unchanged-results" };
    recordSnapshot(source, stable, before);
    const unchanged = recordSnapshot(source, stable, before);
    const added = recordSnapshot(
      source,
      {
        ...metadata,
        name: "new-mobile-view",
        description: "<script>window.galleryInjection = true</script>",
      },
      after,
    );
    const report = path.join(temporary, "export", "report.html");
    fs.mkdirSync(path.dirname(report));
    fs.writeFileSync(
      path.join(source, "report.html"),
      generateHtmlReport([changed, unchanged, added]),
    );
    fs.cpSync(source, path.dirname(report), { recursive: true });
    fs.rmSync(source, { recursive: true, force: true });
    fs.cpSync(path.dirname(report), output, { recursive: true });

    const networkRequests: string[] = [];
    const errors: string[] = [];
    page.on("pageerror", (error) => errors.push(error.message));
    await page.route("**/*", (route) => {
      if (/^https?:/.test(route.request().url())) {
        networkRequests.push(route.request().url());
        return route.abort();
      }
      return route.continue();
    });
    await page.setViewportSize({ width: 1280, height: 900 });
    await page.goto(pathToFileURL(report).href);
    await expect(
      page.getByRole("heading", { name: "Camply Screenshot Comparison" }),
    ).toBeVisible();
    await expect(page.getByRole("status")).toHaveText("3 of 3 screenshots");
    await expect(
      page.getByText(added.description, { exact: true }),
    ).toBeAttached();
    assert.equal(await page.evaluate("window.galleryInjection"), undefined);
    assert.equal(
      await page
        .locator("img[src]")
        .evaluateAll((images) =>
          images.every(
            (image) =>
              /^(before|current|diffs)\//.test(
                image.getAttribute("src") ?? "",
              ) &&
              image instanceof HTMLImageElement &&
              image.src.startsWith("file:"),
          ),
        ),
      true,
    );
    await page.locator("img[src]").evaluateAll((images) =>
      Promise.all(
        images.map((image) => {
          if (image instanceof HTMLImageElement) {
            image.loading = "eager";
            return image.decode();
          }
          return undefined;
        }),
      ),
    );
    const card = page.getByRole("article", {
      name: "campsite-results",
      exact: true,
    });
    await card
      .locator(".pair img")
      .first()
      .evaluate((image) => (image as HTMLImageElement).decode());
    await card
      .locator(".pair .after")
      .evaluate((image) => (image as HTMLImageElement).decode());
    const beforeBounds = await card.locator(".pair .before").boundingBox();
    const afterBounds = await card.locator(".pair .after").boundingBox();
    assert.ok(beforeBounds && afterBounds);
    assert.ok(
      Math.abs(afterBounds.width / beforeBounds.width - 580 / 620) < 0.01,
    );
    assert.ok(Math.abs(beforeBounds.y - afterBounds.y) < 1);
    await page.getByLabel("Status", { exact: true }).selectOption("MODIFIED");
    await expect(page.getByRole("status")).toHaveText("1 of 3 screenshots");
    await page.screenshot({
      path: path.join(output, "desktop.png"),
      fullPage: true,
    });

    const mode = card.getByLabel("Comparison view for campsite-results", {
      exact: true,
    });
    await mode.selectOption("overlay");
    const slider = card.getByRole("slider");
    await slider.focus();
    await slider.press("Home");
    await slider.press("ArrowRight");
    await expect(slider).toHaveValue("1");
    assert.equal(
      await card
        .locator(".overlay")
        .evaluate((element) => element.getAttribute("style")),
      "--split: 1%;",
    );
    await slider.press("Home");
    for (let step = 0; step < 5; step += 1) await slider.press("PageUp");
    await expect(slider).toHaveValue("50");
    await page.screenshot({
      path: path.join(output, "slider.png"),
      fullPage: true,
    });
    await mode.selectOption("diff");
    await expect(card.locator(".diff")).toBeVisible();
    await expect(card.locator(".pair")).toBeHidden();

    await page.getByLabel("Status", { exact: true }).selectOption("NEW");
    const newCard = page.getByRole("article", {
      name: "new-mobile-view",
      exact: true,
    });
    await expect(
      newCard.getByText("No baseline existed for this screenshot."),
    ).toBeVisible();
    await expect(newCard.locator('option[value="overlay"]')).toHaveAttribute(
      "disabled",
      "",
    );
    await expect(newCard.locator('option[value="diff"]')).toHaveAttribute(
      "disabled",
      "",
    );
    await page.getByRole("searchbox").fill("missing");
    await expect(page.getByRole("status")).toHaveText("0 of 3 screenshots");
    await page.getByRole("button", { name: "Clear filters" }).click();
    await expect(page.getByRole("status")).toHaveText("3 of 3 screenshots");
    await page.getByRole("searchbox").fill("campsite-results");
    await expect(page.getByRole("status")).toHaveText("1 of 3 screenshots");
    await mode.selectOption("pair");
    await page.setViewportSize({ width: 375, height: 812 });
    assert.equal(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= window.innerWidth,
      ),
      true,
    );
    await page.screenshot({
      path: path.join(output, "mobile.png"),
      fullPage: true,
    });
    assert.deepEqual(networkRequests, []);
    assert.deepEqual(errors, []);
    console.log(`Offline gallery verification passed. Evidence: ${output}`);
  } finally {
    await browser.close();
    fs.rmSync(temporary, { recursive: true, force: true });
  }
}

main().catch((error: unknown) => {
  console.error(error);
  process.exitCode = 1;
});
