/** Reproduce a snapshot navigation with a request that never completes. */
import fs from "node:fs";
import assert from "node:assert/strict";
import { chromium, expect } from "@playwright/test";
import {
  navigateToSnapshot,
  waitForSnapshotAssets,
} from "./snapshot-navigation";

if (fs.existsSync("/tmp/camply-browser-deps/root/usr/lib/x86_64-linux-gnu")) {
  process.env.LD_LIBRARY_PATH = `/tmp/camply-browser-deps/root/usr/lib/x86_64-linux-gnu:/tmp/camply-browser-deps/root/lib/x86_64-linux-gnu:${process.env.LD_LIBRARY_PATH || ""}`;
  process.env.FONTCONFIG_PATH = "/tmp/camply-browser-deps";
}

async function main(): Promise<void> {
  const browser = await chromium.launch();
  try {
    const page = await browser.newPage();
    page.setDefaultTimeout(5000);
    page.setDefaultNavigationTimeout(5000);
    let backgroundRequested = false;
    await page.route("http://snapshot.test/background", () => {
      backgroundRequested = true;
      // Deliberately leave this request pending until the page closes.
    });
    await page.route("http://snapshot.test/search?*", (route) =>
      route.fulfill({
        contentType: "text/html",
        body: `<!doctype html><div id="root"></div><script>
          fetch('/background');
          setTimeout(() => {
            document.querySelector('#root').innerHTML = '<main aria-busy="true"><section aria-label="Search results"></section></main><div class="camply-map"><canvas></canvas></div><p role="status">Loading map…</p><p role="status">Updating map locations…</p>';
          }, 100);
          setTimeout(() => {
            document.querySelector('main').setAttribute('aria-busy', 'false');
            document.querySelector('section').textContent = 'Upper Pines Campground';
          }, 200);
          setTimeout(() => {
            document.querySelector('.camply-map').innerHTML += '<button class="camply-map-marker">3 places</button>';
            document.querySelectorAll('[role="status"]').forEach(element => element.remove());
          }, 350);
        </script>`,
      }),
    );
    await navigateToSnapshot(page, "http://snapshot.test/search?q=yosemite");
    assert.equal(backgroundRequested, true);
    // Immediate assertions ensure navigation waited for the delayed UI.
    assert.equal(await page.locator("main").getAttribute("aria-busy"), "false");
    assert.equal(await page.locator(".camply-map-marker").count(), 1);
    await expect(
      page.getByRole("region", { name: "Search results" }),
    ).toHaveText("Upper Pines Campground");

    await page.route("http://snapshot.test/search?q=unavailable", (route) =>
      route.fulfill({
        contentType: "text/html",
        body: `<!doctype html><main aria-busy="false"><section aria-label="Search results">Upper Pines Campground</section></main><script>
          setTimeout(() => {
            document.body.innerHTML += '<div role="alert">Map summary could not load. <button>Retry map summary</button></div>';
          }, 100);
        </script>`,
      }),
    );
    await navigateToSnapshot(
      page,
      "http://snapshot.test/search?q=unavailable",
      true,
    );
    assert.equal(
      await page.getByRole("button", { name: "Retry map summary" }).count(),
      1,
    );

    let headerRequested = false;
    let footerRequested = false;
    let releaseHeader: () => void = () => {};
    let releaseFooter: () => void = () => {};
    const headerReady = new Promise<void>((resolve) => {
      releaseHeader = resolve;
    });
    const footerReady = new Promise<void>((resolve) => {
      releaseFooter = resolve;
    });
    const logo =
      '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20"><rect width="20" height="20" fill="green"/></svg>';
    await page.route("http://snapshot.test/header.svg", async (route) => {
      headerRequested = true;
      await headerReady;
      await route.fulfill({ contentType: "image/svg+xml", body: logo });
    });
    await page.route("http://snapshot.test/footer.svg", async (route) => {
      footerRequested = true;
      await footerReady;
      await route.fulfill({ contentType: "image/svg+xml", body: logo });
    });
    await page.route("http://snapshot.test/profile", (route) =>
      route.fulfill({
        contentType: "text/html",
        body: `<!doctype html><div id="root"><header><img src="/header.svg" width="20" height="20"></header><main style="height:10000px">Profile</main><footer><img src="/footer.svg" width="20" height="20" loading="lazy"></footer></div><script>fetch('/background');</script>`,
      }),
    );
    backgroundRequested = false;
    await navigateToSnapshot(page, "http://snapshot.test/profile");
    let assetsReady = false;
    const assets = waitForSnapshotAssets(page).then(() => {
      assetsReady = true;
    });
    await expect.poll(() => headerRequested && footerRequested).toBe(true);
    assert.equal(assetsReady, false);
    releaseHeader();
    await expect(page.locator("header img")).toHaveJSProperty("complete", true);
    assert.equal(assetsReady, false);
    releaseFooter();
    await assets;
    assert.equal(backgroundRequested, true);
    for (const image of await page.locator("img").all()) {
      await expect(image).toHaveJSProperty("complete", true);
      await expect(image).toHaveJSProperty("naturalWidth", 20);
    }

    await page.route("http://snapshot.test/broken.svg", (route) =>
      route.fulfill({ status: 404, body: "Missing image" }),
    );
    await page.route("http://snapshot.test/broken-image", (route) =>
      route.fulfill({
        contentType: "text/html",
        body: '<!doctype html><main><img src="/broken.svg" width="20" height="20"></main>',
      }),
    );
    await navigateToSnapshot(page, "http://snapshot.test/broken-image");
    await assert.rejects(
      waitForSnapshotAssets(page),
      /Snapshot image failed to load:.*broken\.svg/,
    );
    await page.locator("img").evaluate((image) => {
      image.style.display = "none";
    });
    await waitForSnapshotAssets(page);
    console.log(
      "Snapshot navigation and decoded layout assets passed with background traffic pending.",
    );
  } finally {
    await browser.close();
  }
}

main().catch((error: unknown) => {
  console.error(error);
  process.exitCode = 1;
});
