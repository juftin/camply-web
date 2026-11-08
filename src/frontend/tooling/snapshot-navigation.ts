import type { Page } from "@playwright/test";

/** Decode layout images before capture without waiting for unrelated requests. */
export async function waitForSnapshotAssets(page: Page): Promise<void> {
  await page.evaluate(() => {
    for (const image of document.images) {
      const style = getComputedStyle(image);
      if (
        image.getClientRects().length > 0 &&
        style.visibility !== "hidden" &&
        style.visibility !== "collapse"
      ) {
        // Full-page snapshots include below-fold images that browser lazy loading
        // may otherwise defer until after the screenshot has already been taken.
        image.loading = "eager";
      }
    }
  });
  await page.waitForFunction(
    () => {
      let imagesReady = true;
      for (const image of document.images) {
        const style = getComputedStyle(image);
        if (
          image.getClientRects().length === 0 ||
          style.visibility === "hidden" ||
          style.visibility === "collapse"
        ) {
          continue;
        }
        if (image.complete && image.naturalWidth === 0) {
          throw new Error(
            `Snapshot image failed to load: ${image.currentSrc || image.src}`,
          );
        }
        if (!image.complete) imagesReady = false;
      }
      return imagesReady && document.fonts.status === "loaded";
    },
    undefined,
    { timeout: 10000 },
  );
  await page.evaluate(async () => {
    await document.fonts.ready;
    await Promise.all(
      Array.from(document.images)
        .filter((image) => {
          const style = getComputedStyle(image);
          return (
            image.getClientRects().length > 0 &&
            style.visibility !== "hidden" &&
            style.visibility !== "collapse"
          );
        })
        .map((image) => image.decode()),
    );
  });
}

/** Wait for map snapshot content without depending on background network traffic. */
export async function navigateToSnapshot(
  page: Page,
  url: string,
  mapSummaryError = false,
): Promise<void> {
  const pathname = new URL(url).pathname;
  const isSearch = pathname === "/search";
  const hasMap = isSearch || /^\/(campground|rec-area)\//.test(pathname);
  await page.goto(url, {
    waitUntil: "domcontentloaded",
  });
  await page.locator("#root > *, main").first().waitFor();
  if (!hasMap) return;

  if (isSearch) {
    await page.locator('main[aria-busy="false"]').waitFor();
    await page
      .getByRole("region", { name: "Search results", exact: true })
      .waitFor();
  }
  if (mapSummaryError) {
    await page
      .getByRole("button", { name: "Retry map summary", exact: true })
      .waitFor();
    return;
  }

  // Wait for the map to mount first: absence of a loading message on an
  // unmounted React tree does not mean that the map is ready.
  await page.locator(".camply-map canvas").waitFor();
  await page
    .getByText("Loading map…", { exact: true })
    .waitFor({ state: "hidden" });
  await page.locator(".camply-map-marker").first().waitFor();
  await page
    .getByText("Updating map locations…", { exact: true })
    .waitFor({ state: "hidden" });
}
