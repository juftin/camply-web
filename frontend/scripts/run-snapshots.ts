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
import pixelmatch from "pixelmatch";
import { PNG } from "pngjs";
import { setupAdminSnapshotMocks } from "./admin-snapshot-mocks";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const FRONTEND_ROOT = path.resolve(__dirname, "..");
const SNAPSHOTS_DIR = path.resolve(FRONTEND_ROOT, "snapshots");
const BASELINES_DIR = path.resolve(SNAPSHOTS_DIR, "baselines");
const CURRENT_DIR = path.resolve(SNAPSHOTS_DIR, "current");
const DIFFS_DIR = path.resolve(SNAPSHOTS_DIR, "diffs");
const REPORT_MD_PATH = path.resolve(SNAPSHOTS_DIR, "REPORT.md");
const REPORT_HTML_PATH = path.resolve(SNAPSHOTS_DIR, "report.html");

const PORT = 5173;
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
  action?: (page: Page) => Promise<void>;
}

/**
 * Snapshot comparison outcome.
 */
interface SnapshotResult {
  name: string;
  description: string;
  viewport: string;
  theme: "light" | "dark";
  status: "UNCHANGED" | "MODIFIED" | "NEW";
  diffPixels: number;
  diffPercentage: number;
  baselinePath: string | null;
  currentPath: string;
  diffPath: string | null;
}

/**
 * Standard scenarios covering pages, themes, viewports, and components.
 */
const SCENARIOS: Scenario[] = [
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
];

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
    "npm",
    ["run", "dev", "--", "--port", `${PORT}`],
    {
      cwd: FRONTEND_ROOT,
      stdio: "pipe",
      shell: true,
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
  await setupAdminSnapshotMocks(page);
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

  await page.route("**/api/search**", (route) => {
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        campgrounds: MOCK_CAMPGROUNDS,
        total: MOCK_CAMPGROUNDS.length,
      }),
    });
  });

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

  // Settle time for layout rendering
  await page.waitForTimeout(200);

  if (scenario.action) {
    await scenario.action(page);
  }
}

/**
 * Compare two PNG buffers using pixelmatch.
 *
 * Parameters
 * ----------
 * currentBuf : Buffer
 *     Current screenshot buffer.
 * baselineBuf : Buffer
 *     Baseline screenshot buffer.
 *
 * Returns
 * -------
 * { diffPixels: number, diffPercentage: number, diffPng: PNG | null }
 *     Comparison metrics and optional diff image.
 */
function compareImages(
  currentBuf: Buffer,
  baselineBuf: Buffer,
): { diffPixels: number; diffPercentage: number; diffPng: PNG | null } {
  const currentImg = PNG.sync.read(currentBuf);
  const baselineImg = PNG.sync.read(baselineBuf);

  const width = Math.max(currentImg.width, baselineImg.width);
  const height = Math.max(currentImg.height, baselineImg.height);

  const diffPng = new PNG({ width, height });

  // Normalize image sizes if necessary
  const normalizedCurrent = normalizeImage(currentImg, width, height);
  const normalizedBaseline = normalizeImage(baselineImg, width, height);

  const totalPixels = width * height;
  const diffPixels = pixelmatch(
    normalizedCurrent.data,
    normalizedBaseline.data,
    diffPng.data,
    width,
    height,
    { threshold: 0.1, alpha: 0.5, diffColor: [255, 0, 80] },
  );

  const diffPercentage = (diffPixels / totalPixels) * 100;
  return { diffPixels, diffPercentage, diffPng };
}

/**
 * Helper to normalize image bounds by padding transparent pixels if dimensions differ.
 */
function normalizeImage(src: PNG, width: number, height: number): PNG {
  if (src.width === width && src.height === height) return src;
  const target = new PNG({ width, height });
  PNG.bitblt(src, target, 0, 0, src.width, src.height, 0, 0);
  return target;
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

/**
 * Generate self-contained HTML visual comparison report.
 *
 * Parameters
 * ----------
 * results : SnapshotResult[]
 *     Array of test outcomes.
 *
 * Returns
 * -------
 * string
 *     HTML document string.
 */
function generateHtmlReport(results: SnapshotResult[]): string {
  const modified = results.filter((r) => r.status === "MODIFIED").length;
  const unchanged = results.filter((r) => r.status === "UNCHANGED").length;

  return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Camply UI Snapshot Report</title>
  <style>
    :root {
      --bg: #090d16;
      --card-bg: #131a29;
      --text: #f1f5f9;
      --text-muted: #94a3b8;
      --border: #1e293b;
      --accent: #10b981;
      --warn: #f59e0b;
      --danger: #ef4444;
    }
    body {
      margin: 0;
      padding: 2rem;
      background: var(--bg);
      color: var(--text);
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    }
    .header {
      border-bottom: 1px solid var(--border);
      padding-bottom: 1.5rem;
      margin-bottom: 2rem;
    }
    .stats {
      display: flex;
      gap: 1.5rem;
      margin-top: 1rem;
    }
    .stat-badge {
      padding: 0.5rem 1rem;
      border-radius: 8px;
      font-weight: 600;
      font-size: 0.875rem;
      background: var(--card-bg);
      border: 1px solid var(--border);
    }
    .grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(420px, 1fr));
      gap: 1.5rem;
    }
    .card {
      background: var(--card-bg);
      border: 1px solid var(--border);
      border-radius: 12px;
      overflow: hidden;
      display: flex;
      flex-direction: column;
    }
    .card-header {
      padding: 1rem;
      border-bottom: 1px solid var(--border);
      display: flex;
      justify-content: space-between;
      align-items: center;
    }
    .card-title {
      font-size: 0.95rem;
      font-weight: 600;
      font-family: monospace;
    }
    .card-body {
      padding: 1rem;
      flex: 1;
      display: flex;
      flex-direction: column;
      gap: 0.75rem;
    }
    .img-container {
      width: 100%;
      background: #000;
      border-radius: 6px;
      overflow: hidden;
      border: 1px solid var(--border);
    }
    .img-container img {
      width: 100%;
      height: auto;
      display: block;
    }
    .status-tag {
      padding: 0.25rem 0.5rem;
      border-radius: 4px;
      font-size: 0.75rem;
      font-weight: 600;
    }
    .status-unchanged { background: rgba(16, 185, 129, 0.2); color: var(--accent); }
    .status-modified { background: rgba(245, 158, 11, 0.2); color: var(--warn); }
    .status-new { background: rgba(59, 130, 246, 0.2); color: #60a5fa; }
  </style>
</head>
<body>
  <div class="header">
    <h1>🏕️ Camply UI Snapshot Gallery</h1>
    <div class="stats">
      <div class="stat-badge">Total Views: ${results.length}</div>
      <div class="stat-badge" style="color: var(--accent)">✅ Unchanged: ${unchanged}</div>
      <div class="stat-badge" style="color: var(--warn)">⚠️ Modified: ${modified}</div>
    </div>
  </div>
  <div class="grid">
    ${results
      .map(
        (r) => `
      <div class="card">
        <div class="card-header">
          <span class="card-title">${r.name}</span>
          <span class="status-tag status-${r.status.toLowerCase()}">${r.status} ${
            r.status === "MODIFIED" ? `(${r.diffPercentage.toFixed(2)}%)` : ""
          }</span>
        </div>
        <div class="card-body">
          <p style="margin:0; font-size:0.8rem; color:var(--text-muted);">${r.description}</p>
          <div class="img-container">
            <img src="${r.diffPath ? path.relative(SNAPSHOTS_DIR, r.diffPath) : path.relative(SNAPSHOTS_DIR, r.currentPath)}" alt="${r.name}" />
          </div>
        </div>
      </div>
    `,
      )
      .join("")}
  </div>
</body>
</html>`;
}

/**
 * Main snapshot execution entrypoint.
 */
async function main(): Promise<void> {
  const args = process.argv.slice(2);
  const isUpdate = args.includes("--update");
  const isCheck = args.includes("--check");

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
      ],
    });

    const context = await browser.newContext({ timezoneId: "UTC" });
    const page = await context.newPage();

    const results: SnapshotResult[] = [];
    console.log(
      `\n📸 Capturing and analyzing ${SCENARIOS.length} UI snapshot views...\n`,
    );

    for (const scenario of SCENARIOS) {
      process.stdout.write(`  ⏳ Capturing [${scenario.name}]... `);
      await preparePage(page, scenario);

      const currentPath = path.join(CURRENT_DIR, `${scenario.name}.png`);
      const baselinePath = path.join(BASELINES_DIR, `${scenario.name}.png`);
      const diffPath = path.join(DIFFS_DIR, `${scenario.name}-diff.png`);

      const screenshotBuf = await page.screenshot({ fullPage: true });
      fs.writeFileSync(currentPath, screenshotBuf);

      const baselineExists = fs.existsSync(baselinePath);

      if (!baselineExists || isUpdate) {
        fs.writeFileSync(baselinePath, screenshotBuf);
        if (fs.existsSync(diffPath)) fs.unlinkSync(diffPath);

        results.push({
          name: scenario.name,
          description: scenario.description,
          viewport: `${scenario.viewport.width}x${scenario.viewport.height}`,
          theme: scenario.theme,
          status: baselineExists && isUpdate ? "UNCHANGED" : "NEW",
          diffPixels: 0,
          diffPercentage: 0,
          baselinePath,
          currentPath,
          diffPath: null,
        });

        console.log(
          baselineExists && isUpdate ? "🔄 UPDATED" : "🆕 NEW BASELINE",
        );
      } else {
        const baselineBuf = fs.readFileSync(baselinePath);
        const { diffPixels, diffPercentage, diffPng } = compareImages(
          screenshotBuf,
          baselineBuf,
        );

        if (diffPercentage > 0.05 && diffPixels > 10) {
          if (diffPng) {
            fs.writeFileSync(diffPath, PNG.sync.write(diffPng));
          }
          results.push({
            name: scenario.name,
            description: scenario.description,
            viewport: `${scenario.viewport.width}x${scenario.viewport.height}`,
            theme: scenario.theme,
            status: "MODIFIED",
            diffPixels,
            diffPercentage,
            baselinePath,
            currentPath,
            diffPath,
          });
          console.log(`⚠️ MODIFIED (${diffPercentage.toFixed(2)}% diff)`);
        } else {
          if (fs.existsSync(diffPath)) fs.unlinkSync(diffPath);
          results.push({
            name: scenario.name,
            description: scenario.description,
            viewport: `${scenario.viewport.width}x${scenario.viewport.height}`,
            theme: scenario.theme,
            status: "UNCHANGED",
            diffPixels: 0,
            diffPercentage: 0,
            baselinePath,
            currentPath,
            diffPath: null,
          });
          console.log("✅ MATCH");
        }
      }
    }

    // Write reports
    const markdownReport = generateMarkdownReport(results);
    fs.writeFileSync(REPORT_MD_PATH, markdownReport, "utf-8");

    const htmlReport = generateHtmlReport(results);
    fs.writeFileSync(REPORT_HTML_PATH, htmlReport, "utf-8");

    console.log(
      "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
    );
    console.log("📋 Snapshot Execution Complete!");
    console.log(`📄 Markdown Report: ${REPORT_MD_PATH}`);
    console.log(`🌐 HTML Gallery:    ${REPORT_HTML_PATH}`);
    console.log(
      "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n",
    );

    const modifiedViews = results.filter((r) => r.status === "MODIFIED");
    if (modifiedViews.length > 0) {
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
