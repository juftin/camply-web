/** Verify real MapLibre interactions, bounded HTTP discovery and isolated-source behavior. */
import { chromium, expect, type Route, type Page } from "@playwright/test";
import { build, preview, createServer } from "vite";
import { mkdirSync, writeFileSync } from "node:fs";
import os from "node:os";
import { PNG } from "pngjs";
import type {
  SearchMapResponse,
  SearchMapMembers,
  SearchMapSummary,
} from "../lib/structs";

async function expectStackedResults(page: Page) {
  const map = page.getByRole("region", { name: "Explore map", exact: true });
  const results = page.getByRole("region", {
    name: "Search results",
    exact: true,
  });
  await expect(map).toBeVisible();
  await expect(
    results.getByRole("link", { name: /Synthetic Pines/ }).first(),
  ).toBeVisible();
  await expect(page.getByRole("group", { name: "Result view" })).toHaveCount(0);
  const [mapBox, listBox] = await page
    .locator(
      'section[aria-label="Explore map"], section[aria-label="Search results"]',
    )
    .evaluateAll((elements) =>
      elements.map((element) => {
        const bounds = element.getBoundingClientRect();
        return {
          x: bounds.x,
          y: bounds.y,
          bottom: bounds.bottom,
          width: bounds.width,
        };
      }),
    );
  expect(listBox.y).toBeGreaterThanOrEqual(mapBox.bottom);
  expect(Math.abs(listBox.x - mapBox.x)).toBeLessThan(1);
  expect(Math.abs(listBox.width - mapBox.width)).toBeLessThan(1);
}

const image = new PNG({ width: 256, height: 256 });
for (let i = 0; i < image.data.length; i += 4) {
  image.data[i] = 225;
  image.data[i + 1] = 235;
  image.data[i + 2] = 219;
  image.data[i + 3] = 255;
}
const tile = PNG.sync.write(image);
mkdirSync("tmp", { recursive: true });
const report: Record<string, unknown> = {
  platform: os.platform(),
  release: os.release(),
  architecture: os.arch(),
  cpu: os.cpus()[0]?.model,
  fixture:
    "deterministic 5000 matching places; 130 overlapping; two unmappable",
  tileSource: "intercepted deterministic 256px raster",
};
const configFile = new URL("../vite.config.ts", import.meta.url).pathname;
const server = await createServer({
  configFile,
  base: "/",
  server: { host: "127.0.0.1", port: 0 },
});
await server.listen();
const browser = await chromium.launch({
  headless: true,
  args: ["--enable-unsafe-swiftshader"],
});
try {
  report.browser = browser.version();
  const page = await browser.newPage({
    viewport: { width: 1440, height: 1000 },
  });
  const errors: string[] = [];
  const tileRequests: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await page.route("https://tile.openstreetmap.org/**", async (route) => {
    const headers = route.request().headers();
    expect(headers.authorization).toBeUndefined();
    expect(headers["x-csrf-token"]).toBeUndefined();
    expect(new URL(headers.referer).pathname).toBe("/");
    tileRequests.push(route.request().url());
    await route.fulfill({
      contentType: "image/png",
      headers: { "Access-Control-Allow-Origin": "*" },
      body: tile,
    });
  });
  const origin = server.resolvedUrls!.local[0];
  let searchCompleted = 0;
  page.on("response", (response) => {
    if (response.url().includes("/api/search/explore"))
      searchCompleted = performance.now();
  });
  await page.goto(`${origin}search?q=Synthetic`);
  await page
    .locator(".camply-map-marker")
    .first()
    .waitFor({ state: "visible" });
  await expect(
    page.getByText("Loading map…", { exact: true }),
  ).not.toBeVisible();
  await expect(page.getByRole("alert")).toHaveCount(0);
  const initialMs = performance.now() - searchCompleted;
  expect(searchCompleted).toBeGreaterThan(0);
  expect(initialMs).toBeLessThan(3000);
  report.initial_map_ms = initialMs;
  report.graphics = await page
    .locator("canvas.maplibregl-canvas")
    .evaluate((canvas) => {
      const gl = (canvas as HTMLCanvasElement).getContext("webgl2")!;
      const debug = gl.getExtension("WEBGL_debug_renderer_info");
      return {
        version: gl.getParameter(gl.VERSION),
        renderer: gl.getParameter(
          debug ? debug.UNMASKED_RENDERER_WEBGL : gl.RENDERER,
        ),
      };
    });
  await expect(
    page.getByText(/2 matching places cannot be mapped/),
  ).toBeVisible();
  await expect(
    page.getByRole("link", { name: "© OpenStreetMap contributors" }),
  ).toBeVisible();
  const group = page
    .locator('.camply-map-marker[aria-label$="places"]')
    .first();
  const selected = performance.now();
  await group.hover();
  await expect(page.getByRole("tooltip")).toContainText(
    "Zoom in or select this group",
  );
  await group.focus();
  await page.keyboard.press("Enter");
  await expect(
    page.getByRole("heading", { name: /places in this group/ }),
  ).toBeVisible();
  report.group_selection_ms = performance.now() - selected;
  expect(report.group_selection_ms as number).toBeLessThan(500);
  const membersStart = performance.now();
  await page.getByRole("button", { name: "View places", exact: true }).click();
  const panel = page.getByLabel("Selected map location");
  await panel
    .getByRole("link", { name: "Details", exact: true })
    .first()
    .waitFor({ state: "visible" });
  report.group_members_ms = performance.now() - membersStart;
  expect(report.group_members_ms as number).toBeLessThan(500);
  const destination = await panel
    .getByRole("link", { name: "Details", exact: true })
    .first()
    .getAttribute("href");
  await panel
    .getByRole("button", { name: "Monitor", exact: true })
    .first()
    .click();
  await expect(page.getByRole("dialog")).toBeVisible();
  await expect(page.getByRole("dialog")).toContainText(
    `Provider: ${destination!.split("/")[2]}`,
  );
  await expect(page.getByRole("dialog")).toContainText(
    `ID: ${destination!.split("/")[3]}`,
  );
  await page.keyboard.press("Escape");
  await expect(page.getByRole("dialog")).not.toBeVisible();
  await expectStackedResults(page);

  const summary = (await (
    await page.request.get(`${origin}api/search/map/summary?q=Synthetic`)
  ).json()) as SearchMapSummary;
  expect(summary.total).toBe(5000);
  expect(summary.mappable_total).toBe(4998);
  const bounds = "west=-180&east=180&south=-90&north=90";
  const world = (await (
    await page.request.get(
      `${origin}api/search/map?q=Synthetic&${bounds}&zoom=19`,
    )
  ).json()) as SearchMapResponse;
  expect(world.features.length).toBeLessThanOrEqual(512);
  const ids = new Set<string>();
  let largestPage = 0;
  for (const feature of world.features) {
    if (feature.kind === "location") {
      ids.add(feature.item.id);
      continue;
    }
    let cursor: string | null = null;
    do {
      const params = new URLSearchParams({
        q: "Synthetic",
        west: "-180",
        east: "180",
        south: "-90",
        north: "90",
        cell_id: feature.cell_id,
        page_size: "100",
      });
      if (cursor) params.set("after_id", cursor);
      const members = (await (
        await page.request.get(`${origin}api/search/map/members?${params}`)
      ).json()) as SearchMapMembers;
      expect(members.total).toBe(feature.count);
      expect(members.items.length).toBeLessThanOrEqual(100);
      largestPage = Math.max(largestPage, members.items.length);
      members.items.forEach((item) => ids.add(item.id));
      cursor = members.next_cursor;
    } while (cursor);
  }
  expect(ids.size).toBe(4998);
  report.discovery = {
    matches: summary.total,
    mappable: summary.mappable_total,
    discovered: ids.size,
    features: world.features.length,
    largest_member_page: largestPage,
  };

  await page.route("https://ipapi.co/json/", async (route) => {
    const headers = route.request().headers();
    expect(headers.authorization).toBeUndefined();
    expect(headers.cookie).toBeUndefined();
    await route.fulfill({ json: { latitude: 0, longitude: 0 } });
  });
  const regionalResults = page.waitForResponse((response) => {
    const url = new URL(response.url());
    return (
      url.pathname === "/api/search/explore" && url.searchParams.has("west")
    );
  });
  await page.goto(`${origin}search`);
  const regionalData = await (await regionalResults).json();
  expect(regionalData.total).toBeGreaterThanOrEqual(130);
  expect(regionalData.total).toBeLessThan(5000);
  await expectStackedResults(page);
  report.ip_initial_total = regionalData.total;

  await page.goto(`${origin}search?q=Synthetic&page=2&sort=name_desc`);
  await expectStackedResults(page);
  await page.locator("select").selectOption("name_asc");
  expect(new URL(page.url()).searchParams.has("page")).toBe(false);
  await page.goBack();
  expect(new URL(page.url()).searchParams.get("page")).toBe("2");
  await expect(page.locator("select")).toHaveValue("name_desc");
  await expectStackedResults(page);
  await page.locator(".camply-map-marker").first().waitFor();
  const canvas = page.getByLabel("Interactive campground map");
  const box = (await canvas.boundingBox())!;
  await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2);
  const panResults = page.waitForResponse((response) => {
    const url = new URL(response.url());
    return (
      url.pathname === "/api/search/explore" && url.searchParams.has("west")
    );
  });
  await page.mouse.down();
  await page.mouse.move(
    box.x + box.width / 2 + 80,
    box.y + box.height / 2 + 30,
    { steps: 6 },
  );
  await page.mouse.up();
  await expect
    .poll(() => new URL(page.url()).searchParams.has("page"))
    .toBe(false);
  const panData = await (await panResults).json();
  const zoomResults = page.waitForResponse(async (response) => {
    const url = new URL(response.url());
    return (
      response.ok() &&
      url.pathname === "/api/search/explore" &&
      url.searchParams.has("west") &&
      (await response.json()).total < panData.total
    );
  });
  await page.getByRole("button", { name: "Zoom in", exact: true }).click();
  const zoomData = await (await zoomResults).json();
  expect(zoomData.total).toBeLessThan(panData.total);
  report.viewport_filtering = {
    after_pan: panData.total,
    after_zoom: zoomData.total,
  };
  await page.waitForTimeout(400);
  const liveTotals: number[] = [];
  const recordLiveResults = async (
    response: import("@playwright/test").Response,
  ) => {
    const url = new URL(response.url());
    if (
      url.pathname === "/api/search/explore" &&
      url.searchParams.has("west") &&
      response.ok()
    ) {
      liveTotals.push((await response.json()).total);
    }
  };
  page.on("response", recordLiveResults);
  await page.mouse.move(box.x + box.width * 0.35, box.y + box.height * 0.35);
  await page.mouse.down();
  try {
    for (let step = 1; step <= 8; step++) {
      await page.mouse.move(
        box.x + box.width * 0.35 + step * 12,
        box.y + box.height * 0.35,
      );
      await page.waitForTimeout(100);
    }
    await expect.poll(() => liveTotals.length).toBeGreaterThanOrEqual(2);
    await expect
      .poll(async () => {
        const statuses = await page.getByRole("status").allTextContents();
        return statuses.some((status) =>
          status.includes(`Found ${liveTotals.at(-1)} campgrounds`),
        );
      })
      .toBe(true);
    report.live_drag_totals = liveTotals;
  } finally {
    await page.mouse.up();
    page.off("response", recordLiveResults);
  }

  for (const width of [375, 1440])
    for (const colorScheme of ["light", "dark"] as const) {
      await page.setViewportSize({ width, height: 1000 });
      await page.evaluate((theme) => {
        localStorage.setItem("vite-ui-theme", theme);
        document.documentElement.classList.toggle("dark", theme === "dark");
      }, colorScheme);
      await expectStackedResults(page);
      const beforeCollapse = page.url();
      const hideMap = page.getByRole("button", {
        name: "Hide map",
        exact: true,
      });
      await expect(hideMap).toHaveAttribute("aria-expanded", "true");
      await hideMap.focus();
      await page.keyboard.press("Enter");
      await expect(
        page.getByRole("region", { name: "Explore map", exact: true }),
      ).toHaveCount(0);
      await expect(
        page.getByRole("region", { name: "Search results", exact: true }),
      ).toBeVisible();
      const showMap = page.getByRole("button", {
        name: "Show map",
        exact: true,
      });
      await expect(showMap).toHaveAttribute("aria-expanded", "false");
      expect(page.url()).toBe(beforeCollapse);
      await page.keyboard.press("Space");
      await expectStackedResults(page);
      expect(page.url()).toBe(beforeCollapse);
      expect(
        await page.evaluate(
          () => document.documentElement.scrollWidth <= window.innerWidth,
        ),
      ).toBe(true);
      await page.screenshot({
        path: `tmp/maps-${width}-${colorScheme}.png`,
        fullPage: true,
      });
    }
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.route("**/api/search/map/summary*", (route) =>
    route.fulfill({ status: 503, body: "Unavailable" }),
  );
  await page.goto(`${origin}search?q=Synthetic`);
  await expect(
    page.getByRole("button", { name: "Retry map summary" }),
  ).toBeVisible();
  await expect(
    page.getByRole("link", { name: /Synthetic Pines/ }).first(),
  ).toBeVisible();
  await page.unroute("**/api/search/map/summary*");
  await page.getByRole("button", { name: "Retry map summary" }).click();
  await page.locator(".camply-map-marker").first().waitFor();

  const viewportRoute = (url: URL) => url.pathname === "/api/search/map";
  await page.route(viewportRoute, (route) =>
    route.fulfill({ status: 503, body: "Unavailable" }),
  );
  await page.goto(`${origin}search?q=Synthetic`);
  await expect(
    page.getByRole("button", { name: "Retry map locations" }),
  ).toBeVisible();
  await expect(
    page.getByRole("link", { name: /Synthetic Pines/ }).first(),
  ).toBeVisible();
  await page.unroute(viewportRoute);
  await page.getByRole("button", { name: "Retry map locations" }).click();
  await page
    .locator('.camply-map-marker[aria-label$="places"]')
    .first()
    .click();
  await page.route("**/api/search/map/members*", (route) =>
    route.fulfill({ status: 503, body: "Unavailable" }),
  );
  await page.getByRole("button", { name: "View places", exact: true }).click();
  await expect(
    page.getByRole("button", { name: "Retry group members" }),
  ).toBeVisible();
  await page.unroute("**/api/search/map/members*");
  await page.getByRole("button", { name: "Retry group members" }).click();
  await page
    .getByLabel("Selected map location")
    .getByRole("link", { name: "Details" })
    .first()
    .waitFor();
  const failTiles = (route: Route) => route.abort("failed");
  await page.route("https://tile.openstreetmap.org/**", failTiles);
  await page.goto(`${origin}search?q=Synthetic`);
  await expect(page.getByRole("button", { name: "Retry tiles" })).toBeVisible();
  await expect(
    page.getByRole("link", { name: /Synthetic Pines/ }).first(),
  ).toBeVisible();
  await page.unroute("https://tile.openstreetmap.org/**", failTiles);
  await page.getByRole("button", { name: "Retry tiles" }).click();
  await expect(
    page.getByRole("button", { name: "Retry tiles" }),
  ).not.toBeVisible();
  report.independent_failure_recovery =
    "passed: summary, viewport, group members and tiles";
  await page.goto(`${origin}${destination?.replace(/^\//, "")}`);
  await expect(page.getByLabel("Interactive campground map")).toBeVisible();
  await page.goto(`${origin}rec-area/1/area`);
  await expect(page.getByLabel("Interactive campground map")).toBeVisible();
  expect(tileRequests.length).toBeGreaterThan(0);
  expect(errors).toEqual([]);

  const touchPage = await browser.newPage({
    viewport: { width: 375, height: 844 },
    hasTouch: true,
    isMobile: true,
  });
  await touchPage.route("https://tile.openstreetmap.org/**", (route) =>
    route.fulfill({
      contentType: "image/png",
      headers: { "Access-Control-Allow-Origin": "*" },
      body: tile,
    }),
  );
  await touchPage.goto(`${origin}search?q=Synthetic&page=2`);
  await touchPage.locator(".camply-map-marker").first().waitFor();
  await expectStackedResults(touchPage);
  await touchPage.getByRole("button", { name: "Hide map", exact: true }).tap();
  await expect(
    touchPage.getByRole("region", { name: "Search results", exact: true }),
  ).toBeVisible();
  await expect(
    touchPage.getByRole("region", { name: "Explore map", exact: true }),
  ).toHaveCount(0);
  await touchPage.getByRole("button", { name: "Show map", exact: true }).tap();
  await expectStackedResults(touchPage);
  await touchPage.locator(".camply-map-marker").first().waitFor();
  expect(new URL(touchPage.url()).searchParams.get("page")).toBe("2");
  await touchPage
    .locator('.camply-map-marker[aria-label$="places"]')
    .first()
    .tap();
  await touchPage
    .getByRole("button", { name: "View places", exact: true })
    .tap();
  await touchPage
    .getByLabel("Selected map location")
    .getByRole("button", { name: "Monitor", exact: true })
    .first()
    .tap();
  await expect(touchPage.getByRole("dialog")).toBeVisible();
  await touchPage.keyboard.press("Escape");
  await touchPage.close();
  report.touch_and_keyboard =
    "passed: map collapse/reopen by touch and keyboard; stacked map/list; group/Monitor and marker selection";
  const unavailablePage = await browser.newPage({
    viewport: { width: 1440, height: 1000 },
  });
  await unavailablePage.route("https://tile.openstreetmap.org/**", (route) =>
    route.fulfill({
      contentType: "image/png",
      headers: { "Access-Control-Allow-Origin": "*" },
      body: tile,
    }),
  );
  await unavailablePage.addInitScript(`{
    const original = HTMLCanvasElement.prototype.getContext;
    HTMLCanvasElement.prototype.getContext = function(kind, ...args) {
      return kind === "webgl2" || kind === "webgl" ? null : original.call(this, kind, ...args);
    };
    window.restoreMapGraphics = () => { HTMLCanvasElement.prototype.getContext = original; };
  }`);
  await unavailablePage.goto(`${origin}search?q=Synthetic`);
  await expect(
    unavailablePage.getByRole("button", { name: "Retry map", exact: true }),
  ).toBeVisible();
  await expect(
    unavailablePage.getByRole("region", {
      name: "Search results",
      exact: true,
    }),
  ).toBeVisible();
  await unavailablePage.evaluate("window.restoreMapGraphics()");
  await unavailablePage
    .getByRole("button", { name: "Retry map", exact: true })
    .click();
  await unavailablePage.locator(".camply-map-marker").first().waitFor();
  await expect(
    unavailablePage.getByText("Loading map…", { exact: true }),
  ).not.toBeVisible();
  await expect(unavailablePage.getByRole("alert")).toHaveCount(0);
  await unavailablePage
    .locator("canvas.maplibregl-canvas")
    .evaluate((canvas) => {
      const gl = (canvas as HTMLCanvasElement).getContext("webgl2")!;
      const extension = gl.getExtension("WEBGL_lose_context");
      if (!extension)
        throw new Error("Browser cannot exercise WebGL context loss");
      extension.loseContext();
    });
  await expect(unavailablePage.getByRole("alert")).toContainText(
    "graphics context was lost",
  );
  await unavailablePage
    .getByRole("button", { name: "Retry map", exact: true })
    .click();
  await unavailablePage.locator(".camply-map-marker").first().waitFor();
  await expect(
    unavailablePage.getByText("Loading map…", { exact: true }),
  ).not.toBeVisible();
  await expect(unavailablePage.getByRole("alert")).toHaveCount(0);
  await unavailablePage.close();
  report.webgl_failure_recovery =
    "passed: unavailable/lost contexts keep list usable; retry rebuilds the renderer";
  const publicSettings = {
    VITE_MAP_TILE_URL: "/fixture-tiles/{z}/{x}/{y}.png",
    VITE_MAP_ATTRIBUTION_TEXT: "Synthetic map credit",
    VITE_MAP_ATTRIBUTION_URL: "https://example.test/license",
    VITE_MAP_MAX_NATIVE_ZOOM: "4",
  };
  const previousSettings = Object.fromEntries(
    Object.keys(publicSettings).map((key) => [key, process.env[key]]),
  );
  Object.assign(process.env, publicSettings);
  try {
    await build({
      configFile,
      base: "/map-check/",
      build: {
        outDir: new URL("../../../tmp/maps-static", import.meta.url).pathname,
        emptyOutDir: true,
      },
      logLevel: "warn",
    });
    const staticServer = await preview({
      configFile,
      base: "/map-check/",
      build: {
        outDir: new URL("../../../tmp/maps-static", import.meta.url).pathname,
      },
      preview: {
        host: "127.0.0.1",
        port: 0,
        proxy: {
          "/api": { target: process.env.CAMPLY_API_URL!, changeOrigin: true },
        },
      },
    });
    try {
      const address = staticServer.httpServer.address();
      if (!address || typeof address === "string")
        throw new Error("Static map preview did not bind a TCP port");
      const staticOrigin = `http://127.0.0.1:${address.port}`;
      const staticPage = await browser.newPage({
        viewport: { width: 1440, height: 1000 },
      });
      let nativeTiles = 0;
      await staticPage.route("**/fixture-tiles/**", async (route) => {
        expect(
          Number(new URL(route.request().url()).pathname.split("/")[2]),
        ).toBeLessThanOrEqual(4);
        nativeTiles++;
        expect(route.request().headers().authorization).toBeUndefined();
        await route.fulfill({
          contentType: "image/png",
          headers: { "Access-Control-Allow-Origin": "*" },
          body: tile,
        });
      });
      await staticPage.goto(`${staticOrigin}/map-check/search?q=Synthetic`);
      await expect(
        staticPage.getByRole("link", { name: "Synthetic map credit" }),
      ).toHaveAttribute("href", "https://example.test/license");
      await staticPage
        .locator('.camply-map-marker[aria-label$="places"]')
        .first()
        .click();
      await staticPage
        .getByRole("button", { name: "View places", exact: true })
        .click();
      const staticPanel = staticPage.getByLabel("Selected map location");
      await staticPanel
        .getByRole("link", { name: "Details" })
        .first()
        .waitFor();
      expect(
        await staticPanel
          .getByRole("link", { name: "Details" })
          .first()
          .getAttribute("href"),
      ).toMatch(/^\/map-check\/campground\//);
      await staticPanel
        .getByRole("button", { name: "Monitor", exact: true })
        .first()
        .click();
      await expect(staticPage.getByRole("dialog")).toBeVisible();
      await staticPage.keyboard.press("Escape");
      await staticPanel.getByRole("link", { name: "Details" }).first().click();
      await expect(
        staticPage.getByLabel("Interactive campground map"),
      ).toBeVisible();
      await expect(
        staticPage.getByText("Loading map…", { exact: true }),
      ).not.toBeVisible();
      await expect(staticPage.getByRole("alert")).toHaveCount(0);
      expect(nativeTiles).toBeGreaterThan(0);
      await staticPage.close();
      report.static_subpath_overrides =
        "passed; source/attribution/native zoom/details/Monitor";
    } finally {
      await new Promise<void>((resolve, reject) =>
        staticServer.httpServer.close((error) =>
          error ? reject(error) : resolve(),
        ),
      );
    }
    process.env.VITE_MAP_MAX_NATIVE_ZOOM = "25";
    const invalidServer = await createServer({
      configFile,
      server: { host: "127.0.0.1", port: 0 },
    });
    await invalidServer.listen();
    try {
      const invalidPage = await browser.newPage({
        viewport: { width: 1440, height: 1000 },
      });
      await invalidPage.goto(
        `${invalidServer.resolvedUrls!.local[0]}search?q=Synthetic`,
      );
      await expect(invalidPage.getByRole("alert")).toContainText(
        "Map native zoom",
      );
      await expect(
        invalidPage.getByRole("link", { name: /Synthetic Pines/ }).first(),
      ).toBeVisible();
      await invalidPage.close();
      report.invalid_source_recovery = "passed";
    } finally {
      await invalidServer.close();
    }
  } finally {
    for (const [key, value] of Object.entries(previousSettings)) {
      if (value === undefined) delete process.env[key];
      else process.env[key] = value;
    }
  }
  report.tile_requests_intercepted = tileRequests.length;
  report.console_errors = errors;
  report.behavior_checks = [
    "exact-provider monitor and details",
    "global all-pages discovery",
    "group keysets",
    "collapsible map above list at every width without a view selector",
    "history restoration",
    "IP region initializes the list without application credentials",
    "pan and zoom filter the full list and reset pagination",
    "375px/1440px light/dark stacked map/list with no overflow",
    "summary failure/retry keeps list usable",
    "both detail map surfaces",
  ];
} finally {
  mkdirSync("tmp", { recursive: true });
  writeFileSync("tmp/maps-browser.json", JSON.stringify(report, null, 2));
  await browser.close();
  await server.close();
}
