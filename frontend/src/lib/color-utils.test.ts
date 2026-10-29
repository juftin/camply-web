import { describe, expect, it } from "vitest";
import {
  calculateContrast,
  evaluateContrast,
  evaluateGlareRisk,
  formatHslCss,
  generateCssSnippet,
  hexToHsl,
  hexToRgb,
  hslToHex,
  hslToRgb,
  rgbToHex,
  rgbToHsl,
  PRESET_PALETTES,
} from "./color-utils";

describe("color-utils", () => {
  it("converts HSL to RGB and back accurately", () => {
    const original = { h: 215, s: 50, l: 46 };
    const rgb = hslToRgb(original.h, original.s, original.l);
    const convertedBack = rgbToHsl(rgb.r, rgb.g, rgb.b);

    expect(convertedBack.h).toBe(original.h);
    expect(convertedBack.s).toBe(original.s);
    expect(convertedBack.l).toBe(original.l);
  });

  it("converts Hex to RGB and HSL", () => {
    const hex = "#3b6cb0";
    const rgb = hexToRgb(hex);
    expect(rgb).toEqual({ r: 59, g: 108, b: 176 });

    const hsl = hexToHsl(hex);
    expect(hsl).toEqual({ h: 215, s: 50, l: 46 });

    expect(rgbToHex(rgb)).toBe(hex);
    expect(hslToHex(hsl.h, hsl.s, hsl.l)).toBe(hex);
  });

  it("calculates WCAG contrast ratio accurately", () => {
    const black = { r: 2, g: 8, b: 23 }; // #020817
    const white = { r: 255, g: 255, b: 255 };
    const slateBlue = { r: 59, g: 108, b: 176 }; // #3b6cb0

    const contrastBlackWhite = calculateContrast(black, white);
    expect(contrastBlackWhite).toBeGreaterThan(18);

    const contrastText = calculateContrast(slateBlue, white);
    expect(contrastText).toBeGreaterThan(4.5);
    expect(evaluateContrast(contrastText).pass).toBe(true);
  });

  it("flags optical glare risk for high-saturation cyan/blue in dark mode", () => {
    // 91% saturation electric blue
    const neonBlue = { h: 217, s: 91, l: 60 };
    const assessment = evaluateGlareRisk(neonBlue, true);
    expect(assessment.hasRisk).toBe(true);
    expect(assessment.message).toContain("chromostereopsis");

    // Calibrated steel blue
    const steelBlue = { h: 215, s: 45, l: 60 };
    expect(evaluateGlareRisk(steelBlue, true).hasRisk).toBe(false);

    // Light mode does not trigger dark mode chromostereopsis
    expect(evaluateGlareRisk(neonBlue, false).hasRisk).toBe(false);
  });

  it("generates valid CSS snippet and format string", () => {
    const light = { h: 215, s: 50, l: 46 };
    const dark = { h: 215, s: 45, l: 60 };

    expect(formatHslCss(light)).toBe("215 50% 46%");
    expect(formatHslCss(dark)).toBe("215 45% 60%");

    const css = generateCssSnippet(light, dark);
    expect(css).toContain("--primary: 215 50% 46%;");
    expect(css).toContain("--primary: 215 45% 60%;");
    expect(css).toContain(".camply-map-camp");
  });

  it("defines standard preset palettes with valid values", () => {
    expect(PRESET_PALETTES.length).toBeGreaterThanOrEqual(5);
    for (const preset of PRESET_PALETTES) {
      expect(preset.light.h).toBeGreaterThanOrEqual(0);
      expect(preset.light.h).toBeLessThanOrEqual(360);
      expect(preset.dark.s).toBeGreaterThanOrEqual(0);
      expect(preset.dark.s).toBeLessThanOrEqual(100);
    }
  });
});
