/**
 * OpenAPI TypeScript Client Generator
 *
 * Usage:
 *   Run `task api:generate` for offline generation or `task api:check` for drift checks.
 *   To fetch from a running backend, use `task frontend:codegen`.
 *
 * This script fetches the OpenAPI schema from the running backend
 * and generates TypeScript types into `src/frontend/lib/api/generated/`.
 */

import { execFileSync } from "node:child_process";
import { writeFileSync, mkdirSync, readFileSync } from "node:fs";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));

const API_URL = process.env.CAMPLY_API_URL || "http://localhost:8000";
const OUTPUT_DIR = resolve(__dirname, "..", "lib", "api", "generated");
const OPENAPI_URL = `${API_URL}/api/openapi.json`;
const TEMP_SCHEMA = resolve(
  __dirname,
  "..",
  "..",
  "..",
  "build",
  "openapi.json",
);

async function generate(): Promise<void> {
  const schemaPath = process.env.CAMPLY_OPENAPI_SCHEMA;
  console.log(`Loading OpenAPI schema from ${schemaPath || OPENAPI_URL}...`);

  try {
    const schema = schemaPath
      ? JSON.parse(readFileSync(schemaPath, "utf8"))
      : await (async () => {
          const response = await fetch(OPENAPI_URL);
          if (!response.ok)
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
          return response.json();
        })();
    mkdirSync(dirname(TEMP_SCHEMA), { recursive: true });
    writeFileSync(TEMP_SCHEMA, JSON.stringify(schema, null, 2));
    console.log(`Schema saved to ${TEMP_SCHEMA}`);
  } catch (err) {
    console.error("Failed to fetch OpenAPI schema. Is the backend running?");
    console.error(err);
    process.exit(1);
  }

  console.log("Generating TypeScript client...");
  mkdirSync(OUTPUT_DIR, { recursive: true });
  const check = process.argv.includes("--check");
  const outputPath = check ? `${TEMP_SCHEMA}.ts` : `${OUTPUT_DIR}/schema.ts`;

  try {
    execFileSync(
      "pnpm",
      ["exec", "openapi-typescript", TEMP_SCHEMA, "-o", outputPath],
      {
        stdio: "inherit",
        cwd: resolve(__dirname, "..", "..", ".."),
      },
    );
    if (
      check &&
      readFileSync(outputPath, "utf8") !==
        readFileSync(`${OUTPUT_DIR}/schema.ts`, "utf8")
    ) {
      throw new Error(
        "Generated API types are stale. Run task api:generate and commit the result.",
      );
    }
    console.log(
      check
        ? "API types match the backend contract."
        : `TypeScript client generated at ${OUTPUT_DIR}/schema.ts`,
    );
  } catch (error) {
    console.error("Failed to generate TypeScript client.", error);
    process.exit(1);
  }
}

generate();
