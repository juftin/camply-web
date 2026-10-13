/** Exercise admin workflows against a real local API, without intercepted responses. */
import { chromium, expect } from "@playwright/test";
import { createServer } from "vite";

const server = await createServer({
  base: "/",
  server: { host: "127.0.0.1", port: 0 },
});
await server.listen();
const browser = await chromium.launch({ headless: true });
try {
  const page = await browser.newPage();
  const consoleErrors: string[] = [];
  page.on("pageerror", (error) => consoleErrors.push(error.message));
  const origin = server.resolvedUrls!.local[0];
  await page.goto(`${origin}admin/users/${process.env.CAMPLY_SMOKE_USER_ID}`);
  const access = page.getByRole("switch", { name: /Scanning access for/ });
  await expect(access).toBeChecked();
  await access.click();
  await expect(page.getByRole("status")).toContainText("Scanning suspended");
  const profile = await page.request.get(`${origin}api/me`);
  expect((await profile.json()).scanning_enabled).toBe(false);
  await expect(
    page.getByRole("switch", { name: /Saved active scan at/ }),
  ).toBeChecked();
  await access.click();
  await expect(page.getByRole("status")).toContainText("Scanning enabled");
  const scanSetting = page.getByRole("switch", {
    name: /Saved active scan at/,
  });
  await scanSetting.click();
  await expect(page.getByRole("status")).toContainText("Scan paused");
  await expect(scanSetting).not.toBeChecked();
  await scanSetting.click();
  await expect(page.getByRole("status")).toContainText("Scan resumed");
  await expect(scanSetting).toBeChecked();
  await page.goto(`${origin}admin/operations`);
  await expect(page.getByText("Connected", { exact: true })).toBeVisible();
  await expect(
    page.getByRole("row", { name: /admin_smoke.failure/ }),
  ).toBeVisible();
  await expect(page.getByText(/Attempt 2/)).toBeVisible();
  await page.getByRole("button", { name: "Table", exact: true }).click();
  await expect(
    page.getByRole("columnheader", { name: /^Time/ }).first(),
  ).toBeVisible();
  expect(consoleErrors).toEqual([]);
} finally {
  await browser.close();
  await server.close();
}
