import type { Page } from "@playwright/test";

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
    waitUntil: hasMap ? "domcontentloaded" : "networkidle",
  });
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
