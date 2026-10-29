/** Verify the built website through the single Python origin without API interception. */
import { chromium, expect } from "@playwright/test";

const origin = process.env.CAMPLY_SMOKE_ORIGIN!;
const browser = await chromium.launch({ headless: true });
try {
  const page = await browser.newPage();
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await page.goto(`${origin}/auth`);
  await page.getByLabel("Username").fill("synthetic-admin");
  await page.getByLabel("Password", { exact: true }).fill("synthetic-password");
  await page
    .locator("form")
    .getByRole("button", { name: "Sign In", exact: true })
    .click();
  await expect(page).not.toHaveURL(/\/auth/);
  await page.goto(`${origin}/admin/operations`);
  await expect(
    page.getByText(/historical trends are disabled in standalone/i),
  ).toBeVisible();
  await expect(page.getByText(/history clears on restart/i)).toBeVisible();
  await expect(page.getByText("Disconnected", { exact: true })).toHaveCount(0);
  await page
    .getByRole("button", { name: "Sync Providers", exact: true })
    .click();
  await expect(page.getByRole("status")).toContainText(/sync/i);
  await page.reload();
  await expect(
    page.getByRole("heading", { name: "System Operations" }),
  ).toBeVisible();
  const profile = await page.request.get(`${origin}/api/me`);
  expect(profile.ok()).toBe(true);
  const denied = await page.request.patch(`${origin}/api/me`, {
    data: { pushover_token: "synthetic" },
  });
  expect(denied.status()).toBe(403);
  if (process.env.CAMPLY_SMOKE_SCREENSHOT) {
    await page.screenshot({
      path: process.env.CAMPLY_SMOKE_SCREENSHOT,
      fullPage: true,
    });
    await page.setViewportSize({ width: 390, height: 844 });
    await page.screenshot({
      path: process.env.CAMPLY_SMOKE_SCREENSHOT.replace(".png", "-mobile.png"),
      fullPage: true,
    });
  }
  expect(errors).toEqual([]);
} finally {
  await browser.close();
}
