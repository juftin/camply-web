import { readFileSync } from "node:fs";
import path from "node:path";
import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { ThemeProviderContext } from "@/hooks/use-theme";
import { CamplyLogo } from "./CamplyLogo";

describe("CamplyLogo", () => {
  it.each(["horizontal", "stacked", "icon"] as const)(
    "loads the %s artwork in both themes without changing its proportions",
    (variant) => {
      const theme = {
        theme: "system" as const,
        userTheme: "light" as const,
        setTheme: vi.fn(),
        toggleTheme: vi.fn(),
      };
      const { rerender } = render(
        <ThemeProviderContext.Provider value={theme}>
          <CamplyLogo variant={variant} height={76} />
        </ThemeProviderContext.Provider>,
      );
      const logo = screen.getByRole("img", { name: "camply" });
      const dimensions = [
        logo.getAttribute("width"),
        logo.getAttribute("height"),
      ];

      for (const userTheme of ["light", "dark"] as const) {
        rerender(
          <ThemeProviderContext.Provider value={{ ...theme, userTheme }}>
            <CamplyLogo variant={variant} height={76} />
          </ThemeProviderContext.Provider>,
        );
        const source = logo.getAttribute("src")!;
        expect(source).toBe(
          `${import.meta.env.BASE_URL}branding/camply-${variant}${userTheme === "dark" ? "-dark" : ""}.svg`,
        );
        const svg = new DOMParser().parseFromString(
          readFileSync(
            path.resolve(
              import.meta.dirname,
              "../public",
              source.replace(import.meta.env.BASE_URL, ""),
            ),
            "utf8",
          ),
          "image/svg+xml",
        );
        expect(svg.querySelector("parsererror")).toBeNull();
        expect(svg.querySelector("text, style, image")).toBeNull();
        expect(svg.querySelector("#camply-title") !== null).toBe(
          variant !== "icon",
        );
        const [, , width, height] = svg.documentElement
          .getAttribute("viewBox")!
          .split(" ")
          .map(Number);
        expect(Number(logo.getAttribute("width"))).toBeCloseTo(
          (76 * width) / height,
          0,
        );
        expect([
          logo.getAttribute("width"),
          logo.getAttribute("height"),
        ]).toEqual(dimensions);
      }
    },
  );
});
