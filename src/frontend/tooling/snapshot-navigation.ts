import type { Page } from "@playwright/test";

/** Wait for visible MapLibre maps to finish loading and painting basemap tiles. */
async function waitForRenderedMaps(page: Page): Promise<void> {
  const hasVisibleTrackedMap = await page.evaluate(() =>
    Array.from(
      document.querySelectorAll<HTMLElement>(".camply-map[data-map-idle]"),
    ).some((element) => {
      const style = getComputedStyle(element);
      return (
        element.getClientRects().length > 0 &&
        style.visibility !== "hidden" &&
        style.visibility !== "collapse"
      );
    }),
  );
  if (!hasVisibleTrackedMap) return;
  await page.waitForFunction(
    () =>
      Array.from(
        document.querySelectorAll<HTMLElement>(".camply-map[data-map-idle]"),
      )
        .filter((element) => {
          const style = getComputedStyle(element);
          return (
            element.getClientRects().length > 0 &&
            style.visibility !== "hidden" &&
            style.visibility !== "collapse"
          );
        })
        .every((element) => element.dataset.mapIdle === "true"),
    undefined,
    { timeout: 10000 },
  );
  await page.evaluate(
    () =>
      new Promise<void>((resolve) =>
        requestAnimationFrame(() => requestAnimationFrame(() => resolve())),
      ),
  );
}

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
  await waitForRenderedMaps(page);
}

export interface SnapshotReadyContent {
  name: string;
  role?: "heading" | "button" | "combobox" | "text";
}

/** Wait for successful route content, which loading and error views lack. */
export async function waitForSnapshotContent(
  page: Page,
  { name, role = "heading" }: SnapshotReadyContent,
  timeout = 10_000,
): Promise<void> {
  const content =
    role === "text"
      ? page.getByText(name, { exact: true })
      : page.getByRole(role, { name, exact: true });
  try {
    await content.filter({ visible: true }).first().waitFor({ timeout });
  } catch (cause) {
    throw new Error(
      `Expected ${role} "${name}" to become visible at ${page.url()}`,
      { cause },
    );
  }
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
  await waitForRenderedMaps(page);
}
