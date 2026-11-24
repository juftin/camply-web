import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ThemeProviderContext } from "@/hooks/use-theme";
import {
  applyMacroAdjustments,
  buildCssExport,
  contrastRatio,
  hexToHslString,
  hslStringToHex,
} from "./colorUtils";
import { THEME_PRESETS } from "./presets";
import { ThemeStudio } from "./ThemeStudio";

const mockThemeContext = {
  theme: "light" as const,
  userTheme: "light" as const,
  setTheme: vi.fn(),
  toggleTheme: vi.fn(),
};

describe("ThemeStudio color utilities", () => {
  it("converts HSL strings to hex and back accurately", () => {
    const hex = hslStringToHex("187 74% 20%");
    expect(hex).toMatch(/^#[0-9a-f]{6}$/);
    const roundTripped = hexToHslString(hex);
    expect(roundTripped).not.toBeNull();
    expect(hslStringToHex(roundTripped!)).toBe(hex);
  });

  it("computes high contrast between black and white", () => {
    expect(contrastRatio("0 0% 100%", "0 0% 0%")).toBe(21);
  });

  it("ensures every preset maintains accessible body and primary contrast", () => {
    for (const preset of THEME_PRESETS) {
      expect(
        contrastRatio(
          preset.palette.light.background,
          preset.palette.light.foreground,
        ),
      ).toBeGreaterThanOrEqual(7);
      expect(
        contrastRatio(
          preset.palette.dark.background,
          preset.palette.dark.foreground,
        ),
      ).toBeGreaterThanOrEqual(7);
      expect(
        contrastRatio(
          preset.palette.light.primary,
          preset.palette.light["primary-foreground"],
        ),
      ).toBeGreaterThanOrEqual(4.5);
      expect(
        contrastRatio(
          preset.palette.dark.primary,
          preset.palette.dark["primary-foreground"],
        ),
      ).toBeGreaterThanOrEqual(4.5);
    }
  });

  it("applies macro adjustments and exports valid index.css blocks", () => {
    const base = THEME_PRESETS[0].palette;
    const shifted = applyMacroAdjustments(base.light, {
      hueShift: 30,
      saturationScale: 85,
      warmth: 40,
    });
    expect(shifted.primary).not.toBe(base.light.primary);

    const css = buildCssExport(base, "Camply Spruce");
    expect(css).toContain("@layer base");
    expect(css).toContain(":root {");
    expect(css).toContain(".dark {");
    expect(css).toContain("--primary: 187 74% 20%;");
  });
});

describe("ThemeStudio component", () => {
  beforeEach(() => {
    window.localStorage.clear();
    document.getElementById("camply-theme-studio-style")?.remove();
    document.getElementById("camply-theme-studio-font")?.remove();
  });

  it("injects live CSS overrides and switches presets", () => {
    render(
      <ThemeProviderContext.Provider value={mockThemeContext}>
        <ThemeStudio />
      </ThemeProviderContext.Provider>,
    );

    const styleEl = document.getElementById("camply-theme-studio-style");
    expect(styleEl).not.toBeNull();
    expect(styleEl?.textContent).toContain("--primary: 187 74% 20%;");

    fireEvent.click(screen.getByLabelText("Open Theme Studio"));
    expect(screen.getByTestId("theme-studio-drawer")).toBeInTheDocument();

    fireEvent.click(screen.getByText("Moab Terracotta"));
    expect(styleEl?.textContent).toContain("--primary: 13 61% 45%;");

    fireEvent.click(screen.getByText("A/B Stock"));
    expect(styleEl?.textContent).toContain("--primary: 221.2 83.2% 53.3%;");
  });
});
