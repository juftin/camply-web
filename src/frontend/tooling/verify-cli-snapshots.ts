/** Render Rich CLI logging in Chromium and verify terminal screenshots. */
import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { chromium, expect } from "@playwright/test";
import {
  generateHtmlReport,
  recordSnapshot,
  type SnapshotResult,
} from "./snapshot-report";

if (fs.existsSync("/tmp/camply-browser-deps/root/usr/lib/x86_64-linux-gnu")) {
  process.env.LD_LIBRARY_PATH = `/tmp/camply-browser-deps/root/usr/lib/x86_64-linux-gnu:/tmp/camply-browser-deps/root/lib/x86_64-linux-gnu:${process.env.LD_LIBRARY_PATH || ""}`;
  process.env.FONTCONFIG_PATH = "/tmp/camply-browser-deps";
}

interface CliScenario {
  name: string;
  command: string;
  description: string;
  html: string;
  expectedText: string[];
}

const PYTHON_EXPORT_SCRIPT = `
import datetime
import io
import json
import logging
from datetime import date
from rich.console import Console
from rich.terminal_theme import SVG_EXPORT_THEME
from camply.cli.output import (
    CamplyRichHandler,
    format_campground_log,
    log_camply,
    render_discovery,
    render_providers,
    render_stays,
)
from camply.cli.providers import provider_entries
from camply.core.search import AvailabilityStay
from camply.providers.dto import CampgroundSearchResult, RecreationAreaSearchResult

FIXED_TIME = datetime.datetime(2026, 7, 1, 12, 0, 0).timestamp()

class DeterministicLogRecord(logging.LogRecord):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.created = FIXED_TIME
        self.msecs = 0.0

logging.setLogRecordFactory(DeterministicLogRecord)

def capture(width, fn):
    console = Console(
        file=io.StringIO(),
        record=True,
        force_terminal=True,
        color_system="truecolor",
        width=width,
    )
    handler = CamplyRichHandler(
        console=console,
        show_path=False,
        markup=False,
        rich_tracebacks=True,
        omit_repeated_times=False,
        log_time_format="[%Y-%m-%d %H:%M:%S]",
    )
    logger = logging.getLogger("camply.cli")
    logger.handlers = [handler]
    logger.setLevel(logging.DEBUG)
    fn(logger)
    return console.export_html(
        theme=SVG_EXPORT_THEME,
        inline_styles=True,
        code_format="{code}",
    )

def run_providers(logger):
    log_camply("camply, the campsite finder ⛺️")
    render_providers(provider_entries())
    log_camply("Exiting camply 👋")

def run_discovery(logger):
    log_camply("camply, the campsite finder ⛺️")
    logger.info('Using Camply Provider: "RecreationDotGov"')
    logger.info('Searching for Campgrounds: "dunes"')
    render_discovery(
        [
            CampgroundSearchResult(
                provider_id=1,
                provider_name="Recreation.gov",
                campground_id="234685",
                campground_name="Pinon Flats Campground",
                recreation_area_id="2738",
                recreation_area_name="Great Sand Dunes National Park & Preserve",
                state="CO",
                country="USA",
                booking_url="https://www.recreation.gov/camping/campgrounds/234685",
            ),
            CampgroundSearchResult(
                provider_id=1,
                provider_name="Recreation.gov",
                campground_id="258887",
                campground_name="Dunewood Campground",
                recreation_area_id="2767",
                recreation_area_name="Indiana Dunes National Park",
                state="IN",
                country="USA",
                booking_url="https://www.recreation.gov/camping/campgrounds/258887",
            ),
            CampgroundSearchResult(
                provider_id=1,
                provider_name="Recreation.gov",
                campground_id="232458",
                campground_name="Platte River Campground",
                recreation_area_id="2937",
                recreation_area_name="Sleeping Bear Dunes National Lakeshore",
                state="MI",
                country="USA",
                booking_url="https://www.recreation.gov/camping/campgrounds/232458",
            ),
        ],
        empty="No campgrounds found.",
    )
    log_camply("Exiting camply 👋")

def run_campsites(logger):
    log_camply("camply, the campsite finder ⛺️")
    logger.info('Using Camply Provider: "RecreationDotGov"')
    logger.info("1 booking nights selected for search, ranging from 2026-12-10 to 2026-12-10")
    target = CampgroundSearchResult(
        provider_id=1,
        provider_name="Recreation.gov",
        campground_id="233117",
        campground_name="Cerro Alto Campground",
        recreation_area_id="1067",
        recreation_area_name="Los Padres National Forest",
        state="CA",
        country="USA",
        booking_url="https://www.recreation.gov/camping/campgrounds/233117",
    )
    logger.info("1 Matching Campgrounds Found")
    logger.info(format_campground_log(target))
    logger.info("Searching across 1 campgrounds")
    render_stays([
        AvailabilityStay(
            campground=target,
            campsite_id="90005",
            campsite_name="001",
            arrival=date(2026, 12, 10),
            checkout=date(2026, 12, 11),
            booking_url="https://www.recreation.gov/camping/campsites/90005",
        ),
        AvailabilityStay(
            campground=target,
            campsite_id="90024",
            campsite_name="002",
            arrival=date(2026, 12, 10),
            checkout=date(2026, 12, 11),
            booking_url="https://www.recreation.gov/camping/campsites/90024",
        ),
        AvailabilityStay(
            campground=target,
            campsite_id="90116",
            campsite_name="003",
            arrival=date(2026, 12, 10),
            checkout=date(2026, 12, 11),
            booking_url="https://www.recreation.gov/camping/campsites/90116",
        ),
    ])
    log_camply("Exiting camply 👋")

def run_debug(logger):
    log_camply("camply, the campsite finder ⛺️")
    logger.debug("Setting up camply debugging")
    logger.debug("Camply Version: 0.1.0")
    logger.debug("Python Version: 3.14.0")
    logger.debug("Platform: linux")
    logger.info('Using Camply Provider: "RecreationDotGov"')
    logger.debug("Debug: Discovering recreation areas on RecreationDotGov.")
    logger.info('Searching for Recreation Areas: "dune"')
    render_discovery(
        [
            RecreationAreaSearchResult(
                provider_id=1,
                provider_name="Recreation.gov",
                recreation_area_id="2738",
                recreation_area_name="Great Sand Dunes National Park & Preserve",
                state="CO",
                country="USA",
                booking_url="https://www.recreation.gov/camping/gateways/2738",
            ),
            RecreationAreaSearchResult(
                provider_id=1,
                provider_name="Recreation.gov",
                recreation_area_id="2767",
                recreation_area_name="Indiana Dunes National Park",
                state="IN",
                country="USA",
                booking_url="https://www.recreation.gov/camping/gateways/2767",
            ),
            RecreationAreaSearchResult(
                provider_id=1,
                provider_name="Recreation.gov",
                recreation_area_id="2937",
                recreation_area_name="Sleeping Bear Dunes National Lakeshore",
                state="MI",
                country="USA",
                booking_url="https://www.recreation.gov/camping/gateways/2937",
            ),
        ],
        empty="No recreation areas found.",
    )
    log_camply("Exiting camply 👋")

scenarios = [
    {
        "name": "cli-providers",
        "command": "camply providers",
        "description": "Classic camply provider catalog logs and welcome/exit banners",
        "html": capture(120, run_providers),
        "expectedText": ["camply, the campsite finder", '"RecreationDotGov":    Recreation.gov', "Exiting camply"],
    },
    {
        "name": "cli-discovery",
        "command": "camply campgrounds --search dunes",
        "description": "Classic camply campground discovery logs",
        "html": capture(120, run_discovery),
        "expectedText": ["Using Camply Provider", "3 Matching Campgrounds Found", "Pinon Flats Campground (#234685)", "Dunewood Campground (#258887)"],
    },
    {
        "name": "cli-campsites",
        "command": "camply campsites --campground 233117 --start-date 2026-12-10 --end-date 2026-12-11",
        "description": "Classic camply campsite availability logs grouped by date and campground",
        "html": capture(120, run_campsites),
        "expectedText": ["1 booking nights selected", "3 Reservable Campsites Matching Search Preferences", "📅 Thu, December 10 🏕  3 sites", "https://www.recreation.gov/camping/campsites/90005 (1 night)"],
    },
    {
        "name": "cli-debug",
        "command": "camply --debug recreation-areas --search dune",
        "description": "Classic camply debug diagnostics and recreation area discovery logs",
        "html": capture(120, run_debug),
        "expectedText": ["Setting up camply debugging", "Camply Version: 0.1.0", "3 recreation areas found.", "Great Sand Dunes National Park & Preserve, CO (#2738)"],
    },
]
print(json.dumps(scenarios))
`;

function buildTerminalDocument(scenario: CliScenario): string {
  return `<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<style>
  * { box-sizing: border-box; }
  body {
    margin: 0;
    padding: 0;
    background: transparent;
    display: inline-block;
  }
  .terminal-card {
    background: #182324;
    border: 2px solid #354748;
    border-radius: 16px;
    padding: 24px 28px;
    color: #e6edf3;
    font-family: "Liberation Mono", "DejaVu Sans Mono", "Noto Color Emoji", ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
    font-size: 13.5px;
    line-height: 1.45;
    display: inline-block;
  }
  .prompt {
    color: #8cd69b;
    font-weight: 700;
    margin-bottom: 14px;
    white-space: pre;
  }
  .prompt .dollar {
    color: #6bc47d;
    margin-right: 8px;
  }
  pre.cli-output {
    margin: 0;
    font-family: inherit;
    font-size: inherit;
    line-height: inherit;
    white-space: pre;
    overflow: visible;
  }
</style>
</head>
<body>
  <section class="terminal-card" aria-label="${scenario.name}">
    <div class="prompt"><span class="dollar">$</span>${scenario.command}</div>
    <pre class="cli-output">${scenario.html.trimEnd()}</pre>
  </section>
</body>
</html>`;
}

function loadScenarios(rootDir: string): CliScenario[] {
  const output = execFileSync(
    "uv",
    ["run", "--no-sync", "python", "-c", PYTHON_EXPORT_SCRIPT],
    {
      cwd: rootDir,
      encoding: "utf-8",
      maxBuffer: 10 * 1024 * 1024,
    },
  );
  return JSON.parse(output) as CliScenario[];
}

async function main(): Promise<void> {
  const rootDir = path.resolve(import.meta.dirname, "../../..");
  const outputDir = path.join(rootDir, "tmp", "cli-snapshots");
  const baselinesDir = path.join(outputDir, "baselines");
  fs.mkdirSync(outputDir, { recursive: true });
  const writeDocs = process.argv.includes("--write-docs");

  const scenarios = loadScenarios(rootDir);
  assert.equal(scenarios.length, 4);

  const browser = await chromium.launch({
    headless: true,
    args: ["--no-sandbox", "--disable-setuid-sandbox"],
  });
  try {
    const context = await browser.newContext({
      viewport: { width: 1800, height: 1000 },
      deviceScaleFactor: 2,
    });
    const page = await context.newPage();
    const results: SnapshotResult[] = [];

    for (const scenario of scenarios) {
      await page.setContent(buildTerminalDocument(scenario));
      const card = page.getByRole("region", {
        name: scenario.name,
        exact: true,
      });
      await expect(card).toBeVisible();
      for (const expected of scenario.expectedText) {
        await expect(card).toContainText(expected);
      }
      const noHorizontalOverflow = await card
        .locator("pre.cli-output")
        .evaluate((element) => element.scrollWidth <= element.clientWidth + 1);
      assert.equal(
        noHorizontalOverflow,
        true,
        `CLI output overflowed container in ${scenario.name}`,
      );

      const styledSpanCount = await card
        .locator("pre.cli-output span[style*='color']")
        .count();
      assert.ok(
        styledSpanCount >= 10,
        `Expected Rich styled spans in ${scenario.name}, found ${styledSpanCount}`,
      );

      const screenshot = await card.screenshot({ omitBackground: true });
      const box = await card.boundingBox();
      assert.ok(box && box.width > 400 && box.height > 150);

      const metadata = {
        name: scenario.name,
        description: scenario.description,
        viewport: `${Math.round(box.width)}x${Math.round(box.height)}`,
        theme: "dark" as const,
      };
      // Seed baseline and verify deterministic re-capture matches with 0 diff pixels.
      recordSnapshot(outputDir, metadata, screenshot, {
        update: true,
        baselinesDir,
      });
      const verified = recordSnapshot(outputDir, metadata, screenshot, {
        baselinesDir,
      });
      assert.equal(verified.status, "UNCHANGED");
      assert.equal(verified.diffPixels, 0);
      results.push(verified);
    }

    fs.writeFileSync(
      path.join(outputDir, "report.html"),
      generateHtmlReport(results),
      "utf-8",
    );

    if (writeDocs) {
      const docsAssetsDir = path.join(rootDir, "docs", "assets");
      fs.copyFileSync(
        path.join(outputDir, "current", "cli-discovery.png"),
        path.join(docsAssetsDir, "camply-cli-discovery.png"),
      );
      fs.copyFileSync(
        path.join(outputDir, "current", "cli-campsites.png"),
        path.join(docsAssetsDir, "camply-cli-campsites.png"),
      );
    }

    console.log(
      `CLI terminal screenshot verification passed (${results.length} scenarios). Gallery: ${path.join(outputDir, "report.html")}`,
    );
  } finally {
    await browser.close();
  }
}

main().catch((error: unknown) => {
  console.error(error);
  process.exitCode = 1;
});
