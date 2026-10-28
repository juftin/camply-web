import { useEffect, useState, useCallback } from "react";
import {
  type HslColor,
  type PalettePreset,
  PRESET_PALETTES,
  formatHslCss,
  generateCssSnippet,
  evaluateContrast,
  evaluateGlareRisk,
  hslToHex,
  hexToHsl,
  hslToRgb,
  hexToRgb,
  calculateContrast,
  type ContrastAssessment,
} from "@/lib/color-utils";
import { useTheme } from "@/hooks/use-theme";

const STORAGE_KEY_LIGHT = "camply-custom-palette-light";
const STORAGE_KEY_DARK = "camply-custom-palette-dark";
const STORAGE_KEY_FLOAT = "camply-palette-floating-enabled";

export const DEFAULT_PRESET = PRESET_PALETTES[0]; // Steel / Slate Blue

export interface PaletteStudioState {
  light: HslColor;
  dark: HslColor;
  activeHsl: HslColor;
  activeHex: string;
  isCustom: boolean;
  autoTuneDark: boolean;
  isFloatingEnabled: boolean;
  copiedCss: boolean;
  contrast: ContrastAssessment;
  glareAssessment: { hasRisk: boolean; message?: string };
  setAutoTuneDark: (autoTune: boolean) => void;
  setFloatingEnabled: (enabled: boolean) => void;
  setHue: (h: number) => void;
  setSaturation: (s: number) => void;
  setLightness: (l: number) => void;
  setHex: (hex: string) => void;
  applyPreset: (preset: PalettePreset) => void;
  resetToDefault: () => void;
  copyCss: () => Promise<void>;
}

export function usePaletteStudio(): PaletteStudioState {
  const { userTheme } = useTheme();
  const isDark = userTheme === "dark";

  const [light, setLight] = useState<HslColor>(() => {
    try {
      const stored = localStorage.getItem(STORAGE_KEY_LIGHT);
      if (stored) return JSON.parse(stored);
    } catch {
      // fallback
    }
    return DEFAULT_PRESET.light;
  });

  const [dark, setDark] = useState<HslColor>(() => {
    try {
      const stored = localStorage.getItem(STORAGE_KEY_DARK);
      if (stored) return JSON.parse(stored);
    } catch {
      // fallback
    }
    return DEFAULT_PRESET.dark;
  });

  const [isCustom, setIsCustom] = useState<boolean>(() => {
    return Boolean(
      localStorage.getItem(STORAGE_KEY_LIGHT) ||
      localStorage.getItem(STORAGE_KEY_DARK),
    );
  });

  const [autoTuneDark, setAutoTuneDark] = useState<boolean>(true);
  const [copiedCss, setCopiedCss] = useState<boolean>(false);

  const [isFloatingEnabled, setIsFloatingEnabledState] = useState<boolean>(
    () => {
      try {
        return localStorage.getItem(STORAGE_KEY_FLOAT) === "true";
      } catch {
        return false;
      }
    },
  );

  const setFloatingEnabled = useCallback((enabled: boolean) => {
    setIsFloatingEnabledState(enabled);
    localStorage.setItem(STORAGE_KEY_FLOAT, enabled ? "true" : "false");
  }, []);

  // Update DOM styles live whenever light or dark colors change
  useEffect(() => {
    const root = document.documentElement;
    if (isCustom) {
      const currentHsl = isDark ? dark : light;
      const cssVal = formatHslCss(currentHsl);
      root.style.setProperty("--primary", cssVal);
      root.style.setProperty("--ring", cssVal);
    } else {
      root.style.removeProperty("--primary");
      root.style.removeProperty("--ring");
    }
  }, [isCustom, light, dark, isDark]);

  const activeHsl = isDark ? dark : light;
  const activeHex = hslToHex(activeHsl.h, activeHsl.s, activeHsl.l);

  // Calculate live contrast vs button text (white text vs primary button)
  const fgRgb = isDark ? hexToRgb("#f8fafc") : hexToRgb("#ffffff");
  const activeRgb = hslToRgb(activeHsl.h, activeHsl.s, activeHsl.l);

  // Contrast of button text (white text vs primary button)
  const contrastRatio = calculateContrast(activeRgb, fgRgb);
  const contrast = evaluateContrast(contrastRatio);
  const glareAssessment = evaluateGlareRisk(activeHsl, isDark);

  const updateColors = useCallback((newLight: HslColor, newDark: HslColor) => {
    setLight(newLight);
    setDark(newDark);
    setIsCustom(true);
    try {
      localStorage.setItem(STORAGE_KEY_LIGHT, JSON.stringify(newLight));
      localStorage.setItem(STORAGE_KEY_DARK, JSON.stringify(newDark));
    } catch {
      // storage disabled
    }
  }, []);

  const setHue = useCallback(
    (h: number) => {
      const nextLight = { ...light, h };
      const nextDark = autoTuneDark
        ? { ...dark, h }
        : isDark
          ? { ...dark, h }
          : dark;
      if (!isDark) {
        updateColors(nextLight, nextDark);
      } else {
        updateColors(autoTuneDark ? { ...light, h } : light, { ...dark, h });
      }
    },
    [light, dark, isDark, autoTuneDark, updateColors],
  );

  const setSaturation = useCallback(
    (s: number) => {
      if (!isDark) {
        const nextDark = autoTuneDark
          ? { ...dark, s: Math.max(20, Math.min(65, Math.round(s * 0.9))) }
          : dark;
        updateColors({ ...light, s }, nextDark);
      } else {
        updateColors(light, { ...dark, s });
      }
    },
    [light, dark, isDark, autoTuneDark, updateColors],
  );

  const setLightness = useCallback(
    (l: number) => {
      if (!isDark) {
        const nextDark = autoTuneDark
          ? { ...dark, l: Math.max(48, Math.min(68, l + 14)) }
          : dark;
        updateColors({ ...light, l }, nextDark);
      } else {
        updateColors(light, { ...dark, l });
      }
    },
    [light, dark, isDark, autoTuneDark, updateColors],
  );

  const setHex = useCallback(
    (hex: string) => {
      const parsedHsl = hexToHsl(hex);
      if (!isDark) {
        const nextDark = autoTuneDark
          ? {
              h: parsedHsl.h,
              s: Math.max(20, Math.min(65, Math.round(parsedHsl.s * 0.9))),
              l: Math.max(48, Math.min(68, parsedHsl.l + 14)),
            }
          : dark;
        updateColors(parsedHsl, nextDark);
      } else {
        updateColors(light, parsedHsl);
      }
    },
    [isDark, autoTuneDark, light, dark, updateColors],
  );

  const applyPreset = useCallback(
    (preset: PalettePreset) => {
      updateColors(preset.light, preset.dark);
    },
    [updateColors],
  );

  const resetToDefault = useCallback(() => {
    setLight(DEFAULT_PRESET.light);
    setDark(DEFAULT_PRESET.dark);
    setIsCustom(false);
    try {
      localStorage.removeItem(STORAGE_KEY_LIGHT);
      localStorage.removeItem(STORAGE_KEY_DARK);
    } catch {
      // storage disabled
    }
  }, []);

  const copyCss = useCallback(async () => {
    const snippet = generateCssSnippet(light, dark);
    try {
      await navigator.clipboard.writeText(snippet);
      setCopiedCss(true);
      setTimeout(() => setCopiedCss(false), 2000);
    } catch {
      // fallback
    }
  }, [light, dark]);

  return {
    light,
    dark,
    activeHsl,
    activeHex,
    isCustom,
    autoTuneDark,
    isFloatingEnabled,
    copiedCss,
    contrast,
    glareAssessment,
    setAutoTuneDark,
    setFloatingEnabled,
    setHue,
    setSaturation,
    setLightness,
    setHex,
    applyPreset,
    resetToDefault,
    copyCss,
  };
}
