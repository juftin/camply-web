// @vitest-environment node
/** Regressions for the nested Pages project and its HTTP proxy contract. */
import { readFileSync } from "node:fs";
import ts from "typescript";
import { describe, expect, it } from "vitest";

describe("Pages configuration", () => {
  it("finds the project configuration beside its nested Functions", () => {
    const { config, error } = ts.parseConfigFileTextToJson(
      "wrangler.jsonc",
      readFileSync(new URL("../wrangler.jsonc", import.meta.url), "utf8"),
    );
    expect(error).toBeUndefined();
    expect(config).toMatchObject({
      name: "camply-81r",
      pages_build_output_dir: "../../build/frontend",
      compatibility_date: "2024-11-11",
    });
  });
});
