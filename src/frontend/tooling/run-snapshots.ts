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
import os from "os";
import { fileURLToPath } from "url";
import { spawn, execSync, type ChildProcess } from "child_process";
import {
  chromium,
  type Browser,
  type Locator,
  type Page,
} from "@playwright/test";
import { PNG } from "pngjs";
import { setupAdminSnapshotMocks } from "./admin-snapshot-mocks";
import { destinationDetails } from "../test/destination-details";
import {
  navigateToSnapshot,
  waitForSnapshotAssets,
  waitForSnapshotContent,
  type SnapshotReadyContent,
} from "./snapshot-navigation";
import {
  generateHtmlReport,
  recordSnapshot,
  type SnapshotResult,
} from "./snapshot-report";

if (fs.existsSync("/tmp/camply-browser-deps/root/usr/lib/x86_64-linux-gnu")) {
  process.env.LD_LIBRARY_PATH = `/tmp/camply-browser-deps/root/usr/lib/x86_64-linux-gnu:/tmp/camply-browser-deps/root/lib/x86_64-linux-gnu:${process.env.LD_LIBRARY_PATH || ""}`;
  process.env.FONTCONFIG_PATH = "/tmp/camply-browser-deps";
}

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const FRONTEND_ROOT = path.resolve(__dirname, "..", "..", "..");
const SNAPSHOTS_DIR = path.resolve(FRONTEND_ROOT, "tmp", "snapshots");
const BASELINES_DIR = path.resolve(
  FRONTEND_ROOT,
  "tests",
  "frontend",
  "snapshots",
  "baselines",
);
const CURRENT_DIR = path.resolve(SNAPSHOTS_DIR, "current");
const DIFFS_DIR = path.resolve(SNAPSHOTS_DIR, "diffs");
const REPORT_MD_PATH = path.resolve(SNAPSHOTS_DIR, "REPORT.md");
const REPORT_HTML_PATH = path.resolve(SNAPSHOTS_DIR, "report.html");

const DEFAULT_PORT = "5197";
const PORT = Number(process.env.CAMPLY_SNAPSHOT_PORT || DEFAULT_PORT);
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
  areaScans?: boolean;
  partialOperations?: boolean;
  missingMeasurements?: boolean;
  manyCampsites?: boolean;
  enrichment?: boolean;
  overflowOnly?: boolean;
  readyContent?: SnapshotReadyContent;
  authState?: "signup" | "forced-password";
  longValues?: boolean;
  reducedMotion?: boolean;
  touch?: boolean;
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

async function scrollToTop(page: Page): Promise<void> {
  await page.evaluate(() => window.scrollTo({ top: 0, behavior: "instant" }));
  await page.waitForFunction(() => {
    const top = document.querySelector("header")?.getBoundingClientRect().top;
    if (top !== undefined && Math.abs(top) <= 1) return true;
    window.scrollTo({ top: 0, behavior: "instant" });
    return false;
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
    name: "admin-area-scan-detail-desktop-light",
    route: "/admin/scans/area-scan-mock-1",
    viewport: { width: 1280, height: 800 },
    theme: "light",
    description:
      "Admin area scan detail with partial coverage members and attributed results (desktop, light)",
  },
  {
    name: "admin-area-scan-detail-mobile-dark",
    route: "/admin/scans/area-scan-mock-1",
    viewport: { width: 390, height: 844 },
    theme: "dark",
    description:
      "Admin area scan detail with partial coverage members and attributed results (mobile, dark)",
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
  ...(["desktop", "mobile"] as const).map((size) => ({
    name: `dashboard-expanded-${size}-${size === "desktop" ? "light" : "dark"}`,
    route: "/dashboard",
    viewport:
      size === "desktop"
        ? { width: 1280, height: 800 }
        : { width: 390, height: 844 },
    theme: size === "desktop" ? ("light" as const) : ("dark" as const),
    description: "Expanded campground group preserves scan links and controls",
    action: async (page: Page) => {
      await page.locator("details > summary").first().click();
      await page
        .getByRole("button", { name: "Edit scan", exact: true })
        .first()
        .waitFor();
      if (
        await page.evaluate(
          () => document.documentElement.scrollWidth > window.innerWidth,
        )
      )
        throw new Error("Expanded campground group overflows the viewport");
    },
  })),
  {
    name: "scan-edit-dialog-desktop-light",
    route: "/dashboard",
    viewport: { width: 1280, height: 800 },
    theme: "light",
    description: "Edit scan dialog prefilled with saved dates and filters",
    action: async (page: Page) => {
      await page.locator("details > summary").first().click();
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
      await page.locator("details > summary").first().click();
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
      await page.locator("details > summary").first().click();
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
    action: async (page: Page) => {
      await page.getByLabel("Notification provider").waitFor();
    },
  },
  {
    name: "profile-desktop-dark",
    route: "/profile",
    viewport: { width: 1280, height: 800 },
    theme: "dark",
    description:
      "User profile settings and Pushover notification config (Desktop, Dark)",
    action: async (page: Page) => {
      await page.getByLabel("Notification provider").waitFor();
    },
  },
  {
    name: "profile-ntfy-desktop-dark",
    route: "/profile",
    viewport: { width: 1280, height: 800 },
    theme: "dark",
    description:
      "ntfy server/topic copying and notification testing (Desktop, Dark)",
    action: async (page: Page) => {
      await page.getByLabel("Notification provider").selectOption("ntfy");
    },
  },
  {
    name: "profile-ntfy-mobile-light",
    route: "/profile",
    viewport: { width: 390, height: 844 },
    theme: "light",
    description:
      "Custom ntfy server, topic copying and notification testing (Mobile, Light)",
    action: async (page: Page) => {
      await page.getByLabel("Notification provider").selectOption("ntfy");
      await page
        .getByLabel("ntfy server", { exact: true })
        .selectOption("custom");
      await page
        .getByLabel("Your ntfy server URL")
        .fill("https://ntfy.example.test");
    },
  },
  {
    name: "scan-detail-desktop-light",
    route: "/dashboard/scans/scan-mock-1",
    viewport: { width: 1280, height: 800 },
    theme: "light",
    description:
      "Interactive availability calendar with deduplicated campsite cards and cohesive scan header (Desktop, Light)",
  },
  ...(["light", "dark"] as const).map((theme) => ({
    name: `scan-detail-mobile-${theme}`,
    route: "/dashboard/scans/scan-mock-1",
    viewport: { width: 375, height: 812 },
    theme,
    description: `Interactive availability calendar and deduplicated campsite cards (Mobile, ${theme})`,
  })),
  {
    name: "scan-detail-desktop-dark",
    route: "/dashboard/scans/scan-mock-1",
    viewport: { width: 1280, height: 800 },
    theme: "dark",
    description:
      "Interactive availability calendar with deduplicated campsite cards and cohesive scan header (Desktop, Dark)",
  },
  ...(["desktop", "mobile"] as const).map((size) => ({
    name: `scan-detail-grid-${size}-${size === "desktop" ? "light" : "dark"}`,
    route: "/dashboard/scans/scan-mock-1",
    viewport:
      size === "desktop"
        ? { width: 1280, height: 800 }
        : { width: 375, height: 812 },
    theme: size === "desktop" ? ("light" as const) : ("dark" as const),
    description: `Sites x Dates availability grid with inspected stay details (${size}, ${size === "desktop" ? "light" : "dark"})`,
    action: async (page: Page) => {
      const results = page.getByRole("region", { name: "Found campsites" });
      await results.getByRole("button", { name: "Grid" }).click();
      await results
        .getByRole("button", { name: /Upper Pines Site 042.*Nov 15, 2026/i })
        .click();
      await results
        .getByRole("region", { name: "Selected stay details" })
        .waitFor();
      if (
        await page.evaluate(
          () => document.documentElement.scrollWidth > window.innerWidth,
        )
      )
        throw new Error("Availability grid overflows the viewport");
      await scrollToTop(page);
    },
  })),
  ...(["desktop", "mobile"] as const).map((size) => ({
    name: `scan-detail-paginated-${size}-${size === "desktop" ? "light" : "dark"}`,
    route: "/dashboard/scans/scan-mock-1",
    viewport:
      size === "desktop"
        ? { width: 1280, height: 800 }
        : { width: 375, height: 812 },
    theme: size === "desktop" ? ("light" as const) : ("dark" as const),
    manyCampsites: true,
    description:
      "Deduplicated campsite cards stay bounded to ten sites per page",
    action: async (page: Page) => {
      const results = page.getByRole("region", { name: "Found campsites" });
      await results.getByText("1–10 of 13 sites").waitFor();
      if (
        (await results
          .getByRole("link", { name: /^View .* on provider website$/ })
          .count()) !== 10
      )
        throw new Error("Campsite pagination must show ten booking actions");
      await results.getByRole("button", { name: "Next campsites" }).click();
      await results.getByText("11–13 of 13 sites").waitFor();
      if (
        await page.evaluate(
          () => document.documentElement.scrollWidth > window.innerWidth,
        )
      )
        throw new Error("Campsite results overflow the viewport");
      await scrollToTop(page);
    },
  })),
  ...(["light", "dark"] as const).flatMap((theme) =>
    (["desktop", "mobile"] as const).map((size) => ({
      name: `area-scan-detail-${size}-${theme}`,
      route: "/dashboard/scans/area-scan-mock-1",
      viewport:
        size === "desktop"
          ? { width: 1280, height: 800 }
          : { width: 390, height: 844 },
      theme,
      description: `Area scan detail with partial coverage and attributed results (${size}, ${theme})`,
      action: async (page: Page) => {
        await page
          .getByRole("region", { name: "Campground coverage" })
          .waitFor();
        if (
          await page.evaluate(
            () => document.documentElement.scrollWidth > window.innerWidth,
          )
        )
          throw new Error("Area scan detail overflows the viewport");
      },
    })),
  ),
  ...(["desktop", "mobile"] as const).map((size) => ({
    name: `area-dashboard-${size}-${size === "desktop" ? "light" : "dark"}`,
    route: "/dashboard",
    viewport:
      size === "desktop"
        ? { width: 1280, height: 800 }
        : { width: 390, height: 844 },
    theme: size === "desktop" ? ("light" as const) : ("dark" as const),
    areaScans: true,
    description: `Dashboard displaying area all-campgrounds and selected-subset scan cards (${size})`,
    action: async (page: Page) => {
      await page.locator("details > summary").first().click();
      await page
        .getByRole("button", { name: "Edit scan", exact: true })
        .first()
        .waitFor();
      if (
        await page.evaluate(
          () => document.documentElement.scrollWidth > window.innerWidth,
        )
      )
        throw new Error("Area dashboard overflows the viewport");
    },
  })),
  ...(["desktop", "mobile"] as const).map((size) => ({
    name: `area-picker-${size}-${size === "desktop" ? "light" : "dark"}`,
    route: "/rec-area/1/2991",
    viewport:
      size === "desktop"
        ? { width: 1280, height: 800 }
        : { width: 390, height: 844 },
    theme: size === "desktop" ? ("light" as const) : ("dark" as const),
    description: `Monitor recreation area dialog with selected campground coverage picker (${size})`,
    action: async (page: Page) => {
      await page
        .getByRole("button", { name: "Monitor recreation area" })
        .click();
      const dialog = page.getByRole("dialog");
      await dialog.waitFor();
      await dialog.getByLabel("Selected campgrounds").click();
      await dialog.getByRole("button", { name: "Select campgrounds…" }).click();
      await dialog.getByText("Upper Pines Campground").first().waitFor();
      await page.waitForTimeout(150);
    },
  })),
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

for (const [name, width] of [
  ["desktop", 1440],
  ["mobile", 375],
] as const) {
  for (const theme of ["light", "dark"] as const) {
    for (const [surface, route] of [
      ["campground", "/campground/1/232447"],
      ["area", "/rec-area/1/2991"],
    ] as const) {
      SCENARIOS.push({
        name: `enrichment-${surface}-${name}-${theme}`,
        route,
        viewport: { width, height: 1000 },
        theme,
        enrichment: true,
        description: `${surface} photo carousel, attribution, and Know before you go below the map at ${width}px in ${theme} theme`,
        action: async (page) => {
          await page
            .getByRole("heading", { name: "Know before you go" })
            .waitFor();
          const carousel = page.getByRole("region", { name: / photos$/ });
          if (
            (await carousel.getByText(/^Photo \d+ of \d+$/).count()) ||
            (await carousel.getByText(/^Credit:/).count()) ||
            (await carousel.getByRole("link", { name: "Photo source" }).count())
          ) {
            throw new Error(
              "The page carousel must omit photo counts and credit/source lines.",
            );
          }
          if ((await carousel.getByRole("img").count()) !== 1) {
            throw new Error("The photo carousel must show exactly one image.");
          }
          await carousel.getByRole("button", { name: "Next photo" }).click();
          await carousel
            .getByRole("group", { name: "Photo 2 of 2", exact: true })
            .waitFor();
          await carousel
            .getByRole("button", { name: "Previous photo" })
            .click();
          await carousel
            .getByRole("group", { name: "Photo 1 of 2", exact: true })
            .waitFor();
          const image = await carousel.getByRole("img").boundingBox();
          const previous = await carousel
            .getByRole("button", { name: "Previous photo" })
            .boundingBox();
          const next = await carousel
            .getByRole("button", { name: "Next photo" })
            .boundingBox();
          if (
            !image ||
            !previous ||
            !next ||
            [previous, next].some(
              (control) =>
                Math.abs(
                  control.y + control.height / 2 - image.y - image.height / 2,
                ) > 1 ||
                control.x < image.x ||
                control.x + control.width > image.x + image.width,
            )
          ) {
            throw new Error(
              "Photo navigation must overlay the image at its vertical center.",
            );
          }
          const y = image.y + image.height / 2;
          if (width < 640) {
            const touch = await page.context().newCDPSession(page);
            try {
              await touch.send("Input.dispatchTouchEvent", {
                type: "touchStart",
                touchPoints: [{ x: image.x + image.width * 0.75, y }],
              });
              for (let step = 1; step <= 15; step++) {
                await touch.send("Input.dispatchTouchEvent", {
                  type: "touchMove",
                  touchPoints: [
                    {
                      x: image.x + image.width * (0.75 - step * (0.7 / 15)),
                      y,
                    },
                  ],
                });
              }
              await touch.send("Input.dispatchTouchEvent", {
                type: "touchEnd",
                touchPoints: [],
              });
            } finally {
              await touch.detach();
            }
          } else {
            await page.mouse.move(image.x + image.width * 0.75, y);
            await page.mouse.down();
            await page.mouse.move(image.x + image.width * 0.05, y, {
              steps: 15,
            });
            await page.mouse.up();
          }
          await carousel
            .getByRole("group", { name: "Photo 2 of 2", exact: true })
            .waitFor();
          if (await page.getByRole("dialog").count()) {
            throw new Error(
              "Dragging a photo must not open the full-screen viewer.",
            );
          }
          await carousel
            .getByRole("button", { name: "Previous photo" })
            .click();
          await carousel
            .getByRole("group", { name: "Photo 1 of 2", exact: true })
            .waitFor();
          // Paint the below-fold map before capturing the larger photo layout.
          await page.locator(".camply-map").scrollIntoViewIfNeeded();
          await page.evaluate(async () => {
            await new Promise(requestAnimationFrame);
            await new Promise(requestAnimationFrame);
          });
          await scrollToTop(page);
          if (
            await page.evaluate(
              () => document.documentElement.scrollWidth > innerWidth,
            )
          ) {
            const overflow = await page.evaluate(() =>
              Array.from(document.querySelectorAll("body *"))
                .filter(
                  (element) =>
                    element.getBoundingClientRect().right > innerWidth + 1,
                )
                .slice(0, 5)
                .map((element) => `${element.tagName}.${element.className}`),
            );
            throw new Error(
              `Destination enrichment overflows the viewport: ${overflow.join(", ")}`,
            );
          }
        },
      });
    }
  }
}
for (const [name, width, theme] of [
  ["desktop", 1440, "light"],
  ["mobile", 375, "dark"],
] as const) {
  SCENARIOS.push({
    name: `enrichment-dialog-${name}-${theme}`,
    route: "/campground/1/232447",
    viewport: { width, height: 1000 },
    theme,
    enrichment: true,
    description: `Destination photo dialog with caption and credit at ${width}px in ${theme} theme`,
    action: async (page) => {
      const trigger = page.getByRole("button", {
        name: "View Upper Pines Campground photo 1",
      });
      await trigger.click();
      await page.getByRole("dialog").waitFor();
      await page.keyboard.press("ArrowLeft");
      await page
        .getByRole("dialog")
        .getByText("Photo 2 of 2", { exact: true })
        .waitFor();
      await page.keyboard.press("Escape");
      await page.getByRole("dialog").waitFor({ state: "hidden" });
      await page.waitForFunction(
        (label) => document.activeElement?.getAttribute("aria-label") === label,
        "View Upper Pines Campground photo 2",
      );
      await page.keyboard.press("ArrowRight");
      await trigger.click();
    },
  });
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

for (const mobile of [false, true]) {
  SCENARIOS.push({
    name: mobile
      ? "scan-night-selection-mobile-dark"
      : "scan-night-selection-desktop-light",
    route: "/dashboard",
    viewport: mobile
      ? { width: 390, height: 844 }
      : { width: 1280, height: 800 },
    theme: mobile ? "dark" : "light",
    description: mobile
      ? "Keyboard selection adds Sunday to weekend nights in the mobile scan form"
      : "Recurring Friday and Saturday night selection leaves seasonal dates independent",
    action: async (page: Page) => {
      await page.getByRole("button", { name: "New Scan", exact: true }).click();
      const weekends = page.getByRole("button", {
        name: "Weekends",
        exact: true,
      });
      await weekends.focus();
      await page.keyboard.press("Enter");
      if (mobile) {
        await page.getByRole("button", { name: "Sunday", exact: true }).focus();
        await page.keyboard.press("Space");
      }
      for (const name of [
        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday",
        "Friday",
        "Saturday",
        "Sunday",
      ]) {
        const pressed = await page
          .getByRole("button", { name, exact: true })
          .getAttribute("aria-pressed");
        const selected =
          name === "Friday" ||
          name === "Saturday" ||
          (mobile && name === "Sunday");
        if (pressed !== String(selected))
          throw new Error(`Unexpected night selection: ${name}`);
      }
      const fits = await page
        .getByRole("group", { name: "Nights of the week" })
        .evaluate((element) => {
          const bounds = element.getBoundingClientRect();
          return bounds.left >= 0 && bounds.right <= window.innerWidth;
        });
      if (!fits) throw new Error("Night controls overflow the viewport");
    },
  });
}

const compactPhone = { width: 375, height: 667 };
const phone = { width: 390, height: 844 };

const desktopScenariosWithMobile = [
  ["auth", "light"],
  ["providers", "light"],
  ["how-it-works", "dark"],
  ["faq", "light"],
  ["ethos", "light"],
  ["home-search-dropdown", "light"],
  ["map-selected", "dark"],
  ["dashboard-empty", "light"],
  ["scan-form-dialog", "light", compactPhone],
  ["scan-form-checkin-calendar", "light", compactPhone],
  ["scan-form-checkout-calendar", "dark", compactPhone],
  ["scan-delete-error", "dark"],
  ["admin-users", "light"],
  ["admin-create-user-password", "dark"],
  ["admin-user-detail", "light"],
  ["admin-user-detail-reset-password", "dark"],
  ["admin-scans", "dark"],
  ["admin-scan-detail", "light"],
  ["admin-target-detail", "dark"],
  ["admin-audit", "light"],
  ["admin-api-trends-table", "dark"],
] as const;

for (const [name, theme, viewport = phone] of desktopScenariosWithMobile) {
  const desktop = SCENARIOS.find(({ name: source }) =>
    source.startsWith(`${name}-desktop-`),
  );
  if (!desktop) throw new Error(`Missing desktop snapshot for ${name}`);
  SCENARIOS.push({
    ...desktop,
    name: `${name}-mobile-${theme}`,
    viewport,
    theme,
    description: desktop.description.replace(/ \(Desktop, (Light|Dark)\)$/, ""),
  });
}

for (const [route, theme, description] of [
  ["/contact", "light", "Contact form"],
  ["/contribute", "dark", "Community contribution options"],
  ["/privacy", "light", "Privacy policy"],
  ["/terms", "dark", "Terms of service"],
  ["/admin/invitations", "light", "Invitation cards with review actions"],
] as const) {
  SCENARIOS.push({
    name: `${route.slice(1).replace("/", "-")}-mobile-${theme}`,
    route,
    viewport: phone,
    theme,
    description,
  });
}

SCENARIOS.push(
  {
    name: "mobile-nav-drawer-mobile-dark",
    route: "/",
    viewport: phone,
    theme: "dark",
    description: "Open mobile navigation drawer",
    action: async (page) => {
      const trigger = page.getByRole("button", { name: "Toggle mobile menu" });
      const drawer = page.getByRole("dialog", { name: "Navigation" });
      await trigger.click();
      await drawer.waitFor();
      await page.keyboard.press("Escape");
      await drawer.waitFor({ state: "hidden" });
      await trigger.click();
      await drawer.waitFor();
      await page.mouse.click(4, 44);
      await drawer.waitFor({ state: "hidden" });
      await trigger.click();
      await drawer.waitFor();
    },
  },
  {
    name: "profile-mobile-light",
    route: "/profile",
    viewport: phone,
    theme: "light",
    description: "Pushover settings and active sessions",
    action: async (page) => {
      await page.getByText("Active Sessions", { exact: true }).waitFor();
      await page.getByRole("button", { name: "Revoke" }).first().waitFor();
    },
  },
);

async function openTaskDetails(page: Page) {
  const details = page
    .getByRole("button", { name: "Details", exact: true })
    .first();
  await details.click();
  const dialog = page.getByRole("dialog", { name: "Task Execution Details" });
  await dialog.waitFor();
  return dialog;
}

SCENARIOS.push(
  {
    name: "auth-signup-mobile-dark",
    route: "/auth?mode=signup",
    viewport: phone,
    theme: "dark",
    authState: "signup",
    description: "App signup handoff to Auth0",
    action: async (page) => {
      const authorize = page.waitForRequest(
        "https://auth.snapshot.test/authorize?*",
      );
      await page
        .getByRole("button", { name: "Create Account", exact: true })
        .click();
      const request = await authorize;
      if (new URL(request.url()).searchParams.get("screen_hint") !== "signup") {
        throw new Error("Signup did not send the Auth0 signup hint");
      }
    },
  },
  {
    name: "auth-forced-password-mobile-light",
    route: "/dashboard",
    viewport: compactPhone,
    theme: "light",
    authState: "forced-password",
    emptyScans: true,
    description: "Required session password rotation and inline validation",
    action: async (page) => {
      await page
        .getByLabel("Current / Temporary Password")
        .fill("SyntheticCurrent!");
      await page
        .getByLabel("New Password", { exact: true })
        .fill("SyntheticNew!");
      await page.getByLabel("Confirm New Password").fill("SyntheticMismatch!");
      await page.getByRole("button", { name: "Update Password" }).click();
      await page.getByRole("alert").filter({ hasText: /match/i }).waitFor();
    },
  },
  {
    name: "admin-operations-task-detail-mobile-dark",
    route: "/admin/operations",
    viewport: compactPhone,
    theme: "dark",
    description: "Operations task details with pinned dismissal action",
    action: async (page) => {
      const dialog = await openTaskDetails(page);
      await dialog.getByRole("button", { name: "Done" }).click();
      await dialog.waitFor({ state: "hidden" });
      await openTaskDetails(page);
    },
  },
);

// Use a success-only landmark or fixture value, including on routes whose
// loading and error views repeat the page title.
const AUDIT_ROUTES = [
  ["/", "Find Campsites at Sold-Out Campgrounds"],
  ["/search?q=yosemite", "Upper Pines Campground", "text"],
  ["/providers", "Supported Providers"],
  ["/how-it-works", "How camply Works"],
  ["/faq", "Frequently Asked Questions"],
  ["/contact", "Get in Touch"],
  ["/ethos", "Making the Great Outdoors Accessible to All"],
  ["/contribute", "Contribute to camply"],
  ["/privacy", "Privacy Policy"],
  ["/terms", "Terms of Service"],
  ["/auth", "Sign In"],
  ["/invite-only", "Request Access", "button"],
  ["/dashboard", "Upper Pines Campground"],
  ["/dashboard/scans/scan-mock-1", "Found campsites"],
  ["/profile", "Notification provider", "combobox"],
  ["/campground/1/232447", "Upper Pines Campground"],
  ["/rec-area/1/2991", "Yosemite National Park"],
  ["/admin", "Shared Targets"],
  ["/admin/users", "camper@example.test", "text"],
  ["/admin/users/user-snap-2", "Account Profile & Status"],
  ["/admin/invitations", "hiker@example.test", "text"],
  ["/admin/scans", "Upper Pines Campground", "text"],
  ["/admin/scans/scan-mock-1", "Scan Configuration"],
  ["/admin/targets/target-mock-1", "Shared Availability Target"],
  ["/admin/operations", "celery@worker-1", "text"],
  ["/admin/audit", "admin@example.test", "text"],
] as const satisfies readonly (readonly [
  string,
  string,
  SnapshotReadyContent["role"]?,
])[];

const OVERFLOW_SWEEP: Scenario[] = AUDIT_ROUTES.flatMap(([route, name, role]) =>
  [{ width: 375, height: 812 }, phone, { width: 768, height: 1024 }].map(
    (viewport) => ({
      name: `overflow-${viewport.width}-${route === "/" ? "home" : route.slice(1)}`,
      route,
      viewport,
      theme: "light",
      description: `Document overflow check for ${route}`,
      overflowOnly: true,
      readyContent: { name, role },
    }),
  ),
);

async function assertViewportBounds(locator: Locator) {
  await locator.waitFor();
  const bounds = await locator.evaluate((element) => {
    const { top, left, bottom, right } = element.getBoundingClientRect();
    return { top, left, bottom, right, width: innerWidth, height: innerHeight };
  });
  if (
    bounds.top < -1 ||
    bounds.left < -1 ||
    bounds.right > bounds.width + 1 ||
    bounds.bottom > bounds.height + 1
  ) {
    throw new Error(
      `Element exceeds viewport bounds: ${JSON.stringify(bounds)}`,
    );
  }
}

async function assertPinnedDialog(dialog: Locator, requireScroll = false) {
  await assertViewportBounds(dialog);
  const header = dialog.locator("[data-dialog-header]");
  const footer = dialog.locator("[data-dialog-footer]");
  const close = dialog.getByRole("button", { name: "Close", exact: true });
  const body = dialog.locator("[data-dialog-body]");
  const initial = await Promise.all([
    header.boundingBox(),
    footer.boundingBox(),
    close.boundingBox(),
  ]);
  const scrollTop = await body.evaluate((element) => {
    if (element.scrollWidth > element.clientWidth) {
      throw new Error("Dialog body scrolls horizontally");
    }
    element.scrollTop = element.scrollHeight;
    return element.scrollTop;
  });
  if (requireScroll && scrollTop === 0)
    throw new Error("Expected the dialog body to scroll");
  const scrolled = await Promise.all([
    header.boundingBox(),
    footer.boundingBox(),
    close.boundingBox(),
  ]);
  if (
    initial.some(
      (box, index) =>
        !box || !scrolled[index] || Math.abs(box.y - scrolled[index].y) > 1,
    )
  ) {
    throw new Error(
      "Dialog header, footer, or close button moved while scrolling",
    );
  }
  for (const part of [header, footer, close]) await assertViewportBounds(part);
  await body.evaluate((element) => {
    element.scrollTop = 0;
  });
}

async function assertTouchTarget(button: Locator) {
  const box = await button.boundingBox();
  if (!box || box.width < 44 || box.height < 44)
    throw new Error("Expected a 44 × 44px touch target");
  await button.focus();
  if (
    !(await button.evaluate((element) => element.matches(":focus-visible")))
  ) {
    throw new Error("Expected a keyboard-visible focus state");
  }
}

const overlayChecks: Omit<Scenario, "viewport" | "theme">[] = [
  {
    name: "scan-calendars",
    route: "/dashboard",
    description: "Pinned scan actions and reachable calendars",
    action: async (page) => {
      await page.getByRole("button", { name: "New Scan", exact: true }).click();
      const dialog = page.getByRole("dialog", { name: "Create a New Scan" });
      await assertPinnedDialog(dialog, page.viewportSize()!.height === 667);
      for (const field of ["Check-in", "Check-out"]) {
        const trigger = dialog.getByLabel(field, { exact: true });
        await trigger.click();
        const calendar = dialog.getByRole("dialog", { name: "Choose a date" });
        const select = calendar.getByRole("combobox", { name: "Select month" });
        await select.click({ trial: true });
        await assertViewportBounds(select);
        const option = calendar
          .getByRole("button", { name: /^\d+$/ })
          .and(calendar.locator("button:enabled"))
          .first();
        await option.click({ trial: true });
        await assertViewportBounds(option);
        await page.keyboard.press("Escape");
        await calendar.waitFor({ state: "hidden" });
      }
      await dialog.getByRole("button", { name: "Cancel", exact: true }).click();
      await dialog.waitFor({ state: "hidden" });
    },
  },
  {
    name: "coverage",
    route: "/rec-area/1/2991",
    longValues: true,
    description: "Long destination title and area choices",
    action: async (page) => {
      await page
        .getByRole("button", { name: "Monitor recreation area" })
        .click();
      const dialog = page.getByRole("dialog", { name: "Create a New Scan" });
      await assertPinnedDialog(dialog);
      await dialog.getByLabel("Selected campgrounds").click();
      await dialog.getByRole("button", { name: "Select campgrounds…" }).click();
      const choice = dialog.getByRole("checkbox", {
        name: "Upper Pines Campground",
      });
      await choice.click();
      await assertViewportBounds(choice);
      await page.keyboard.press("Escape");
      await dialog
        .getByRole("button", { name: "Upper Pines Campground", exact: true })
        .waitFor();
    },
  },
  {
    name: "task-detail",
    route: "/admin/operations",
    longValues: true,
    description: "Pinned task details with long worker metadata",
    action: async (page) => {
      const dialog = await openTaskDetails(page);
      await assertPinnedDialog(dialog);
      await dialog.getByRole("button", { name: "Done" }).click();
      await dialog.waitFor({ state: "hidden" });
    },
  },
  {
    name: "admin-passwords",
    route: "/admin/users",
    description: "Pinned create and reset password actions",
    action: async (page) => {
      for (const [trigger, title] of [
        ["Create User", "Create User"],
        ["Reset password for camper@example.test", "Reset Password"],
      ]) {
        await page.getByRole("button", { name: trigger, exact: true }).click();
        const dialog = page.getByRole("dialog", { name: title, exact: true });
        await revealSnapshotPassword(page);
        await assertPinnedDialog(dialog);
        await dialog
          .getByRole("button", { name: "Copy password" })
          .click({ trial: true });
        await dialog.getByRole("button", { name: "Cancel" }).click();
        await dialog.waitFor({ state: "hidden" });
      }
    },
  },
  {
    name: "profile-long-values",
    route: "/profile",
    longValues: true,
    description: "Long notification and session values",
    action: async (page) => {
      const server = page.getByLabel("Your ntfy server URL");
      await server.scrollIntoViewIfNeeded();
      await assertViewportBounds(server);
      for (const field of [
        server,
        page.getByLabel("Your ntfy topic"),
        page.getByLabel("Access token (optional)"),
      ]) {
        if ((await field.inputValue()).length < 100)
          throw new Error("Expected a long notification fixture");
      }
      const device = page.getByTitle("SyntheticAgent".repeat(30), {
        exact: true,
      });
      await device.scrollIntoViewIfNeeded();
      await assertViewportBounds(device);
      for (const name of [
        "Copy ntfy server URL",
        "Copy ntfy topic",
        "Save notification settings",
        "Send test notification",
        "Revoke",
      ]) {
        const action = page.getByRole("button", { name, exact: true }).first();
        await action.scrollIntoViewIfNeeded();
        await assertViewportBounds(action);
      }
    },
  },
  {
    name: "header",
    route: "/",
    reducedMotion: true,
    description: "Touch targets and reduced-motion navigation",
    action: async (page) => {
      if (page.viewportSize()!.width >= 768) {
        await page
          .getByRole("navigation")
          .getByRole("link", { name: "Explore" })
          .waitFor();
        return;
      }
      await assertTouchTarget(
        page.getByRole("button", { name: "Close banner" }),
      );
      await page.getByRole("button", { name: "Toggle mobile menu" }).click();
      const drawer = page.getByRole("dialog", { name: "Navigation" });
      await assertViewportBounds(drawer);
      await page.keyboard.press("Escape");
      await drawer.waitFor({ state: "hidden" });
    },
  },
  {
    name: "results-controls",
    route: "/dashboard/scans/scan-mock-1",
    description: "Mobile sort and view control ergonomics",
    action: async (page) => {
      if (page.viewportSize()!.width >= 640) return;
      const sort = page.getByRole("combobox", { name: "Sort campsites" });
      if (
        (await sort.evaluate((element) =>
          parseFloat(getComputedStyle(element).fontSize),
        )) < 16
      ) {
        throw new Error("Campsite sort must use at least 16px type on phones");
      }
      for (const name of ["Cards", "Grid"])
        await assertTouchTarget(
          page.getByRole("button", { name, exact: true }),
        );
    },
  },
  {
    name: "reduced-dialogs",
    route: "/dashboard",
    reducedMotion: true,
    description: "Reduced-motion dialog and calendar transitions",
    action: async (page) => {
      await page.getByRole("button", { name: "New Scan", exact: true }).click();
      const dialog = page.getByRole("dialog", { name: "Create a New Scan" });
      await dialog.getByLabel("Check-in", { exact: true }).click();
      const calendar = dialog.getByRole("dialog", { name: "Choose a date" });
      for (const overlay of [dialog, calendar]) {
        if (
          (await overlay.evaluate(
            (element) => getComputedStyle(element).animationName,
          )) !== "none"
        ) {
          throw new Error("Dialog or date picker animated with reduced motion");
        }
      }
      await page.keyboard.press("Escape");
      await calendar.waitFor({ state: "hidden" });
      await page.keyboard.press("Escape");
      await dialog.waitFor({ state: "hidden" });
    },
  },
];

for (const [name, baselineName] of [
  ["photo-viewer", "enrichment-dialog-mobile-dark"],
  ["delete-error", "scan-delete-error-mobile-dark"],
  ["edit-scan", "scan-edit-dialog-mobile-dark"],
] as const) {
  const baseline = SCENARIOS.find((scenario) => scenario.name === baselineName);
  if (!baseline) throw new Error(`Missing snapshot for ${name}`);
  overlayChecks.push({
    ...baseline,
    name,
    action: async (page) => {
      await baseline.action?.(page);
      const dialog = page.getByRole("dialog");
      if (name === "edit-scan") await assertPinnedDialog(dialog);
      else await assertViewportBounds(dialog);
    },
  });
}

const OVERLAY_SWEEP: Scenario[] = overlayChecks.flatMap((scenario) =>
  [compactPhone, phone, { width: 768, height: 1024 }].flatMap((viewport) =>
    (["light", "dark"] as const).map((theme) => ({
      ...scenario,
      name: `overlay-${scenario.name}-${viewport.width}-${theme}`,
      viewport,
      theme,
      overflowOnly: true,
    })),
  ),
);

const compactScan = overlayChecks.find(
  ({ name }) => name === "scan-calendars",
)!;
OVERLAY_SWEEP.push({
  ...compactScan,
  name: "overlay-scan-calendars-360-light",
  viewport: { width: 360, height: 667 },
  theme: "light",
  overflowOnly: true,
});

for (const viewport of [compactPhone, phone]) {
  OVERLAY_SWEEP.push({
    name: `overlay-home-autocomplete-${viewport.width}`,
    route: "/",
    viewport,
    theme: viewport.width === 375 ? "light" : "dark",
    description:
      "Home suggestions stay visible and tappable with long result text",
    overflowOnly: true,
    longValues: true,
    reducedMotion: true,
    touch: true,
    action: async (page) => {
      const input = page.getByPlaceholder("Search campgrounds...");
      const panel = page.locator("[data-search-suggestions]");
      await input.fill("Yosemite".repeat(24));
      const first = panel.getByText("Synthetic Camp 1", { exact: true });
      const last = panel.getByText("Synthetic Camp 8", { exact: true });
      await first.waitFor();
      // Put the search field near the bottom of the visible viewport.
      await input.evaluate((element) => {
        const bottom = element.getBoundingClientRect().bottom;
        window.scrollBy(0, bottom - (innerHeight - 24));
      });
      await assertViewportBounds(panel);
      const anchorBounds = (await input.boundingBox())!;
      const panelBounds = (await panel.boundingBox())!;
      if (panelBounds.y + panelBounds.height > anchorBounds.y) {
        throw new Error("Autocomplete did not flip above the search field");
      }
      await panel.evaluate((element) => {
        const original = element.scrollTo.bind(element);
        element.scrollTo = (options?: number | ScrollToOptions, y?: number) => {
          if (typeof options === "number") {
            original(options, y ?? 0);
          } else {
            element.setAttribute(
              "data-scroll-behavior",
              options?.behavior ?? "",
            );
            original(options);
          }
        };
      });
      // ArrowUp wraps from the unselected input to the last result.
      await input.press("ArrowUp");
      await page.waitForFunction(
        () => {
          const panel = document.querySelector("[data-search-suggestions]");
          return panel?.getAttribute("data-scroll-behavior") === "instant";
        },
        undefined,
        { timeout: 3000 },
      );
      const styles = await panel.evaluate((element) => {
        const style = getComputedStyle(element);
        return {
          overflow: element.scrollWidth - element.clientWidth,
          duration: style.transitionDuration,
          transform: style.transform,
        };
      });
      if (
        styles.overflow > 1 ||
        styles.duration !== "0s" ||
        styles.transform !== "none"
      ) {
        throw new Error(
          `Autocomplete overflows or animates with reduced motion: ${JSON.stringify(styles)}`,
        );
      }
      const visible = await last.evaluate((element) => {
        const panel = element
          .closest("[data-search-suggestions]")!
          .getBoundingClientRect();
        const row = element.getBoundingClientRect();
        return row.top >= panel.top && row.bottom <= panel.bottom;
      });
      if (!visible) throw new Error("Keyboard-selected result is clipped");
      await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
      await panel.waitFor({ state: "hidden" });
      await input.scrollIntoViewIfNeeded();
      await assertViewportBounds(panel);
      await last.tap();
      await page.waitForURL("**/campground/1/232447");
      await page.goBack();
    },
  });
}

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

const MOCK_AREA_SCANS = [
  {
    id: "area-scan-mock-1",
    provider_id: 1,
    destination_type: "recreation_area",
    destination_name: "Yosemite National Park",
    campground_id: null,
    campground_name: null,
    recreation_area_id: "2991",
    recreation_area_name: "Yosemite National Park",
    coverage_mode: "selected",
    campground_ids: ["232447", "232499"],
    destination_available: true,
    eligible_campground_count: 1,
    unavailable_selection_count: 1,
    matching_campground_count: 1,
    checked_campground_count: 1,
    pending_campground_count: 0,
    failed_campground_count: 1,
    coverage_status: "partial",
    row_version: 2,
    start_date: "2026-11-15",
    end_date: "2026-11-19",
    is_active: true,
    min_stay_length: 2,
    preferred_types: ["TENT ONLY"],
    require_electric: false,
    last_checked_at: "2026-10-10T11:59:40Z",
    found_count: 2,
    created_at: "2026-06-15T08:00:00Z",
  },
  {
    id: "area-scan-mock-2",
    provider_id: 1,
    destination_type: "recreation_area",
    destination_name: "Sequoia National Park",
    campground_id: null,
    campground_name: null,
    recreation_area_id: "2992",
    recreation_area_name: "Sequoia National Park",
    coverage_mode: "all",
    campground_ids: [],
    destination_available: true,
    eligible_campground_count: 6,
    unavailable_selection_count: 0,
    matching_campground_count: 2,
    checked_campground_count: 6,
    pending_campground_count: 0,
    failed_campground_count: 0,
    coverage_status: "complete",
    row_version: 1,
    start_date: "2026-12-01",
    end_date: "2026-12-05",
    is_active: true,
    min_stay_length: 1,
    preferred_types: [],
    require_electric: false,
    last_checked_at: "2026-10-10T12:00:00Z",
    found_count: 4,
    created_at: "2026-06-20T10:00:00Z",
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
      let body = "";
      res.on("data", (chunk) => {
        body += chunk;
      });
      res.on("end", () => {
        resolve(
          res.statusCode === 200 &&
            (body.includes("camply") || body.includes('<div id="root">')),
        );
      });
    });
    req.on("error", () => resolve(false));
    req.setTimeout(1000, () => {
      req.destroy();
      resolve(false);
    });
  });
}

/**
 * Terminate the spawned Vite development server and all processes in its process group.
 *
 * Parameters
 * ----------
 * serverProcess : ChildProcess
 *     The child process reference returned by ensureServerRunning.
 */
function stopServer(serverProcess: ChildProcess): void {
  if (!serverProcess || serverProcess.pid === undefined) return;
  console.log("🛑 Stopping spawned Vite dev server...");
  const pid = serverProcess.pid;
  try {
    if (process.platform === "win32") {
      execSync(`taskkill /pid ${pid} /T /F`, { stdio: "ignore" });
    } else {
      try {
        process.kill(-pid, "SIGTERM");
      } catch {
        try {
          process.kill(pid, "SIGTERM");
        } catch {
          // Process already terminated.
        }
      }
    }
  } catch {
    // Process already terminated.
  }
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
  const isWin = process.platform === "win32";
  const executable = isWin ? "pnpm.cmd" : "pnpm";
  const serverProcess = spawn(
    executable,
    ["run", "dev", "--port", `${PORT}`, "--strictPort", "--base", "/"],
    {
      cwd: FRONTEND_ROOT,
      stdio: "ignore",
      detached: !isWin,
      env: {
        ...process.env,
        GITHUB_REPOSITORY: "",
        // Keep visual coverage of the optional community pages and navigation.
        VITE_ENABLE_COMMUNITY_PAGES: "true",
      },
    },
  );
  serverProcess.unref();

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
    stopServer(serverProcess);
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
  if (scenario.enrichment) {
    const image = new PNG({ width: 640, height: 480 });
    for (let index = 0; index < image.data.length; index += 4) {
      const y = Math.floor(index / 4 / 640);
      image.data[index] = y < 250 ? 170 : 45;
      image.data[index + 1] = y < 250 ? 205 : 95;
      image.data[index + 2] = y < 250 ? 220 : 70;
      image.data[index + 3] = 255;
    }
    await page.route("https://images.example.test/**", (route) =>
      route.fulfill({ contentType: "image/png", body: PNG.sync.write(image) }),
    );
  }
  const invitationRequired =
    scenario.name.startsWith("early-access-") ||
    scenario.route === "/invite-only";
  const signedOut = scenario.route.split("?")[0] === "/auth";
  const signup = scenario.authState === "signup";
  if (signup) {
    await page.route("https://auth.snapshot.test/authorize?*", (route) =>
      route.fulfill({ status: 204 }),
    );
  }
  await page.route("**/api/auth-config", (route) => {
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        auth_mode: signup ? "auth0" : "session",
        auth0_audience: signup ? "https://api.snapshot.test" : null,
        auto_login: false,
        signup_enabled: signup,
        invite_only: invitationRequired,
        auth0_domain: signup ? "auth.snapshot.test" : null,
        auth0_client_id: signup ? "synthetic-snapshot-client" : null,
      }),
    });
  });

  await page.route("**/api/me", (route) => {
    route.fulfill({
      status: signedOut ? 401 : 200,
      contentType: "application/json",
      body: JSON.stringify({
        ...MOCK_USER,
        ...(scenario.longValues
          ? {
              email: `${"synthetic".repeat(24)}@example.test`,
              notification_provider: "ntfy",
              ntfy_server_url: `https://ntfy.example.test/${"server".repeat(32)}`,
              ntfy_topic: "topic".repeat(30),
              ntfy_access_token: "token".repeat(45),
            }
          : {}),
        must_change_password: scenario.authState === "forced-password",
        is_invited: !invitationRequired,
        is_admin: scenario.route.startsWith("/admin"),
        invitation_status: null,
      }),
    });
  });

  await page.route("**/api/me/sessions", (route) => {
    route.fulfill({
      status: signedOut ? 401 : 200,
      contentType: "application/json",
      body: JSON.stringify({
        items: signedOut
          ? []
          : [
              {
                id: "session-snap-1",
                user_agent: scenario.longValues
                  ? "SyntheticAgent".repeat(30)
                  : "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/131.0.0.0 Safari/537.36",
                ip_address: "198.51.100.42",
                created_at: "2026-10-10T11:30:00Z",
                expires_at: "2026-10-10T23:30:00Z",
                is_current: true,
              },
              {
                id: "session-snap-2",
                user_agent:
                  "Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 Mobile/15E148 Safari/604.1",
                ip_address: "203.0.113.19",
                created_at: "2026-10-10T09:15:00Z",
                expires_at: "2026-10-10T21:15:00Z",
                is_current: false,
              },
            ],
      }),
    });
  });

  await page.route("**/api/me/sessions/*", (route) => {
    route.fulfill({ status: 204 });
  });

  await page.route("**/api/scans", (route) => {
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        scans: scenario.emptyScans
          ? []
          : scenario.areaScans
            ? MOCK_AREA_SCANS
            : MOCK_SCANS,
        total: scenario.emptyScans
          ? 0
          : scenario.areaScans
            ? MOCK_AREA_SCANS.length
            : MOCK_SCANS.length,
      }),
    });
  });

  await page.route("**/api/scans/area-scan-mock-1", (route) => {
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        ...MOCK_AREA_SCANS[0],
        campgrounds: [
          {
            provider_id: 1,
            campground_id: "232447",
            campground_name: "Upper Pines Campground",
            eligible: true,
            outcome: "success",
            target_id: "target-mock-1",
          },
          {
            provider_id: 1,
            campground_id: "232499",
            campground_name: "Closed Basin Campground",
            eligible: false,
            outcome: "failed",
            unavailable_reason:
              "Campground is no longer eligible in this recreation area",
          },
        ],
        results: [
          {
            provider_id: 1,
            campground_id: "232447",
            campground_name: "Upper Pines Campground",
            is_stale: true,
            campsite_id: "site-401",
            campsite_name: "Upper Pines Site 042",
            campsite_type: "TENT ONLY",
            is_electric: false,
            is_accessible: true,
            booking_url:
              "https://www.recreation.gov/camping/campgrounds/232447",
            available_dates: ["2026-11-15", "2026-11-16"],
          },
          {
            provider_id: 1,
            campground_id: "232447",
            campground_name: "Upper Pines Campground",
            is_stale: true,
            campsite_id: "site-402",
            campsite_name: "Upper Pines Site 048",
            campsite_type: "TENT ONLY",
            is_electric: false,
            is_accessible: false,
            booking_url:
              "https://www.recreation.gov/camping/campgrounds/232447",
            available_dates: ["2026-11-15", "2026-11-16", "2026-11-17"],
          },
        ],
      }),
    });
  });

  await page.route("**/api/scans/scan-mock-1", (route) => {
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        ...MOCK_SCANS[0],
        found_count: scenario.manyCampsites ? 13 : 3,
        start_date: "2026-11-15",
        end_date: "2026-11-21",
        last_checked_at: "2026-10-10T11:59:40Z",
        preferred_types: [],
        results: [
          {
            campsite_id: "site-401",
            campsite_name: "Upper Pines Site 042",
            campsite_type: "RV",
            is_electric: true,
            is_accessible: true,
            booking_url:
              "https://www.recreation.gov/camping/campgrounds/232447",
            available_dates: [
              "2026-11-15",
              "2026-11-16",
              "2026-11-19",
              "2026-11-20",
            ],
          },
          {
            campsite_id: "site-402",
            campsite_name: "Upper Pines Site 048",
            campsite_type: "TENT",
            is_electric: false,
            is_accessible: false,
            booking_url:
              "https://www.recreation.gov/camping/campgrounds/232447",
            available_dates: ["2026-11-17", "2026-11-18"],
          },
          {
            campsite_id: "site-403",
            campsite_name: "Upper Pines Site 063",
            campsite_type: "TENT",
            is_electric: false,
            is_accessible: false,
            booking_url:
              "https://www.recreation.gov/camping/campgrounds/232447",
            available_dates: [
              "2026-11-15",
              "2026-11-16",
              "2026-11-19",
              "2026-11-20",
            ],
          },
          ...(scenario.manyCampsites
            ? Array.from({ length: 10 }, (_, index) => ({
                campsite_id: `site-extra-${index}`,
                campsite_name: `Upper Pines Site ${String(50 + index).padStart(3, "0")}`,
                campsite_type: "TENT",
                is_electric: false,
                is_accessible: false,
                booking_url:
                  "https://www.recreation.gov/camping/campgrounds/232447",
                available_dates: ["2026-11-15", "2026-11-16"],
              }))
            : []),
        ],
      }),
    });
  });

  await page.route("**/api/search/explore*", (route) => {
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        items: MOCK_SEARCH_RESULTS,
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
        body: JSON.stringify(
          scenario.longValues && scenario.route === "/"
            ? Array.from({ length: 8 }, (_, index) => ({
                ...MOCK_SEARCH_ITEMS[0],
                id: `synthetic-search-${index}`,
                campground_name: `Synthetic Camp ${index + 1}`,
                provider_name: "LongProvider".repeat(15),
                recreation_area_name: "LongLocation".repeat(15),
              }))
            : MOCK_SEARCH_ITEMS,
        ),
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
        items: MOCK_SEARCH_RESULTS,
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
      body: JSON.stringify({
        ...MOCK_CAMPGROUNDS[0],
        ...(scenario.enrichment ? { details: destinationDetails() } : {}),
      }),
    }),
  );
  await page.route("**/api/rec-area/1/2991", (route) =>
    route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        id: "2991",
        provider_id: 1,
        name: scenario.longValues
          ? "Destination" + "Synthetic".repeat(18)
          : "Yosemite National Park",
        description: "Synthetic recreation area for map verification.",
        latitude: 37.74,
        longitude: -119.58,
        state: "CA",
        country: "US",
        reservable: true,
        enabled: true,
        url: "https://example.test",
        ...(scenario.enrichment ? { details: destinationDetails() } : {}),
      }),
    }),
  );
  await page.route("**/api/rec-area/1/2991/campgrounds", (route) =>
    route.fulfill({
      contentType: "application/json",
      body: JSON.stringify(MOCK_CAMPGROUNDS),
    }),
  );
  await page.route("**/api/rec-area/1/2991/monitoring-campgrounds*", (route) =>
    route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        items: MOCK_CAMPGROUNDS.map((item) => ({
          id: item.id,
          provider_id: item.provider_id,
          recreation_area_id: item.recreation_area_id,
          name: item.name,
          state: item.state,
          city: "Yosemite Valley",
        })),
        total: MOCK_CAMPGROUNDS.length,
        eligible_total: MOCK_CAMPGROUNDS.length,
        limit: 50,
        offset: 0,
        has_more: false,
        catalog_revision: 1,
      }),
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
    reducedMotion:
      scenario.reducedMotion ||
      scenario.enrichment ||
      scenario.route.startsWith("/admin")
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

  await navigateToSnapshot(
    page,
    `${BASE_URL}${scenario.route}`,
    scenario.name.startsWith("map-error"),
  );
  if (scenario.readyContent) {
    await waitForSnapshotContent(page, scenario.readyContent);
  }

  // Enforce zero CSS animations and transitions for pixel stability
  if (!scenario.reducedMotion)
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

  if (scenario.route === "/dashboard" && !scenario.emptyScans) {
    try {
      await page.waitForSelector("text=Upper Pines Campground", {
        timeout: 4000,
      });
    } catch {
      // Continue if selector is not found within timeout
    }
  }

  await page.waitForFunction(
    () => document.querySelectorAll(".animate-spin").length === 0,
    { timeout: 10000 },
  );

  if (scenario.route.startsWith("/dashboard/scans/")) {
    try {
      await page.waitForSelector("text=View campground on provider", {
        timeout: 4000,
      });
    } catch {
      // Continue if selector is not found within timeout
    }
  }

  // Settle time for layout rendering
  await page.waitForTimeout(200);

  if (scenario.action) {
    await scenario.action(page);
  }
  if (scenario.name.startsWith("map-")) {
    // Foreground the page before scrolling back to the map so Chromium paints
    // the WebGL canvas even when other snapshot workers have opened tabs.
    await page.bringToFront();
    await page.evaluate(() => window.scrollTo(0, 0));
  }
  await waitForSnapshotAssets(page);

  if (scenario.overflowOnly) {
    const expectedPath = new URL(scenario.route, BASE_URL).pathname;
    const actualPath = new URL(page.url()).pathname;
    if (actualPath !== expectedPath) {
      throw new Error(`Expected ${expectedPath}, landed on ${actualPath}`);
    }
  }

  if (scenario.viewport.width <= 768) {
    const overflow = await page.evaluate(
      () => document.documentElement.scrollWidth - window.innerWidth,
    );
    if (overflow > 0) {
      throw new Error(`Document overflows the viewport by ${overflow}px`);
    }
  }
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
        { createBaseline: false, baselinesDir: BASELINES_DIR },
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

  const filterArg =
    args.find((a) => a.startsWith("--filter="))?.slice(9) ||
    (args.includes("--filter")
      ? args[args.indexOf("--filter") + 1]
      : undefined) ||
    (args.includes("-f") ? args[args.indexOf("-f") + 1] : undefined);

  const candidates = args.includes("--overlay-only")
    ? OVERLAY_SWEEP
    : args.includes("--overflow-only")
      ? OVERFLOW_SWEEP
      : filterArg
        ? SCENARIOS
        : [...SCENARIOS, ...OVERFLOW_SWEEP, ...OVERLAY_SWEEP];
  const scenariosToRun = filterArg
    ? candidates.filter(
        (s) => s.name.includes(filterArg) || s.route.includes(filterArg),
      )
    : candidates;

  if (scenariosToRun.length === 0) {
    console.error(`❌ No scenarios matched filter: "${filterArg}"`);
    process.exit(1);
  }

  // Ensure directories exist
  [SNAPSHOTS_DIR, BASELINES_DIR, CURRENT_DIR, DIFFS_DIR].forEach((dir) => {
    if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
  });

  const serverProcess = await ensureServerRunning();
  let browser: Browser | null = null;
  let hasRegressions = false;

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

    const defaultConcurrency = Math.max(1, Math.min(os.cpus()?.length || 4, 4));
    const concurrency = Math.max(
      1,
      Number(process.env.CAMPLY_SNAPSHOT_CONCURRENCY) || defaultConcurrency,
    );

    const captures: (SnapshotResult | undefined)[] = new Array(
      scenariosToRun.length,
    );
    const failures: string[] = [];
    console.log(
      `\n📸 Capturing and analyzing ${scenariosToRun.length} UI snapshot views (concurrency: ${concurrency})...\n`,
    );

    let nextIndex = 0;
    const workerPromises = Array.from(
      { length: Math.min(concurrency, scenariosToRun.length) },
      async () => {
        const contextOptions = {
          timezoneId: "UTC",
          locale: "en-US",
          deviceScaleFactor: 1,
        };
        const context = await browser!.newContext(contextOptions);
        try {
          while (true) {
            const index = nextIndex++;
            if (index >= scenariosToRun.length) break;
            const scenario = scenariosToRun[index];
            const prefix = `[${index + 1}/${scenariosToRun.length}]`;
            const page = scenario.touch
              ? await browser!.newPage({ ...contextOptions, hasTouch: true })
              : await context.newPage();
            try {
              await preparePage(page, scenario);
              if (scenario.overflowOnly) {
                console.log(`  ${prefix} ${scenario.name}: fits viewport`);
                continue;
              }
              // Fixed overlays belong to the visible viewport, especially after
              // clicking a trigger below the fold scrolls the page.
              const fullPage =
                scenario.viewport.width > 768 ||
                (await page.getByRole("dialog").count()) === 0;
              const screenshotBuf = await page.screenshot({ fullPage });
              const result = recordSnapshot(
                SNAPSHOTS_DIR,
                {
                  name: scenario.name,
                  description: scenario.description,
                  viewport: `${scenario.viewport.width}x${scenario.viewport.height}`,
                  theme: scenario.theme,
                },
                screenshotBuf,
                {
                  update: isUpdate,
                  createBaseline: !isCheck,
                  baselinesDir: BASELINES_DIR,
                },
              );
              captures[index] = result;
              const statusLabel = isUpdate
                ? `🔄 UPDATED (${result.status.toLowerCase()})`
                : result.status === "MODIFIED"
                  ? `⚠️ MODIFIED (${result.diffPercentage.toFixed(2)}% diff)`
                  : result.status === "NEW"
                    ? "🆕 NEW BASELINE"
                    : "✅ MATCH";
              console.log(`  ${prefix} ${scenario.name}: ${statusLabel}`);
            } catch (error) {
              const failure = `${scenario.name}: ${error instanceof Error ? error.message : String(error)}`;
              failures.push(failure);
              console.error(`  ${prefix} ${failure}`);
            } finally {
              await page.close();
            }
          }
        } finally {
          await context.close();
        }
      },
    );

    await Promise.all(workerPromises);

    const results = captures.filter((result) => result !== undefined);
    if (results.length) writeReports(results);
    if (failures.length) {
      throw new Error(
        `${failures.length} scenario(s) failed:\n${failures.join("\n")}`,
      );
    }
    if (results.length === 0) return;

    const modifiedViews = results.filter((r) => r.status === "MODIFIED");
    const newViews = results.filter((result) => result.status === "NEW");
    if (isCheck && newViews.length) {
      console.error(
        `Missing baselines: ${newViews.map(({ name }) => name).join(", ")}`,
      );
      hasRegressions = true;
    }
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
        hasRegressions = true;
      }
    } else {
      console.log("🎉 All snapshots match baselines perfectly!");
    }
  } finally {
    if (browser) await browser.close();
    if (serverProcess) {
      stopServer(serverProcess);
    }
  }

  if (hasRegressions) {
    console.error("\n❌ Visual regression check failed in --check mode.");
    process.exit(1);
  }
}

main()
  .then(() => {
    process.exit(0);
  })
  .catch((err) => {
    console.error("Fatal error during snapshot execution:", err);
    process.exit(1);
  });
