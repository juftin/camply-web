export type ThemeTokenKey =
  | "background"
  | "foreground"
  | "card"
  | "card-foreground"
  | "popover"
  | "popover-foreground"
  | "primary"
  | "primary-foreground"
  | "secondary"
  | "secondary-foreground"
  | "muted"
  | "muted-foreground"
  | "accent"
  | "accent-foreground"
  | "destructive"
  | "destructive-foreground"
  | "border"
  | "input"
  | "ring";

export type ThemeTokens = Record<ThemeTokenKey, string>;

export interface MapPinColors {
  camp: string;
  area: string;
  group: string;
}

export interface ThemePalette {
  light: ThemeTokens;
  dark: ThemeTokens;
  radius: string;
  fontId: string;
  mapPins?: MapPinColors;
}

export interface HslColor {
  h: number;
  s: number;
  l: number;
}

export interface RgbColor {
  r: number;
  g: number;
  b: number;
}

export const ALL_TOKEN_KEYS: readonly ThemeTokenKey[] = [
  "background",
  "foreground",
  "card",
  "card-foreground",
  "popover",
  "popover-foreground",
  "primary",
  "primary-foreground",
  "secondary",
  "secondary-foreground",
  "muted",
  "muted-foreground",
  "accent",
  "accent-foreground",
  "destructive",
  "destructive-foreground",
  "border",
  "input",
  "ring",
];

export const SURFACE_TOKEN_KEYS: readonly ThemeTokenKey[] = [
  "background",
  "card",
  "popover",
  "secondary",
  "muted",
  "accent",
  "border",
  "input",
];

export const ACCENT_TOKEN_KEYS: readonly ThemeTokenKey[] = ["primary", "ring"];

function clamp(value: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, value));
}

function round1(value: number): number {
  return Math.round(value * 10) / 10;
}

/** Parse a Tailwind CSS variable HSL string like "221.2 83.2% 53.3%" into H/S/L. */
export function parseHslString(value: string): HslColor {
  const parts = value
    .trim()
    .replace(/,/g, " ")
    .split(/\s+/)
    .map((part) => Number.parseFloat(part.replace("%", "")));

  const h = Number.isFinite(parts[0]) ? ((parts[0] % 360) + 360) % 360 : 0;
  const s = Number.isFinite(parts[1]) ? clamp(parts[1], 0, 100) : 0;
  const l = Number.isFinite(parts[2]) ? clamp(parts[2], 0, 100) : 50;
  return { h: round1(h), s: round1(s), l: round1(l) };
}

/** Format an HslColor into the space-separated CSS variable format used by Tailwind. */
export function formatHslString(hsl: HslColor): string {
  const h = round1(((hsl.h % 360) + 360) % 360);
  const s = round1(clamp(hsl.s, 0, 100));
  const l = round1(clamp(hsl.l, 0, 100));
  return `${h} ${s}% ${l}%`;
}

export function hslToRgb(hsl: HslColor): RgbColor {
  const h = (((hsl.h % 360) + 360) % 360) / 360;
  const s = clamp(hsl.s, 0, 100) / 100;
  const l = clamp(hsl.l, 0, 100) / 100;

  if (s === 0) {
    const gray = Math.round(l * 255);
    return { r: gray, g: gray, b: gray };
  }

  const hue2rgb = (p: number, q: number, tIn: number): number => {
    let t = tIn;
    if (t < 0) t += 1;
    if (t > 1) t -= 1;
    if (t < 1 / 6) return p + (q - p) * 6 * t;
    if (t < 1 / 2) return q;
    if (t < 2 / 3) return p + (q - p) * (2 / 3 - t) * 6;
    return p;
  };

  const q = l < 0.5 ? l * (1 + s) : l + s - l * s;
  const p = 2 * l - q;

  return {
    r: Math.round(hue2rgb(p, q, h + 1 / 3) * 255),
    g: Math.round(hue2rgb(p, q, h) * 255),
    b: Math.round(hue2rgb(p, q, h - 1 / 3) * 255),
  };
}

export function rgbToHex(rgb: RgbColor): string {
  const toHex = (n: number) =>
    clamp(Math.round(n), 0, 255).toString(16).padStart(2, "0");
  return `#${toHex(rgb.r)}${toHex(rgb.g)}${toHex(rgb.b)}`;
}

export function hexToRgb(hex: string): RgbColor | null {
  const cleaned = hex.trim().replace(/^#/, "");
  if (/^[0-9a-fA-F]{3}$/.test(cleaned)) {
    return {
      r: Number.parseInt(cleaned[0] + cleaned[0], 16),
      g: Number.parseInt(cleaned[1] + cleaned[1], 16),
      b: Number.parseInt(cleaned[2] + cleaned[2], 16),
    };
  }
  if (/^[0-9a-fA-F]{6}$/.test(cleaned)) {
    return {
      r: Number.parseInt(cleaned.slice(0, 2), 16),
      g: Number.parseInt(cleaned.slice(2, 4), 16),
      b: Number.parseInt(cleaned.slice(4, 6), 16),
    };
  }
  return null;
}

export function rgbToHsl(rgb: RgbColor): HslColor {
  const r = clamp(rgb.r, 0, 255) / 255;
  const g = clamp(rgb.g, 0, 255) / 255;
  const b = clamp(rgb.b, 0, 255) / 255;

  const max = Math.max(r, g, b);
  const min = Math.min(r, g, b);
  const l = (max + min) / 2;
  let h = 0;
  let s = 0;

  if (max !== min) {
    const d = max - min;
    s = l > 0.5 ? d / (2 - max - min) : d / (max + min);
    switch (max) {
      case r:
        h = (g - b) / d + (g < b ? 6 : 0);
        break;
      case g:
        h = (b - r) / d + 2;
        break;
      default:
        h = (r - g) / d + 4;
        break;
    }
    h *= 60;
  }

  return {
    h: round1(h),
    s: round1(s * 100),
    l: round1(l * 100),
  };
}

export function hslStringToHex(value: string): string {
  return rgbToHex(hslToRgb(parseHslString(value)));
}

export function hexToHslString(hex: string): string | null {
  const rgb = hexToRgb(hex);
  if (!rgb) return null;
  return formatHslString(rgbToHsl(rgb));
}

function relativeLuminance(rgb: RgbColor): number {
  const linear = [rgb.r, rgb.g, rgb.b].map((channel) => {
    const c = channel / 255;
    return c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
  });
  return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2];
}

/** Calculate WCAG 2.1 contrast ratio between two HSL token strings. */
export function contrastRatio(hslA: string, hslB: string): number {
  const lumA = relativeLuminance(hslToRgb(parseHslString(hslA)));
  const lumB = relativeLuminance(hslToRgb(parseHslString(hslB)));
  const lighter = Math.max(lumA, lumB);
  const darker = Math.min(lumA, lumB);
  return Math.round(((lighter + 0.05) / (darker + 0.05)) * 100) / 100;
}

/** Pick an accessible light or dark foreground HSL string for a given background HSL string. */
export function autoContrastForeground(bgHsl: string): string {
  const lightCandidate = "40 33% 98%";
  const darkCandidate = "180 12% 10%";
  const lightContrast = contrastRatio(bgHsl, lightCandidate);
  const darkContrast = contrastRatio(bgHsl, darkCandidate);
  return lightContrast >= darkContrast ? lightCandidate : darkCandidate;
}

export interface MacroAdjustments {
  hueShift: number;
  saturationScale: number;
  warmth: number;
}

export const DEFAULT_MACRO_ADJUSTMENTS: MacroAdjustments = {
  hueShift: 0,
  saturationScale: 100,
  warmth: 0,
};

/**
 * Apply non-destructive macro adjustments (hue shift on brand/accent, saturation scale,
 * and surface warmth shift) on top of a base token map.
 */
export function applyMacroAdjustments(
  tokens: ThemeTokens,
  adjustments: MacroAdjustments,
): ThemeTokens {
  const { hueShift, saturationScale, warmth } = adjustments;
  if (hueShift === 0 && saturationScale === 100 && warmth === 0) {
    return tokens;
  }

  const next = { ...tokens };
  const satFactor = saturationScale / 100;

  for (const key of ALL_TOKEN_KEYS) {
    const parsed = parseHslString(tokens[key]);
    let { h, s, l } = parsed;

    // Hue shift applies most strongly to primary/ring, and subtly to other chromatic tokens
    if (hueShift !== 0) {
      if (ACCENT_TOKEN_KEYS.includes(key)) {
        h = (h + hueShift + 360) % 360;
      } else if (
        key !== "destructive" &&
        key !== "destructive-foreground" &&
        s > 8
      ) {
        h = (h + hueShift * 0.35 + 360) % 360;
      }
    }

    // Saturation scaling preserves destructive clarity slightly while tuning everything else
    if (saturationScale !== 100) {
      if (key !== "destructive" && key !== "destructive-foreground") {
        s = clamp(s * satFactor, 0, 100);
      }
    }

    // Warmth pulls neutral/surface hues toward warm paper/parchment (~38deg) or cool slate (~212deg)
    if (warmth !== 0 && SURFACE_TOKEN_KEYS.includes(key)) {
      const targetHue = warmth > 0 ? 38 : 212;
      const strength = Math.abs(warmth) / 100;
      const isDarkSurface = l < 50;
      // Blend hue toward warm/cool target and add gentle tint saturation
      const deltaHue = ((targetHue - h + 540) % 360) - 180;
      h = (h + deltaHue * strength * 0.75 + 360) % 360;
      const targetTintSat = isDarkSurface ? 14 : 26;
      s = clamp(s + (targetTintSat - s) * strength * 0.6, 0, 45);
      // Slight paper softening for pure white backgrounds when warming
      if (warmth > 0 && key === "background" && l > 98) {
        l = clamp(l - strength * 3.5, 92, 100);
      }
    }

    next[key] = formatHslString({ h, s, l });
  }

  // Re-ensure primary-foreground stays legible if primary shifted significantly
  if (contrastRatio(next.primary, next["primary-foreground"]) < 4.5) {
    next["primary-foreground"] = autoContrastForeground(next.primary);
  }

  return next;
}

/** Generate a randomized outdoor/earthy theme palette (both light and dark). */
export function generateEarthyPalette(): ThemePalette {
  // Curated natural hue bands: pine/spruce (140-195), olive/moss (75-125), terracotta/ochre (15-42), slate-fjord (198-218)
  const bands: Array<[number, number, [number, number], [number, number]]> = [
    [145, 192, [34, 62], [20, 32]], // spruce / evergreen
    [78, 122, [28, 48], [24, 34]], // moss / olive
    [16, 40, [48, 72], [36, 46]], // terracotta / ochre / redwood
    [198, 214, [26, 44], [28, 38]], // glacier mineral slate
  ];
  const band = bands[Math.floor(Math.random() * bands.length)];
  const primaryHue = round1(band[0] + Math.random() * (band[1] - band[0]));
  const primarySat = round1(
    band[2][0] + Math.random() * (band[2][1] - band[2][0]),
  );
  const primaryLight = round1(
    band[3][0] + Math.random() * (band[3][1] - band[3][0]),
  );

  // Subtle warm paper or cool stone base
  const isWarmPaper = Math.random() > 0.25;
  const baseHue = isWarmPaper
    ? round1(34 + Math.random() * 14)
    : round1((primaryHue + 10) % 360);
  const bgSat = isWarmPaper
    ? round1(18 + Math.random() * 16)
    : round1(8 + Math.random() * 10);
  const bgLight = round1(95.5 + Math.random() * 3.5);

  const primary = formatHslString({
    h: primaryHue,
    s: primarySat,
    l: primaryLight,
  });
  const darkPrimary = formatHslString({
    h: primaryHue,
    s: clamp(primarySat + 6, 30, 72),
    l: clamp(primaryLight + 20, 48, 62),
  });

  const radii = ["0.25rem", "0.375rem", "0.5rem", "0.625rem", "0.75rem"];
  const radius = radii[Math.floor(Math.random() * radii.length)];

  const light: ThemeTokens = {
    background: formatHslString({ h: baseHue, s: bgSat, l: bgLight }),
    foreground: formatHslString({ h: primaryHue, s: 18, l: 12 }),
    card: formatHslString({
      h: baseHue,
      s: clamp(bgSat - 6, 4, 30),
      l: clamp(bgLight + 2.2, 98, 100),
    }),
    "card-foreground": formatHslString({ h: primaryHue, s: 18, l: 12 }),
    popover: formatHslString({
      h: baseHue,
      s: clamp(bgSat - 6, 4, 30),
      l: clamp(bgLight + 2.2, 98, 100),
    }),
    "popover-foreground": formatHslString({ h: primaryHue, s: 18, l: 12 }),
    primary,
    "primary-foreground": autoContrastForeground(primary),
    secondary: formatHslString({
      h: baseHue,
      s: clamp(bgSat + 4, 12, 30),
      l: 91,
    }),
    "secondary-foreground": formatHslString({ h: primaryHue, s: 22, l: 18 }),
    muted: formatHslString({
      h: baseHue,
      s: clamp(bgSat + 2, 10, 26),
      l: 91.5,
    }),
    "muted-foreground": formatHslString({ h: baseHue, s: 12, l: 41 }),
    accent: formatHslString({ h: primaryHue, s: 22, l: 90 }),
    "accent-foreground": formatHslString({ h: primaryHue, s: 28, l: 16 }),
    destructive: "7 68% 46%",
    "destructive-foreground": "40 33% 98%",
    border: formatHslString({ h: baseHue, s: clamp(bgSat - 2, 10, 24), l: 84 }),
    input: formatHslString({ h: baseHue, s: clamp(bgSat - 2, 10, 24), l: 84 }),
    ring: primary,
  };

  const darkHue = isWarmPaper ? primaryHue : baseHue;
  const dark: ThemeTokens = {
    background: formatHslString({ h: darkHue, s: 16, l: 8.5 }),
    foreground: formatHslString({ h: baseHue, s: 18, l: 93 }),
    card: formatHslString({ h: darkHue, s: 14, l: 11.5 }),
    "card-foreground": formatHslString({ h: baseHue, s: 18, l: 93 }),
    popover: formatHslString({ h: darkHue, s: 14, l: 11.5 }),
    "popover-foreground": formatHslString({ h: baseHue, s: 18, l: 93 }),
    primary: darkPrimary,
    "primary-foreground": autoContrastForeground(darkPrimary),
    secondary: formatHslString({ h: darkHue, s: 14, l: 17 }),
    "secondary-foreground": formatHslString({ h: baseHue, s: 18, l: 92 }),
    muted: formatHslString({ h: darkHue, s: 14, l: 16 }),
    "muted-foreground": formatHslString({ h: baseHue, s: 12, l: 64 }),
    accent: formatHslString({ h: primaryHue, s: 20, l: 20 }),
    "accent-foreground": formatHslString({ h: baseHue, s: 18, l: 94 }),
    destructive: "7 62% 42%",
    "destructive-foreground": "40 33% 98%",
    border: formatHslString({ h: darkHue, s: 14, l: 21 }),
    input: formatHslString({ h: darkHue, s: 14, l: 21 }),
    ring: darkPrimary,
  };

  return {
    light,
    dark,
    radius,
    fontId: "system",
    mapPins: {
      camp: hslStringToHex(primary),
      area: hslStringToHex(
        formatHslString({ h: (primaryHue + 35) % 360, s: 44, l: 32 }),
      ),
      group: hslStringToHex(formatHslString({ h: darkHue, s: 16, l: 28 })),
    },
  };
}

/** Generate the exact CSS block ready to paste into src/frontend/index.css. */
export function buildCssExport(
  palette: ThemePalette,
  themeName?: string,
): string {
  const formatBlock = (tokens: ThemeTokens, includeRadius: boolean) => {
    const lines = ALL_TOKEN_KEYS.map((key) => `    --${key}: ${tokens[key]};`);
    if (includeRadius) {
      lines.push(`    --radius: ${palette.radius};`);
    }
    return lines.join("\n");
  };

  const header = themeName ? `/* Camply Theme: ${themeName} */\n` : "";
  const mapBlock = palette.mapPins
    ? `\n\n/* Optional map pin colors */\n.camply-map-camp {\n  background: ${palette.mapPins.camp};\n}\n.camply-map-area {\n  background: ${palette.mapPins.area};\n}\n.camply-map-group {\n  background: ${palette.mapPins.group};\n}`
    : "";

  return `${header}@layer base {\n  :root {\n${formatBlock(palette.light, true)}\n  }\n\n  .dark {\n${formatBlock(palette.dark, false)}\n  }\n}${mapBlock}`;
}

/** Build the runtime <style> sheet injected into <head> for instant live theming. */
export function buildRuntimeStyleSheet(
  palette: ThemePalette,
  fontHeadingStack: string | null,
  fontBodyStack: string | null,
): string {
  const lightVars = ALL_TOKEN_KEYS.map(
    (key) => `  --${key}: ${palette.light[key]};`,
  ).join("\n");
  const darkVars = ALL_TOKEN_KEYS.map(
    (key) => `  --${key}: ${palette.dark[key]};`,
  ).join("\n");

  const mapCss = palette.mapPins
    ? `\n.camply-map-camp { background: ${palette.mapPins.camp} !important; }\n.camply-map-area { background: ${palette.mapPins.area} !important; }\n.camply-map-group { background: ${palette.mapPins.group} !important; }\n`
    : "";

  const fontCss =
    fontHeadingStack || fontBodyStack
      ? `\nbody { ${fontBodyStack ? `font-family: ${fontBodyStack};` : ""} }\nh1, h2, h3, h4, h5, h6 { ${fontHeadingStack ? `font-family: ${fontHeadingStack};` : ""} }\n`
      : "";

  return `:root {\n${lightVars}\n  --radius: ${palette.radius};\n}\n\n.dark {\n${darkVars}\n  --radius: ${palette.radius};\n}${mapCss}${fontCss}`;
}
