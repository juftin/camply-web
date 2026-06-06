// SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0

/**
 * OpenAPI TypeScript Client Generator
 *
 * Usage:
 *   1. Start the backend: `task backend:dev`
 *   2. Run: `npx tsx src/lib/codegen.ts`
 *
 * This script fetches the OpenAPI schema from the running backend
 * and generates TypeScript types into `src/lib/api/generated/`.
 */

/* eslint-disable no-undef */

import { execSync } from "node:child_process";
import { writeFileSync, mkdirSync } from "node:fs";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));

const API_URL = process.env.CAMPLY_API_URL || "http://localhost:8000";
const OUTPUT_DIR = resolve(__dirname, "api", "generated");
const OPENAPI_URL = `${API_URL}/api/openapi.json`;
const TEMP_SCHEMA = resolve(__dirname, "..", "..", "tmp", "openapi.json");

async function generate(): Promise<void> {
  console.log(`Fetching OpenAPI schema from ${OPENAPI_URL}...`);

  try {
    const response = await fetch(OPENAPI_URL);
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }
    const schema = await response.json();
    mkdirSync(dirname(TEMP_SCHEMA), { recursive: true });
    writeFileSync(TEMP_SCHEMA, JSON.stringify(schema, null, 2));
    console.log(`Schema saved to ${TEMP_SCHEMA}`);
  } catch (err) {
    console.error(
      "Failed to fetch OpenAPI schema. Is the backend running?",
    );
    console.error(err);
    process.exit(1);
  }

  console.log("Generating TypeScript client...");
  mkdirSync(OUTPUT_DIR, { recursive: true });

  try {
    execSync(
      `npx openapi-typescript ${TEMP_SCHEMA} -o ${OUTPUT_DIR}/schema.ts`,
      {
        stdio: "inherit",
        cwd: resolve(__dirname, "..", ".."),
      },
    );
    console.log(`TypeScript client generated at ${OUTPUT_DIR}/schema.ts`);
  } catch {
    console.error("Failed to generate TypeScript client.");
    process.exit(1);
  }
}

generate();
