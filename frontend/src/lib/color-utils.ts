/**
 * Color manipulation, WCAG contrast calculation, and HSL/Hex utilities
 * for the interactive Camply theme experimenter.
 */

export interface HslColor {
  h: number; // 0 - 360
  s: number; // 0 - 100
  l: number; // 0 - 100
}

export interface RgbColor {
  r: number; // 0 - 255
  g: number; // 0 - 255
  b: number; // 0 - 255
}

export interface PalettePreset {
  id: string;
  name: string;
  description: string;
  light: HslColor;
  dark: HslColor;
  badge?: string;
}

export const PRESET_PALETTES: PalettePreset[] = [
  {
    id: "steel-slate",
    name: "Steel / Slate Blue",
    description:
      "Modern, calm, balanced (Linear / GitHub style). Default choice.",
    light: { h: 215, s: 50, l: 46 },
    dark: { h: 215, s: 45, l: 60 },
    badge: "Recommended",
  },
  {
    id: "alpine-lake",
    name: "Alpine Lake Blue",
    description:
      "Glacial mountain lake cyan-blue. Nature and campsite inspired.",
    light: { h: 204, s: 55, l: 42 },
    dark: { h: 204, s: 48, l: 58 },
    badge: "Nature",
  },
  {
    id: "nordic-dusk",
    name: "Nordic Dusk",
    description: "Ultra-low glare evening twilight with 38% saturation.",
    light: { h: 218, s: 38, l: 48 },
    dark: { h: 218, s: 38, l: 62 },
    badge: "Low Glare",
  },
  {
    id: "deep-denim",
    name: "Deep Denim Navy",
    description: "Classic structured nautical indigo navy.",
    light: { h: 224, s: 46, l: 45 },
    dark: { h: 222, s: 42, l: 62 },
  },
  {
    id: "evergreen-pine",
    name: "Evergreen Pine",
    description: "Forest green inspired by Camply's pine logo artwork.",
    light: { h: 152, s: 60, l: 36 },
    dark: { h: 152, s: 48, l: 54 },
    badge: "Forest",
  },
  {
    id: "campfire-amber",
    name: "Campfire Amber",
    description: "Warm glowing campfire and tent orange.",
    light: { h: 28, s: 80, l: 44 },
    dark: { h: 28, s: 70, l: 58 },
    badge: "Warm",
  },
  {
    id: "legacy-neon",
    name: "Legacy Neon Blue",
    description: "Original 91% saturation Tailwind blue (High Glare baseline).",
    light: { h: 221, s: 83, l: 53 },
    dark: { h: 217, s: 91, l: 60 },
    badge: "Legacy Glow",
  },
];

/**
 * Converts HSL values to an RGB object.
 */
export function hslToRgb(h: number, s: number, l: number): RgbColor {
  h = ((h % 360) + 360) % 360;
  const sat = Math.max(0, Math.min(100, s)) / 100;
  const lum = Math.max(0, Math.min(100, l)) / 100;

  const c = (1 - Math.abs(2 * lum - 1)) * sat;
  const x = c * (1 - Math.abs(((h / 60) % 2) - 1));
  const m = lum - c / 2;

  let r = 0;
  let g = 0;
  let b = 0;

  if (0 <= h && h < 60) {
    r = c;
    g = x;
    b = 0;
  } else if (60 <= h && h < 120) {
    r = x;
    g = c;
    b = 0;
  } else if (120 <= h && h < 180) {
    r = 0;
    g = c;
    b = x;
  } else if (180 <= h && h < 240) {
    r = 0;
    g = x;
    b = c;
  } else if (240 <= h && h < 300) {
    r = x;
    g = 0;
    b = c;
  } else if (300 <= h && h < 360) {
    r = c;
    g = 0;
    b = x;
  }

  return {
    r: Math.round((r + m) * 255),
    g: Math.round((g + m) * 255),
    b: Math.round((b + m) * 255),
  };
}

/**
 * Converts RGB values to an HSL object.
 */
export function rgbToHsl(r: number, g: number, b: number): HslColor {
  const normR = r / 255;
  const normG = g / 255;
  const normB = b / 255;

  const max = Math.max(normR, normG, normB);
  const min = Math.min(normR, normG, normB);

  let h = 0;
  let s = 0;
  const l = (max + min) / 2;

  if (max !== min) {
    const d = max - min;
    s = l > 0.5 ? d / (2 - max - min) : d / (max + min);

    switch (max) {
      case normR:
        h = (normG - normB) / d + (normG < normB ? 6 : 0);
        break;
      case normG:
        h = (normB - normR) / d + 2;
        break;
      case normB:
        h = (normR - normG) / d + 4;
        break;
    }
    h *= 60;
  }

  return {
    h: Math.round(h),
    s: Math.round(s * 100),
    l: Math.round(l * 100),
  };
}

/**
 * Converts Hex string (e.g., "#3b6cb0") to RGB.
 */
export function hexToRgb(hex: string): RgbColor {
  const cleanHex = hex.replace(/^#/, "");
  const fullHex =
    cleanHex.length === 3
      ? cleanHex
          .split("")
          .map((c) => c + c)
          .join("")
      : cleanHex;

  const num = parseInt(fullHex, 16);
  return {
    r: (num >> 16) & 255,
    g: (num >> 8) & 255,
    b: num & 255,
  };
}

/**
 * Converts RGB to 6-character Hex string with leading #.
 */
export function rgbToHex(rgb: RgbColor): string {
  const toHex = (n: number) =>
    Math.max(0, Math.min(255, n)).toString(16).padStart(2, "0");
  return `#${toHex(rgb.r)}${toHex(rgb.g)}${toHex(rgb.b)}`;
}

/**
 * Converts HSL to Hex string.
 */
export function hslToHex(h: number, s: number, l: number): string {
  return rgbToHex(hslToRgb(h, s, l));
}

/**
 * Converts Hex to HSL.
 */
export function hexToHsl(hex: string): HslColor {
  const rgb = hexToRgb(hex);
  return rgbToHsl(rgb.r, rgb.g, rgb.b);
}

/**
 * Calculates WCAG 2.1 relative luminance for an sRGB channel.
 */
function sRgbLuminanceChannel(value: number): number {
  const normalized = value / 255;
  return normalized <= 0.03928
    ? normalized / 12.92
    : Math.pow((normalized + 0.055) / 1.055, 2.4);
}

/**
 * Calculates WCAG relative luminance (0.0 to 1.0).
 */
export function getRelativeLuminance(rgb: RgbColor): number {
  return (
    0.2126 * sRgbLuminanceChannel(rgb.r) +
    0.7152 * sRgbLuminanceChannel(rgb.g) +
    0.0722 * sRgbLuminanceChannel(rgb.b)
  );
}

/**
 * Calculates WCAG contrast ratio between two colors (e.g. 4.5 for 4.5:1).
 */
export function calculateContrast(rgb1: RgbColor, rgb2: RgbColor): number {
  const lum1 = getRelativeLuminance(rgb1);
  const lum2 = getRelativeLuminance(rgb2);
  const lighter = Math.max(lum1, lum2);
  const darker = Math.min(lum1, lum2);
  return Number(((lighter + 0.05) / (darker + 0.05)).toFixed(2));
}

/**
 * WCAG compliance assessment result.
 */
export interface ContrastAssessment {
  ratio: number;
  level: "AAA" | "AA" | "AA Large" | "Fail";
  pass: boolean;
  scoreLabel: string;
}

/**
 * Evaluates contrast ratio compliance.
 */
export function evaluateContrast(ratio: number): ContrastAssessment {
  if (ratio >= 7.0) {
    return {
      ratio,
      level: "AAA",
      pass: true,
      scoreLabel: "AAA (Excellent)",
    };
  }
  if (ratio >= 4.5) {
    return {
      ratio,
      level: "AA",
      pass: true,
      scoreLabel: "AA (Standard)",
    };
  }
  if (ratio >= 3.0) {
    return {
      ratio,
      level: "AA Large",
      pass: true,
      scoreLabel: "AA Large (Components / Large text)",
    };
  }
  return {
    ratio,
    level: "Fail",
    pass: false,
    scoreLabel: "Low Contrast (May fail accessibility)",
  };
}

/**
 * Evaluates whether a color carries optical glare / neon halo risk in dark mode.
 */
export function evaluateGlareRisk(
  hsl: HslColor,
  isDark: boolean,
): {
  hasRisk: boolean;
  message?: string;
} {
  if (!isDark) {
    return { hasRisk: false };
  }

  // Cyan-blue hue range with high saturation and high lightness on dark canvas
  if (hsl.h >= 200 && hsl.h <= 230 && hsl.s > 70 && hsl.l > 55) {
    return {
      hasRisk: true,
      message:
        "High saturation (>70%) cyan-blue in dark mode causes chromostereopsis (optical glowing halo).",
    };
  }

  if (hsl.s > 80) {
    return {
      hasRisk: true,
      message:
        "Saturation above 80% can cause eye strain against dark backgrounds.",
    };
  }

  return { hasRisk: false };
}

/**
 * Formats an HSL object into standard CSS variable format: "215 50% 46%".
 */
export function formatHslCss(hsl: HslColor): string {
  return `${hsl.h} ${hsl.s}% ${hsl.l}%`;
}

/**
 * Generates ready-to-copy CSS code snippet.
 */
export function generateCssSnippet(light: HslColor, dark: HslColor): string {
  return `@layer base {
  :root {
    --primary: ${formatHslCss(light)};
    --ring: ${formatHslCss(light)};
  }

  .dark {
    --primary: ${formatHslCss(dark)};
    --ring: ${formatHslCss(dark)};
  }
}

.camply-map-camp {
  background: hsl(var(--primary));
}`;
}
