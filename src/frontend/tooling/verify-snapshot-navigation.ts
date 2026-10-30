/** Reproduce a snapshot navigation with a request that never completes. */
import assert from "node:assert/strict";
import { chromium, expect } from "@playwright/test";
import { navigateToSnapshot } from "./snapshot-navigation";

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
    console.log("Snapshot navigation passed with background traffic pending.");
  } finally {
    await browser.close();
  }
}

main().catch((error: unknown) => {
  console.error(error);
  process.exitCode = 1;
});
