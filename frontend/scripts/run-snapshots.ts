/**
 * Camply UI Snapshot & Visual Feedback Engine.
 *
 * Captures deterministic full-page and component snapshots across viewports
 * and themes, compares them against baseline snapshots via pixelmatch, generates
 * diff images for modified views, and produces GitHub-Flavored Markdown and HTML
 * reports for human reviewers and autonomous AI agents.
 */

import fs from "fs";
import path from "path";
import http from "http";
import { fileURLToPath } from "url";
import { spawn, type ChildProcess } from "child_process";
import { chromium, type Browser, type Page } from "@playwright/test";
import { PNG } from "pngjs";
import { setupAdminSnapshotMocks } from "./admin-snapshot-mocks";
import {
  generateHtmlReport,
  recordSnapshot,
  type SnapshotResult,
} from "./snapshot-report";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const FRONTEND_ROOT = path.resolve(__dirname, "..");
const SNAPSHOTS_DIR = path.resolve(FRONTEND_ROOT, "snapshots");
const BASELINES_DIR = path.resolve(SNAPSHOTS_DIR, "baselines");
const CURRENT_DIR = path.resolve(SNAPSHOTS_DIR, "current");
const DIFFS_DIR = path.resolve(SNAPSHOTS_DIR, "diffs");
const REPORT_MD_PATH = path.resolve(SNAPSHOTS_DIR, "REPORT.md");
const REPORT_HTML_PATH = path.resolve(SNAPSHOTS_DIR, "report.html");

const PORT = Number(process.env.CAMPLY_SNAPSHOT_PORT || "5173");
const BASE_URL = `http://localhost:${PORT}`;

/**
 * Snapshot scenario definition.
 */
interface Scenario {
  name: string;
  route: string;
  viewport: { width: number; height: number };
  theme: "light" | "dark";
  description: string;
  emptyScans?: boolean;
  partialOperations?: boolean;
  missingMeasurements?: boolean;
  action?: (page: Page) => Promise<void>;
}

/** Reveal a deterministic synthetic password for visual checks, then restore Web Crypto. */
async function revealSnapshotPassword(page: Page): Promise<void> {
  await page.evaluate(`
    Object.defineProperty(crypto, "getRandomValues", {
      configurable: true,
      value: (bytes) => {
        for (let index = 0; index < bytes.length; index++) bytes[index] = index * 17;
        return bytes;
      },
    });
  `);
  await page.getByRole("button", { name: "Generate Password" }).click();
  await page.getByRole("button", { name: "Copy password" }).waitFor();
  await page.evaluate(() => {
    Reflect.deleteProperty(crypto, "getRandomValues");
  });
}

/**
 * Standard scenarios covering pages, themes, viewports, and components.
 */
const SCENARIOS: Scenario[] = [
  {
    name: "admin-create-user-password-desktop-light",
    route: "/admin/users",
    viewport: { width: 1280, height: 800 },
    theme: "light",
    description:
      "Create user dialog reveals a generated password with a copy action",
    action: async (page: Page) => {
      await page.getByRole("button", { name: "Create User" }).click();
      await revealSnapshotPassword(page);
    },
  },
  {
    name: "admin-reset-password-mobile-light",
    route: "/admin/users",
    viewport: { width: 390, height: 844 },
    theme: "light",
    description:
      "User row reset dialog shows generated password and copy action on mobile",
    action: async (page: Page) => {
      await page
        .getByRole("button", { name: "Reset password for camper@example.test" })
        .click();
      await revealSnapshotPassword(page);
    },
  },
  {
    name: "admin-user-detail-reset-password-desktop-dark",
    route: "/admin/users/user-snap-2",
    viewport: { width: 1280, height: 800 },
    theme: "dark",
    description:
      "User detail reset dialog reveals a generated password in dark mode",
    action: async (page: Page) => {
      await page.getByRole("button", { name: "Reset Password" }).click();
      await revealSnapshotPassword(page);
    },
  },
  {
    name: "admin-operations-partial-desktop-light",
    route: "/admin/operations",
    viewport: { width: 1280, height: 800 },
    theme: "light",
    description:
      "Partial worker inspection preserves known counts and marks unanswered counts unknown",
    partialOperations: true,
  },
  {
    name: "admin-api-trends-table-desktop-light",
    route: "/admin/operations?tab=api&api_view=table",
    viewport: { width: 1280, height: 800 },
    theme: "light",
    description:
      "API trend table distinguishes missing measurements from measured zero",
    missingMeasurements: true,
  },
  {
    name: "admin-overview-desktop-light",
    route: "/admin",
    viewport: { width: 1280, height: 800 },
    theme: "light",
    description: "Admin overview with synthetic data (desktop, light)",
  },
  {
    name: "admin-overview-desktop-dark",
    route: "/admin",
    viewport: { width: 1280, height: 800 },
    theme: "dark",
    description: "Admin overview with synthetic data (desktop, dark)",
  },
  {
    name: "admin-overview-mobile-light",
    route: "/admin",
    viewport: { width: 390, height: 844 },
    theme: "light",
    description: "Admin overview with synthetic data (mobile, light)",
  },
  {
    name: "admin-users-desktop-light",
    route: "/admin/users",
    viewport: { width: 1280, height: 800 },
    theme: "light",
    description: "Admin users with synthetic data (desktop, light)",
  },
  {
    name: "admin-scans-desktop-light",
    route: "/admin/scans",
    viewport: { width: 1280, height: 800 },
    theme: "light",
    description: "Admin scans with synthetic data (desktop, light)",
  },
  {
    name: "admin-operations-desktop-light",
    route: "/admin/operations",
    viewport: { width: 1280, height: 800 },
    theme: "light",
    description: "Admin operations with synthetic data (desktop, light)",
  },
  {
    name: "admin-operations-desktop-dark",
    route: "/admin/operations",
    viewport: { width: 1280, height: 800 },
    theme: "dark",
    description: "Admin operations with synthetic data (desktop, dark)",
  },
  {
    name: "admin-operations-mobile-light",
    route: "/admin/operations",
    viewport: { width: 390, height: 844 },
    theme: "light",
    description: "Admin operations with synthetic data (mobile, light)",
  },
  {
    name: "admin-audit-desktop-light",
    route: "/admin/audit",
    viewport: { width: 1280, height: 800 },
    theme: "light",
    description: "Admin audit with synthetic data (desktop, light)",
  },
  {
    name: "admin-user-detail-desktop-light",
    route: "/admin/users/user-snap-2",
    viewport: { width: 1280, height: 800 },
    theme: "light",
    description: "Admin user detail with synthetic data (desktop, light)",
  },
  {
    name: "admin-scan-detail-desktop-light",
    route: "/admin/scans/scan-mock-1",
    viewport: { width: 1280, height: 800 },
    theme: "light",
    description: "Admin scan detail with synthetic data (desktop, light)",
  },
  {
    name: "admin-target-detail-desktop-light",
    route: "/admin/targets/target-mock-1",
    viewport: { width: 1280, height: 800 },
    theme: "light",
    description: "Admin target detail with synthetic data (desktop, light)",
  },
  {
    name: "home-desktop-light",
    route: "/",
    viewport: { width: 1280, height: 800 },
    theme: "light",
    description:
      "Home landing page hero, search bar, and features (Desktop, Light)",
  },
  {
    name: "home-desktop-dark",
    route: "/",
    viewport: { width: 1280, height: 800 },
    theme: "dark",
    description:
      "Home landing page hero, search bar, and features (Desktop, Dark)",
  },
  {
    name: "home-mobile-light",
    route: "/",
    viewport: { width: 390, height: 844 },
    theme: "light",
    description: "Home landing page mobile responsive layout (Mobile, Light)",
  },
  {
    name: "dashboard-desktop-light",
    route: "/dashboard",
    viewport: { width: 1280, height: 800 },
    theme: "light",
    description:
      "User dashboard with active scan cards and stat metrics (Desktop, Light)",
  },
  {
    name: "dashboard-desktop-dark",
    route: "/dashboard",
    viewport: { width: 1280, height: 800 },
    theme: "dark",
    description:
      "User dashboard with active scan cards and stat metrics (Desktop, Dark)",
  },
  {
    name: "dashboard-mobile-light",
    route: "/dashboard",
    viewport: { width: 390, height: 844 },
    theme: "light",
    description: "User dashboard mobile stacked layout (Mobile, Light)",
  },
  {
    name: "dashboard-empty-desktop-light",
    route: "/dashboard",
    viewport: { width: 1280, height: 800 },
    theme: "light",
    emptyScans: true,
    description:
      "Dashboard empty state when user has zero active scans (Desktop, Light)",
  },
  {
    name: "scan-edit-dialog-desktop-light",
    route: "/dashboard",
    viewport: { width: 1280, height: 800 },
    theme: "light",
    description: "Edit scan dialog prefilled with saved dates and filters",
    action: async (page: Page) => {
      await page
        .getByRole("button", { name: "Edit scan", exact: true })
        .first()
        .click();
      await page.getByRole("dialog", { name: "Edit Scan" }).waitFor();
    },
  },
  {
    name: "scan-edit-dialog-mobile-dark",
    route: "/dashboard",
    viewport: { width: 390, height: 844 },
    theme: "dark",
    description: "Edit scan dialog fits a mobile viewport in dark mode",
    action: async (page: Page) => {
      await page
        .getByRole("button", { name: "Edit scan", exact: true })
        .first()
        .click();
      await page.getByRole("dialog", { name: "Edit Scan" }).waitFor();
    },
  },
  {
    name: "scan-delete-error-desktop-light",
    route: "/dashboard",
    viewport: { width: 1280, height: 800 },
    theme: "light",
    description: "Delete failure stays in its confirmation dialog for retry",
    action: async (page: Page) => {
      await page.route("**/api/scans/scan-mock-1", (route) =>
        route.fulfill({
          status: 503,
          contentType: "application/json",
          body: JSON.stringify({
            detail: "Unable to delete scan. Please try again.",
          }),
        }),
      );
      await page
        .getByRole("button", { name: "Delete scan", exact: true })
        .first()
        .click();
      await page.getByRole("button", { name: "Delete", exact: true }).click();
      await page.getByRole("alert").waitFor();
      if (new URL(page.url()).pathname !== "/dashboard")
        throw new Error("Deleting navigated away from the dashboard");
    },
  },
  {
    name: "scan-form-dialog-desktop-light",
    route: "/dashboard",
    viewport: { width: 1280, height: 800 },
    theme: "light",
    description:
      "Create New Scan modal dialog open with form inputs (Desktop, Light)",
    action: async (page: Page) => {
      const button = page.locator("button:has-text('New Scan')");
      await button.waitFor({ state: "visible", timeout: 5000 });
      await button.click();
      await page.waitForSelector("[role='dialog']", { timeout: 5000 });
      await page.waitForTimeout(200);
    },
  },
  {
    name: "scan-form-checkin-calendar-desktop-light",
    route: "/dashboard",
    viewport: { width: 1280, height: 800 },
    theme: "light",
    description: "Scan modal with Check-in DatePicker calendar open",
    action: async (page: Page) => {
      const button = page.locator("button:has-text('New Scan')");
      await button.waitFor({ state: "visible", timeout: 5000 });
      await button.click();
      await page.waitForSelector("[role='dialog']", { timeout: 5000 });
      await page.locator("#start_date").click();
      await page.waitForSelector("[role='dialog'] [role='dialog']", {
        timeout: 5000,
      });
      await page.waitForTimeout(200);
    },
  },
  {
    name: "scan-form-checkout-calendar-desktop-light",
    route: "/dashboard",
    viewport: { width: 1280, height: 800 },
    theme: "light",
    description:
      "Scan modal with Check-out DatePicker calendar open anchored to future start date",
    action: async (page: Page) => {
      const button = page.locator("button:has-text('New Scan')");
      await button.waitFor({ state: "visible", timeout: 5000 });
      await button.click();
      await page.waitForSelector("[role='dialog']", { timeout: 5000 });
      await page.locator("#start_date").click();
      await page.waitForSelector("[role='dialog'] [role='dialog']", {
        timeout: 5000,
      });
      // Click next month
      await page.locator("button[aria-label='Next month']").click();
      await page.waitForTimeout(100);
      // Select 15th
      await page
        .locator("[role='dialog'] button:has-text('15')")
        .last()
        .click();
      await page.waitForTimeout(200);
      // Open check-out picker
      await page.locator("#end_date").click();
      await page.waitForSelector("[role='dialog'] [role='dialog']", {
        timeout: 5000,
      });
      await page.waitForTimeout(200);
    },
  },
  {
    name: "early-access-desktop-light",
    route: "/dashboard",
    viewport: { width: 1280, height: 800 },
    theme: "light",
    description: "Invite-only request gate (Desktop, Light)",
  },
  {
    name: "early-access-mobile-light",
    route: "/dashboard",
    viewport: { width: 390, height: 844 },
    theme: "light",
    description: "Invite-only request gate (Mobile, Light)",
  },
  {
    name: "auth-desktop-light",
    route: "/auth",
    viewport: { width: 1280, height: 800 },
    theme: "light",
    description: "Authentication and login screen (Desktop, Light)",
  },
  {
    name: "auth-desktop-dark",
    route: "/auth",
    viewport: { width: 1280, height: 800 },
    theme: "dark",
    description: "Authentication and login screen (Desktop, Dark)",
  },
  {
    name: "dev-preview-desktop-light",
    route: "/dev/preview",
    viewport: { width: 1280, height: 800 },
    theme: "light",
    description:
      "Design system catalog showcasing scan cards, buttons, badges, and stats (Desktop, Light)",
  },
  {
    name: "dev-preview-desktop-dark",
    route: "/dev/preview",
    viewport: { width: 1280, height: 800 },
    theme: "dark",
    description:
      "Design system catalog showcasing scan cards, buttons, badges, and stats (Desktop, Dark)",
  },
  {
    name: "dev-preview-mobile-light",
    route: "/dev/preview",
    viewport: { width: 390, height: 844 },
    theme: "light",
    description: "Design system catalog mobile layout (Mobile, Light)",
  },
  {
    name: "ethos-desktop-light",
    route: "/ethos",
    viewport: { width: 1280, height: 800 },
    theme: "light",
    description:
      "Project Ethos and open-source principles page (Desktop, Light)",
  },
  {
    name: "providers-desktop-light",
    route: "/providers",
    viewport: { width: 1280, height: 800 },
    theme: "light",
    description: "Supported booking providers and platforms (Desktop, Light)",
  },
  {
    name: "providers-desktop-dark",
    route: "/providers",
    viewport: { width: 1280, height: 800 },
    theme: "dark",
    description: "Supported booking providers and platforms (Desktop, Dark)",
  },
  {
    name: "how-it-works-desktop-light",
    route: "/how-it-works",
    viewport: { width: 1280, height: 800 },
    theme: "light",
    description:
      "How Camply Works architecture and lifecycle explanation (Desktop, Light)",
  },
  {
    name: "how-it-works-desktop-dark",
    route: "/how-it-works",
    viewport: { width: 1280, height: 800 },
    theme: "dark",
    description:
      "How Camply Works architecture and lifecycle explanation (Desktop, Dark)",
  },
  {
    name: "faq-desktop-light",
    route: "/faq",
    viewport: { width: 1280, height: 800 },
    theme: "light",
    description: "Frequently Asked Questions catalog (Desktop, Light)",
  },
  {
    name: "faq-desktop-dark",
    route: "/faq",
    viewport: { width: 1280, height: 800 },
    theme: "dark",
    description: "Frequently Asked Questions catalog (Desktop, Dark)",
  },
  {
    name: "profile-desktop-light",
    route: "/profile",
    viewport: { width: 1280, height: 800 },
    theme: "light",
    description:
      "User profile settings and Pushover notification config (Desktop, Light)",
  },
  {
    name: "profile-desktop-dark",
    route: "/profile",
    viewport: { width: 1280, height: 800 },
    theme: "dark",
    description:
      "User profile settings and Pushover notification config (Desktop, Dark)",
  },
  {
    name: "scan-detail-desktop-light",
    route: "/dashboard/scans/scan-mock-1",
    viewport: { width: 1280, height: 800 },
    theme: "light",
    description:
      "Scan details view displaying found campsites and polling status (Desktop, Light)",
  },
  {
    name: "home-search-dropdown-desktop-light",
    route: "/",
    viewport: { width: 1280, height: 800 },
    theme: "light",
    description:
      "Search autocomplete dropdown displaying matched campgrounds and recreation areas (Desktop, Light)",
    action: async (page: Page) => {
      const input = page.locator("input[placeholder*='Search']");
      await input.waitFor({ state: "visible", timeout: 5000 });
      await input.fill("Yosemite");
      await page.waitForSelector(".cursor-pointer", { timeout: 5000 });
      await page.waitForTimeout(300);
    },
  },
  {
    name: "search-desktop-light",
    route: "/search?q=yosemite",
    viewport: { width: 1280, height: 800 },
    theme: "light",
    description:
      "Search and discovery page with filters, cards, and sorting (Desktop, Light)",
  },
  {
    name: "search-desktop-dark",
    route: "/search?q=yosemite",
    viewport: { width: 1280, height: 800 },
    theme: "dark",
    description:
      "Search and discovery page with filters, cards, and sorting (Desktop, Dark)",
  },
  {
    name: "search-mobile-light",
    route: "/search?q=yosemite",
    viewport: { width: 390, height: 844 },
    theme: "light",
    description:
      "Search and discovery page mobile stacked layout (Mobile, Light)",
  },
];

for (const [name, width] of [
  ["desktop", 1440],
  ["mobile", 375],
] as const) {
  for (const theme of ["light", "dark"] as const) {
    for (const [surface, route] of [
      ["explore", "/search?q=yosemite"],
      ["campground", "/campground/1/232447"],
      ["area", "/rec-area/1/2991"],
    ]) {
      SCENARIOS.push({
        name: `map-${surface}-${name}-${theme}`,
        route,
        viewport: { width, height: 1000 },
        theme,
        description: `${surface} map at ${width}px in ${theme} theme`,
        action: async (page) => {
          await page
            .locator(".camply-map-marker")
            .first()
            .waitFor({ state: "visible" });
        },
      });
    }
  }
}
for (const [name, width, theme] of [
  ["desktop-light", 1440, "light"],
  ["mobile-dark", 375, "dark"],
] as const) {
  SCENARIOS.push({
    name: `map-collapsed-${name}`,
    route: "/search?q=yosemite",
    viewport: { width, height: 1000 },
    theme,
    description:
      "Explore with the map collapsed and list actions still visible",
    action: async (page) => {
      await page.getByRole("button", { name: "Hide map", exact: true }).click();
      await page
        .getByRole("button", { name: "Show map", exact: true })
        .waitFor();
    },
  });
}
SCENARIOS.push({
  name: "map-hover-desktop-light",
  route: "/search?q=yosemite",
  viewport: { width: 1440, height: 1000 },
  theme: "light",
  description: "Map marker hover shows place information",
  action: async (page) => {
    await page.locator(".camply-map-marker").first().hover();
    await page.getByRole("tooltip").waitFor();
  },
});
SCENARIOS.push({
  name: "map-focus-mobile-dark",
  route: "/search?q=yosemite",
  viewport: { width: 375, height: 1000 },
  theme: "dark",
  description:
    "Map marker keyboard focus shows place information in dark theme",
  action: async (page) => {
    await page.locator(".camply-map-marker").first().focus();
    await page.getByRole("tooltip").waitFor();
    const visible = await page.getByRole("tooltip").evaluate((element) => {
      const bounds = element.getBoundingClientRect();
      return bounds.left >= 0 && bounds.right <= window.innerWidth;
    });
    if (!visible)
      throw new Error("Marker tooltip extends beyond the mobile viewport");
  },
});
SCENARIOS.push({
  name: "map-selected-desktop-light",
  route: "/search?q=yosemite",
  viewport: { width: 1440, height: 1000 },
  theme: "light",
  description: "Explore overlapping-place picker with details and monitoring",
  action: async (page) => {
    await page.locator('.camply-map-marker[aria-label="3 places"]').click();
    await page
      .getByRole("button", { name: "View places", exact: true })
      .click();
    await page
      .getByLabel("Selected map location")
      .getByRole("link", { name: "Details" })
      .first()
      .waitFor();
  },
});
SCENARIOS.push({
  name: "map-error-mobile-dark",
  route: "/search?q=yosemite",
  viewport: { width: 375, height: 1000 },
  theme: "dark",
  description: "Recoverable map summary failure on mobile",
  action: async (page) => {
    await page.getByRole("button", { name: "Retry map summary" }).waitFor();
  },
});

/**
 * Mock data used for consistent and deterministic rendering.
 */
const MOCK_USER = {
  id: "user-snap-1",
  email: "camper@camply.app",
  is_invited: true,
  is_admin: false,
  scanning_enabled: true,
  pushover_token: "mock-token-xyz",
};

const MOCK_SCANS = [
  {
    id: "scan-mock-1",
    provider_id: 1,
    campground_id: "232447",
    campground_name: "Upper Pines Campground",
    recreation_area_name: "Yosemite National Park",
    start_date: "2026-07-15",
    end_date: "2026-07-19",
    is_active: true,
    min_stay_length: 2,
    preferred_types: ["STANDARD NONELECTRIC", "TENT ONLY"],
    require_electric: false,
    last_checked_at: "2026-07-01T12:00:00Z",
    found_count: 3,
    created_at: "2026-06-15T08:00:00Z",
  },
  {
    id: "scan-mock-2",
    provider_id: 1,
    campground_id: "232450",
    campground_name: "Camp 4 Walk-In",
    recreation_area_name: "Yosemite National Park",
    start_date: "2026-08-01",
    end_date: "2026-08-03",
    is_active: false,
    min_stay_length: 1,
    preferred_types: ["TENT ONLY"],
    require_electric: false,
    last_checked_at: "2026-07-01T11:45:00Z",
    found_count: 0,
    created_at: "2026-06-20T10:00:00Z",
  },
  {
    id: "scan-mock-3",
    provider_id: 1,
    campground_id: "232449",
    campground_name: "Lower Pines",
    recreation_area_name: "Yosemite National Park",
    start_date: "2026-09-10",
    end_date: "2026-09-14",
    is_active: true,
    min_stay_length: 3,
    preferred_types: ["RV NONELECTRIC"],
    require_electric: true,
    last_checked_at: "2026-07-01T12:05:00Z",
    found_count: 1,
    created_at: "2026-06-25T14:30:00Z",
  },
];

const MOCK_CAMPGROUNDS = [
  {
    id: "232447",
    provider_id: 1,
    recreation_area_id: "2991",
    name: "Upper Pines Campground",
    description: "Located in the heart of Yosemite Valley.",
    country: "United States",
    state: "California",
    longitude: -119.566,
    latitude: 37.739,
    reservable: true,
    enabled: true,
    url: "https://www.recreation.gov/camping/campgrounds/232447",
  },
  {
    id: "232450",
    provider_id: 1,
    recreation_area_id: "2991",
    name: "Camp 4",
    description: "World famous rock climbing camp.",
    country: "United States",
    state: "California",
    longitude: -119.601,
    latitude: 37.742,
    reservable: true,
    enabled: true,
    url: "https://www.recreation.gov/camping/campgrounds/232450",
  },
];

const MOCK_SEARCH_ITEMS = [
  {
    id: "Camp/1/2991/232447",
    entity_type: "Campground",
    provider_id: 1,
    provider_name: "recreation_dot_gov",
    recreation_area_id: "2991",
    recreation_area_name: "Yosemite National Park",
    campground_id: "232447",
    campground_name: "Upper Pines Campground",
    city: "Yosemite Valley",
    state: "CA",
    country: "USA",
    latitude: 37.739,
    longitude: -119.566,
    reservable: true,
    campsite_types: ["STANDARD NONELECTRIC", "RV NONELECTRIC"],
    has_electric: true,
    has_water: true,
    has_sewer: false,
    pets_allowed: true,
    ada_accessible: true,
    max_rv_length: 35,
  },
  {
    id: "RecArea/1/2991",
    entity_type: "RecreationArea",
    provider_id: 1,
    provider_name: "recreation_dot_gov",
    recreation_area_id: "2991",
    recreation_area_name: "Yosemite National Park",
    campground_id: null,
    campground_name: null,
    city: "Yosemite Valley",
    state: "CA",
    country: "USA",
    latitude: 37.74,
    longitude: -119.57,
    reservable: true,
    campsite_types: [],
    has_electric: false,
    has_water: false,
    has_sewer: false,
    pets_allowed: true,
    ada_accessible: true,
    max_rv_length: 0,
  },
  {
    id: "Camp/1/2991/232450",
    entity_type: "Campground",
    provider_id: 1,
    provider_name: "recreation_dot_gov",
    recreation_area_id: "2991",
    recreation_area_name: "Yosemite National Park",
    campground_id: "232450",
    campground_name: "Camp 4 Walk-In",
    city: "Yosemite Valley",
    state: "CA",
    country: "USA",
    latitude: 37.742,
    longitude: -119.601,
    reservable: true,
    campsite_types: ["TENT ONLY"],
    has_electric: false,
    has_water: true,
    has_sewer: false,
    pets_allowed: false,
    ada_accessible: false,
    max_rv_length: 0,
  },
];
const MOCK_SEARCH_RESULTS = MOCK_SEARCH_ITEMS;

/**
 * Check if local server is listening on port.
 *
 * Parameters
 * ----------
 * port : number
 *     Port to check.
 *
 * Returns
 * -------
 * Promise<boolean>
 *     True if server responds.
 */
function isServerRunning(port: number): Promise<boolean> {
  return new Promise((resolve) => {
    const req = http.get(`http://localhost:${port}/`, (res) => {
      resolve(res.statusCode !== undefined);
    });
    req.on("error", () => resolve(false));
    req.setTimeout(1000, () => {
      req.destroy();
      resolve(false);
    });
  });
}

/**
 * Start the Vite development server if not already running.
 *
 * Returns
 * -------
 * Promise<ChildProcess | null>
 *     Child process reference if spawned, null if already running.
 */
async function ensureServerRunning(): Promise<ChildProcess | null> {
  const running = await isServerRunning(PORT);
  if (running) {
    console.log(`📡 Reusing existing frontend server on ${BASE_URL}`);
    return null;
  }

  console.log(`🚀 Starting Vite development server on port ${PORT}...`);
  const serverProcess = spawn(
    "pnpm",
    ["run", "dev", "--port", `${PORT}`, "--base", "/"],
    {
      cwd: FRONTEND_ROOT,
      stdio: "pipe",
      shell: true,
      env: {
        ...process.env,
        GITHUB_REPOSITORY: "",
        // Keep visual coverage of the optional community pages and navigation.
        VITE_ENABLE_COMMUNITY_PAGES: "true",
      },
    },
  );

  const started = await new Promise<boolean>((resolve) => {
    const timeout = setTimeout(() => resolve(false), 15000);
    const interval = setInterval(async () => {
      if (await isServerRunning(PORT)) {
        clearInterval(interval);
        clearTimeout(timeout);
        resolve(true);
      }
    }, 250);
  });

  if (!started) {
    serverProcess.kill();
    throw new Error(
      `Failed to start Vite dev server on port ${PORT} within 15 seconds.`,
    );
  }

  console.log(`✅ Vite server started on ${BASE_URL}`);
  return serverProcess;
}

/**
 * Setup deterministic network route interception on page.
 *
 * Parameters
 * ----------
 * page : Page
 *     Playwright page.
 * scenario : Scenario
 *     Auth and scan state needed for the requested snapshot.
 */
async function setupPageMocks(page: Page, scenario: Scenario): Promise<void> {
  await setupAdminSnapshotMocks(page, scenario);
  const invitationRequired = scenario.name.startsWith("early-access-");
  const signedOut = scenario.route === "/auth";
  await page.route("**/api/auth-config", (route) => {
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        auth_mode: "session",
        auth0_audience: null,
        auto_login: false,
        signup_enabled: false,
        invite_only: invitationRequired,
        auth0_domain: null,
        auth0_client_id: null,
      }),
    });
  });

  await page.route("**/api/me", (route) => {
    route.fulfill({
      status: signedOut ? 401 : 200,
      contentType: "application/json",
      body: JSON.stringify({
        ...MOCK_USER,
        is_invited: !invitationRequired,
        is_admin: scenario.route.startsWith("/admin"),
      }),
    });
  });

  await page.route("**/api/scans", (route) => {
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        scans: scenario.emptyScans ? [] : MOCK_SCANS,
        total: scenario.emptyScans ? 0 : MOCK_SCANS.length,
      }),
    });
  });

  await page.route("**/api/scans/scan-mock-1", (route) => {
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        ...MOCK_SCANS[0],
        results: [
          {
            campsite_id: "site-401",
            campsite_name: "Upper Pines Site 042",
            available_dates: ["2026-07-15", "2026-07-16"],
          },
          {
            campsite_id: "site-402",
            campsite_name: "Upper Pines Site 048",
            available_dates: ["2026-07-17", "2026-07-18"],
          },
        ],
      }),
    });
  });

  await page.route("**/api/search/explore*", (route) => {
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        items: MOCK_SEARCH_ITEMS,
        total: MOCK_SEARCH_ITEMS.length,
        page: 1,
        page_size: 20,
        total_pages: 1,
        facets: {
          providers: { recreation_dot_gov: 2 },
          states: { CA: 2 },
          entity_types: { Campground: 2 },
        },
      }),
    });
  });

  await page.route(
    (url) => url.pathname === "/api/search",
    (route) => {
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(MOCK_SEARCH_ITEMS),
      });
    },
  );

  await page.route("**/api/providers", (route) => {
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify([
        {
          id: 1,
          name: "Recreation.gov",
          description: "Federal booking",
          url: "https://recreation.gov",
          enabled: true,
        },
      ]),
    });
  });
  const raster = new PNG({ width: 256, height: 256 });
  for (let i = 0; i < raster.data.length; i += 4) {
    raster.data[i] = 225;
    raster.data[i + 1] = 235;
    raster.data[i + 2] = 219;
    raster.data[i + 3] = 255;
  }
  await page.route("https://tile.openstreetmap.org/**", (route) =>
    route.fulfill({
      contentType: "image/png",
      headers: { "Access-Control-Allow-Origin": "*" },
      body: PNG.sync.write(raster),
    }),
  );
  const bounds = { west: -119.61, east: -119.55, south: 37.73, north: 37.75 };
  await page.route("**/api/search/map/summary*", (route) =>
    route.fulfill({
      status: scenario.name.startsWith("map-error") ? 503 : 200,
      contentType: "application/json",
      body: JSON.stringify({
        total: 3,
        mappable_total: 3,
        unmappable_total: 0,
        bounds,
      }),
    }),
  );
  await page.route(
    (url) => url.pathname === "/api/search/map",
    (route) => {
      const query = new URL(route.request().url()).searchParams;
      const viewport = Object.fromEntries(
        ["west", "south", "east", "north"].map((key) => [
          key,
          Number(query.get(key)),
        ]),
      );
      return route.fulfill({
        contentType: "application/json",
        body: JSON.stringify({
          viewport,
          grid_level: 12,
          represented_total: 3,
          features:
            scenario.name.startsWith("map-hover") ||
            scenario.name.startsWith("map-focus")
              ? [
                  {
                    kind: "location",
                    cell_id: "12:0:0",
                    item: MOCK_SEARCH_ITEMS[0],
                  },
                ]
              : [
                  {
                    kind: "group",
                    cell_id: "12:0:0",
                    count: 3,
                    latitude: 37.74,
                    longitude: -119.58,
                    bounds,
                  },
                ],
        }),
      });
    },
  );
  await page.route("**/api/search/map/members*", (route) =>
    route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        items: MOCK_SEARCH_ITEMS,
        total: 3,
        next_cursor: null,
      }),
    }),
  );
  await page.route("**/api/provider/1", (route) =>
    route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        id: 1,
        name: "Recreation.gov",
        description: "Federal booking",
        url: "https://example.test",
        enabled: true,
      }),
    }),
  );
  await page.route("**/api/campground/1/232447", (route) =>
    route.fulfill({
      contentType: "application/json",
      body: JSON.stringify(MOCK_CAMPGROUNDS[0]),
    }),
  );
  await page.route("**/api/rec-area/1/2991", (route) =>
    route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        id: "2991",
        provider_id: 1,
        name: "Yosemite National Park",
        description: "Synthetic recreation area for map verification.",
        latitude: 37.74,
        longitude: -119.58,
        state: "CA",
        country: "US",
        reservable: true,
        enabled: true,
        url: "https://example.test",
      }),
    }),
  );
  await page.route("**/api/rec-area/1/2991/campgrounds", (route) =>
    route.fulfill({
      contentType: "application/json",
      body: JSON.stringify(MOCK_CAMPGROUNDS),
    }),
  );
}

/**
 * Configure page environment for visual determinism.
 *
 * Parameters
 * ----------
 * page : Page
 *     Playwright page.
 * scenario : Scenario
 *     Scenario details.
 */
async function preparePage(page: Page, scenario: Scenario): Promise<void> {
  await page.clock.setFixedTime(new Date("2026-10-10T12:00:00Z"));
  await page.setViewportSize(scenario.viewport);
  await page.emulateMedia({
    colorScheme: scenario.theme,
    reducedMotion: scenario.route.startsWith("/admin")
      ? "reduce"
      : "no-preference",
  });

  // Set theme via localStorage and DOM initialization
  await page.addInitScript(
    ({ theme }) => {
      localStorage.setItem("camply-ui-theme", theme);
      localStorage.setItem("vite-ui-theme", theme);
      document.documentElement.classList.remove("light", "dark");
      document.documentElement.classList.add(theme);
    },
    { theme: scenario.theme },
  );

  await setupPageMocks(page, scenario);

  await page.goto(`${BASE_URL}${scenario.route}`, { waitUntil: "networkidle" });

  // Enforce zero CSS animations and transitions for pixel stability
  await page.addStyleTag({
    content: `
      *, *::before, *::after {
        -moz-transition: none !important;
        transition: none !important;
        -webkit-transition: none !important;
        -moz-animation: none !important;
        animation: none !important;
        -webkit-animation: none !important;
        caret-color: transparent !important;
      }
    `,
  });

  // Ensure fonts are loaded
  await page.evaluate(() => document.fonts.ready);

  if (scenario.route === "/dashboard" && !scenario.emptyScans) {
    try {
      await page.waitForSelector("text=Upper Pines Campground", {
        timeout: 4000,
      });
    } catch {
      // Continue if selector is not found within timeout
    }
  }

  if (scenario.route.startsWith("/admin")) {
    await page.waitForFunction(
      () => document.querySelectorAll(".animate-spin").length === 0,
    );
  }

  if (
    scenario.route.startsWith("/search") ||
    scenario.name.startsWith("map-")
  ) {
    await page.waitForFunction(
      () =>
        !Array.from(document.querySelectorAll('[role="status"]')).some(
          (element) => element.textContent === "Loading map…",
        ),
    );
  }

  // Settle time for layout rendering
  await page.waitForTimeout(200);

  if (scenario.action) {
    await scenario.action(page);
  }
  if (scenario.name.startsWith("map-"))
    await page.evaluate(() => window.scrollTo(0, 0));
}

/**
 * Generate Markdown snapshot report with links, status, and agent instructions.
 *
 * Parameters
 * ----------
 * results : SnapshotResult[]
 *     Array of test outcomes.
 *
 * Returns
 * -------
 * string
 *     Formatted GitHub markdown report.
 */
function generateMarkdownReport(results: SnapshotResult[]): string {
  const total = results.length;
  const unchanged = results.filter((r) => r.status === "UNCHANGED").length;
  const modified = results.filter((r) => r.status === "MODIFIED").length;
  const newCount = results.filter((r) => r.status === "NEW").length;
  const timestamp = new Date().toISOString();

  let md = `# 📸 UI Snapshot & Visual Feedback Report\n\n`;
  md += `**Generated**: \`${timestamp}\`  \n`;
  md += `**Total Views**: **${total}** | ✅ Unchanged: **${unchanged}** | ⚠️ Modified: **${modified}** | 🆕 New: **${newCount}**\n\n`;

  md += `---\n\n`;

  md += `## 🤖 AI Agent Feedback Loop Instructions\n\n`;
  md += `When evaluating UI changes or diagnosing unexpected visual diffs:\n`;
  md += `1. **Inspect Modified Views**: If any snapshot indicates **⚠️ MODIFIED**, open the **Diff** and **Current** image links below using the \`view_file\` tool.\n`;
  md += `2. **Verify Visual Intent**:\n`;
  md += `   - **Layout & Spacing**: Confirm elements are properly aligned without accidental margin/padding collapses.\n`;
  md += `   - **Theme Consistency**: Verify dark and light modes preserve legible contrast and proper background tokens.\n`;
  md += `   - **Responsiveness**: Verify text wraps smoothly on mobile (390px) without horizontal clipping.\n`;
  md += `3. **Iterate or Accept**:\n`;
  md += `   - If the change is an unintended regression, refine the CSS / TSX code and run \`task snapshot\` to verify.\n`;
  md += `   - If the change is intended, run \`task snapshot:update\` to bless the updated baseline.\n\n`;

  md += `---\n\n`;
  md += `## 📊 Snapshot Results Summary\n\n`;
  md += `| Snapshot | Viewport | Theme | Status | Diff % | Baseline Image | Current Image | Visual Diff |\n`;
  md += `| :--- | :---: | :---: | :---: | :---: | :--- | :--- | :--- |\n`;

  for (const r of results) {
    const statusIcon =
      r.status === "UNCHANGED"
        ? "✅ UNCHANGED"
        : r.status === "MODIFIED"
          ? "⚠️ MODIFIED"
          : "🆕 NEW";

    const diffPctStr = r.diffPercentage.toFixed(2) + "%";
    const baseLink = r.baselinePath
      ? `[\`${path.basename(r.baselinePath)}\`](file://${r.baselinePath})`
      : "-";
    const currLink = `[\`${path.basename(r.currentPath)}\`](file://${r.currentPath})`;
    const diffLink = r.diffPath
      ? `[\`diff\` (🔍 view)](file://${r.diffPath})`
      : "-";

    md += `| **${r.name}** | ${r.viewport} | ${r.theme} | ${statusIcon} | \`${diffPctStr}\` | ${baseLink} | ${currLink} | ${diffLink} |\n`;
  }

  if (modified > 0) {
    md += `\n---\n\n## ⚠️ Modified Visual Snapshots\n\n`;
    for (const r of results.filter((x) => x.status === "MODIFIED")) {
      md += `### \`${r.name}\` (${r.diffPercentage.toFixed(2)}% pixel mismatch)\n\n`;
      md += `> ${r.description}\n\n`;
      md += `| Baseline | Current | Highlighted Diff |\n`;
      md += `| :---: | :---: | :---: |\n`;
      md += `| ![Baseline](${r.baselinePath}) | ![Current](${r.currentPath}) | ![Diff](${r.diffPath}) |\n\n`;
    }
  }

  return md;
}

/** Save the Markdown index and HTML gallery pointing to local screenshots. */
function writeReports(results: SnapshotResult[]): void {
  for (const [file, contents] of [
    [REPORT_MD_PATH, generateMarkdownReport(results)],
    [REPORT_HTML_PATH, generateHtmlReport(results)],
  ]) {
    fs.writeFileSync(
      file,
      contents.replace(/[ \t]+$/gm, "").trimEnd() + "\n",
      "utf-8",
    );
  }
  console.log(`📄 Markdown Report: ${REPORT_MD_PATH}`);
  console.log(`🌐 Local HTML Gallery: ${REPORT_HTML_PATH}`);
}

/** Rebuild reports from existing captures without running Vite or a browser. */
function reportExistingScreenshots(): void {
  const results = SCENARIOS.flatMap((scenario) => {
    const currentPath = path.join(CURRENT_DIR, `${scenario.name}.png`);
    if (!fs.existsSync(currentPath)) return [];
    return [
      recordSnapshot(
        SNAPSHOTS_DIR,
        {
          name: scenario.name,
          description: scenario.description,
          viewport: `${scenario.viewport.width}x${scenario.viewport.height}`,
          theme: scenario.theme,
        },
        fs.readFileSync(currentPath),
        { createBaseline: false },
      ),
    ];
  });
  if (!results.length)
    throw new Error("No saved captures found. Run task snapshot first.");
  console.log(
    `Comparing ${results.length} of ${SCENARIOS.length} saved screenshot views.`,
  );
  writeReports(results);
}

/**
 * Main snapshot execution entrypoint.
 */
async function main(): Promise<void> {
  const args = process.argv.slice(2);
  const isUpdate = args.includes("--update");
  const isCheck = args.includes("--check");
  if (args.includes("--report-only")) {
    reportExistingScreenshots();
    return;
  }

  // Ensure directories exist
  [SNAPSHOTS_DIR, BASELINES_DIR, CURRENT_DIR, DIFFS_DIR].forEach((dir) => {
    if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
  });

  const serverProcess = await ensureServerRunning();
  let browser: Browser | null = null;

  try {
    console.log("🌐 Launching headless browser...");
    browser = await chromium.launch({
      headless: true,
      args: [
        "--no-sandbox",
        "--disable-setuid-sandbox",
        "--disable-animations",
        "--use-angle=swiftshader",
        "--enable-unsafe-swiftshader",
      ],
    });

    const context = await browser.newContext({ timezoneId: "UTC" });
    const page = await context.newPage();
    await page.clock.setFixedTime(new Date("2026-10-10T12:00:00Z"));

    const results: SnapshotResult[] = [];
    console.log(
      `\n📸 Capturing and analyzing ${SCENARIOS.length} UI snapshot views...\n`,
    );

    for (const scenario of SCENARIOS) {
      process.stdout.write(`  ⏳ Capturing [${scenario.name}]... `);
      await preparePage(page, scenario);

      const screenshotBuf = await page.screenshot({ fullPage: true });
      const result = recordSnapshot(
        SNAPSHOTS_DIR,
        {
          name: scenario.name,
          description: scenario.description,
          viewport: `${scenario.viewport.width}x${scenario.viewport.height}`,
          theme: scenario.theme,
        },
        screenshotBuf,
        { update: isUpdate },
      );
      results.push(result);
      console.log(
        isUpdate
          ? `🔄 UPDATED (${result.status.toLowerCase()})`
          : result.status === "MODIFIED"
            ? `⚠️ MODIFIED (${result.diffPercentage.toFixed(2)}% diff)`
            : result.status === "NEW"
              ? "🆕 NEW BASELINE"
              : "✅ MATCH",
      );
    }

    writeReports(results);

    const modifiedViews = results.filter((r) => r.status === "MODIFIED");
    if (isUpdate) {
      console.log(
        `Accepted baselines. The HTML gallery preserves the comparison for ${modifiedViews.length} modified views.`,
      );
    } else if (modifiedViews.length > 0) {
      console.log(
        `⚠️  Detected ${modifiedViews.length} visually modified view(s):`,
      );
      for (const m of modifiedViews) {
        console.log(`   - ${m.name}: ${m.diffPercentage.toFixed(2)}% diff`);
        console.log(`     Diff Image: file://${m.diffPath}`);
      }
      console.log(
        "\n💡 Review with `view_file` or run `task snapshot:update` if changes are expected.",
      );

      if (isCheck) {
        console.error(
          "\n❌ Visual regression check failed: modified snapshots detected in --check mode.",
        );
        process.exit(1);
      }
    } else {
      console.log("🎉 All snapshots match baselines perfectly!");
    }
  } finally {
    if (browser) await browser.close();
    if (serverProcess) {
      console.log("🛑 Stopping spawned Vite dev server...");
      serverProcess.kill();
    }
  }
}

main().catch((err) => {
  console.error("Fatal error during snapshot execution:", err);
  process.exit(1);
});
