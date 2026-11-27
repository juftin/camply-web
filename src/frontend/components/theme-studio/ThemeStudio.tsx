import * as React from "react";
import {
  Check,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  Copy,
  Dices,
  Eye,
  Heart,
  Moon,
  Palette,
  PanelLeft,
  PanelRight,
  RotateCcw,
  Search,
  Sliders,
  Sparkles,
  Sun,
  Trash2,
  Type,
  X,
} from "lucide-react";
import { useTheme } from "@/hooks/use-theme";
import {
  applyMacroAdjustments,
  autoContrastForeground,
  buildCssExport,
  buildRuntimeStyleSheet,
  contrastRatio,
  DEFAULT_MACRO_ADJUSTMENTS,
  formatHslString,
  generateEarthyPalette,
  hexToHslString,
  hslStringToHex,
  parseHslString,
  type MacroAdjustments,
  type MapPinColors,
  type ThemePalette,
  type ThemeTokenKey,
  type ThemeTokens,
} from "./colorUtils";
import {
  QUICK_PRIMARY_SWATCHES,
  QUICK_SURFACE_MOODS,
  THEME_CATEGORIES,
  THEME_PRESETS,
  type QuickPrimarySwatch,
  type QuickSurfaceMood,
  type ThemeCategory,
} from "./presets";
import {
  BODY_FONT_OPTIONS,
  FONT_CATEGORIES,
  FONT_OPTIONS,
  FONT_PAIRINGS,
  resolveTypography,
  type FontCategory,
} from "./fonts";

const STORAGE_STATE_KEY = "camply-theme-studio-state-v1";
const STORAGE_SAVED_KEY = "camply-theme-studio-saved-v1";
const STYLE_ELEMENT_ID = "camply-theme-studio-style";
const FONT_LINK_ELEMENT_ID = "camply-theme-studio-font";

type StudioTab = "presets" | "customize" | "fonts" | "saved" | "export";
type DockSide = "right" | "left";

interface SavedTheme {
  id: string;
  name: string;
  createdAt: string;
  palette: ThemePalette;
}

interface PersistedState {
  activePresetId: string;
  palette: ThemePalette;
  macro: MacroAdjustments;
  isDirty: boolean;
  isOpen: boolean;
  dockSide: DockSide;
}

interface TokenGroup {
  label: string;
  tokens: Array<{
    key: ThemeTokenKey;
    label: string;
    contrastAgainst?: ThemeTokenKey;
  }>;
}

const TOKEN_GROUPS: readonly TokenGroup[] = [
  {
    label: "Brand & Actions",
    tokens: [
      { key: "primary", label: "Primary", contrastAgainst: "background" },
      {
        key: "primary-foreground",
        label: "Primary Text",
        contrastAgainst: "primary",
      },
      { key: "ring", label: "Focus Ring" },
      { key: "destructive", label: "Destructive" },
      {
        key: "destructive-foreground",
        label: "Destructive Text",
        contrastAgainst: "destructive",
      },
    ],
  },
  {
    label: "Surfaces & Ink",
    tokens: [
      { key: "background", label: "Page Background" },
      { key: "foreground", label: "Body Text", contrastAgainst: "background" },
      { key: "card", label: "Card Surface" },
      {
        key: "card-foreground",
        label: "Card Text",
        contrastAgainst: "card",
      },
      { key: "popover", label: "Popover Surface" },
      {
        key: "popover-foreground",
        label: "Popover Text",
        contrastAgainst: "popover",
      },
    ],
  },
  {
    label: "Subtle & Borders",
    tokens: [
      { key: "secondary", label: "Secondary Fill" },
      {
        key: "secondary-foreground",
        label: "Secondary Text",
        contrastAgainst: "secondary",
      },
      { key: "muted", label: "Muted Surface" },
      {
        key: "muted-foreground",
        label: "Muted Text",
        contrastAgainst: "background",
      },
      { key: "accent", label: "Accent / Hover" },
      {
        key: "accent-foreground",
        label: "Accent Text",
        contrastAgainst: "accent",
      },
      { key: "border", label: "Border" },
      { key: "input", label: "Input Border" },
    ],
  },
];

const RADIUS_OPTIONS = [
  { label: "Sharp", value: "0rem" },
  { label: "Topo", value: "0.25rem" },
  { label: "Crisp", value: "0.375rem" },
  { label: "Default", value: "0.5rem" },
  { label: "Soft", value: "0.75rem" },
  { label: "Round", value: "1rem" },
];

const DEFAULT_PRESET = THEME_PRESETS[0];
const STOCK_PRESET =
  THEME_PRESETS.find((preset) => preset.id === "stock-shadcn") ??
  THEME_PRESETS[THEME_PRESETS.length - 1];

function clonePalette(palette: ThemePalette): ThemePalette {
  return {
    light: { ...palette.light },
    dark: { ...palette.dark },
    radius: palette.radius,
    fontId: palette.fontId,
    customHeadingFontId: palette.customHeadingFontId,
    customBodyFontId: palette.customBodyFontId,
    headingTracking: palette.headingTracking,
    fontScale: palette.fontScale,
    mapPins: palette.mapPins ? { ...palette.mapPins } : undefined,
  };
}

function loadPersistedState(): PersistedState {
  try {
    const raw = window.localStorage.getItem(STORAGE_STATE_KEY);
    if (raw) {
      const parsed = JSON.parse(raw) as Partial<PersistedState>;
      if (parsed.palette?.light && parsed.palette?.dark) {
        return {
          activePresetId: parsed.activePresetId ?? DEFAULT_PRESET.id,
          palette: clonePalette(parsed.palette),
          macro: { ...DEFAULT_MACRO_ADJUSTMENTS, ...parsed.macro },
          isDirty: Boolean(parsed.isDirty),
          isOpen: Boolean(parsed.isOpen),
          dockSide: parsed.dockSide === "left" ? "left" : "right",
        };
      }
    }
  } catch {
    // Ignore storage failures and fall back to default preset.
  }

  return {
    activePresetId: DEFAULT_PRESET.id,
    palette: clonePalette(DEFAULT_PRESET.palette),
    macro: { ...DEFAULT_MACRO_ADJUSTMENTS },
    isDirty: false,
    isOpen: false,
    dockSide: "right",
  };
}

function loadSavedThemes(): SavedTheme[] {
  try {
    const raw = window.localStorage.getItem(STORAGE_SAVED_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw) as SavedTheme[];
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

function contrastBadge(ratio: number): {
  label: string;
  bg: string;
  color: string;
} {
  if (ratio >= 7) {
    return {
      label: `${ratio.toFixed(1)} AAA`,
      bg: "#14532d",
      color: "#bbf7d0",
    };
  }
  if (ratio >= 4.5) {
    return { label: `${ratio.toFixed(1)} AA`, bg: "#1e3a2f", color: "#86efac" };
  }
  if (ratio >= 3) {
    return {
      label: `${ratio.toFixed(1)} AA+`,
      bg: "#451a03",
      color: "#fde68a",
    };
  }
  return { label: `${ratio.toFixed(1)} Low`, bg: "#450a0a", color: "#fecaca" };
}

interface TokenEditorRowProps {
  tokenKey: ThemeTokenKey;
  label: string;
  value: string;
  contrastTargetValue?: string;
  onChange: (nextHsl: string) => void;
}

function TokenEditorRow({
  tokenKey,
  label,
  value,
  contrastTargetValue,
  onChange,
}: TokenEditorRowProps) {
  const [expanded, setExpanded] = React.useState(false);
  const hex = hslStringToHex(value);
  const [hexDraft, setHexDraft] = React.useState(hex);
  const hsl = parseHslString(value);

  React.useEffect(() => {
    setHexDraft(hex);
  }, [hex]);

  const ratio = contrastTargetValue
    ? contrastRatio(value, contrastTargetValue)
    : null;
  const badge = ratio !== null ? contrastBadge(ratio) : null;

  return (
    <div
      style={{
        borderBottom: "1px solid #262a30",
        padding: "7px 0",
      }}
    >
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          gap: "8px",
        }}
      >
        <button
          type="button"
          onClick={() => setExpanded((prev) => !prev)}
          style={{
            display: "flex",
            alignItems: "center",
            gap: "6px",
            background: "transparent",
            border: "none",
            color: "#e5e7eb",
            cursor: "pointer",
            padding: 0,
            textAlign: "left",
            minWidth: 0,
            flex: 1,
          }}
        >
          <ChevronDown
            size={13}
            style={{
              color: "#9ca3af",
              transform: expanded ? "rotate(0deg)" : "rotate(-90deg)",
              transition: "transform 120ms ease",
              flexShrink: 0,
            }}
          />
          <span
            style={{
              fontSize: "12px",
              fontWeight: 500,
              whiteSpace: "nowrap",
              overflow: "hidden",
              textOverflow: "ellipsis",
            }}
            title={`--${tokenKey}`}
          >
            {label}
          </span>
        </button>

        <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
          {badge && (
            <span
              style={{
                fontSize: "10px",
                fontWeight: 600,
                padding: "1px 5px",
                borderRadius: "4px",
                background: badge.bg,
                color: badge.color,
                fontVariantNumeric: "tabular-nums",
              }}
              title="WCAG contrast ratio"
            >
              {badge.label}
            </span>
          )}

          {contrastTargetValue &&
            tokenKey.endsWith("foreground") &&
            ratio !== null &&
            ratio < 4.5 && (
              <button
                type="button"
                onClick={() =>
                  onChange(autoContrastForeground(contrastTargetValue))
                }
                style={{
                  fontSize: "10px",
                  padding: "1px 5px",
                  borderRadius: "4px",
                  border: "1px solid #4b5563",
                  background: "#1f242b",
                  color: "#f3f4f6",
                  cursor: "pointer",
                }}
                title="Auto-pick readable foreground"
              >
                Fix
              </button>
            )}

          <input
            type="color"
            aria-label={`${label} color picker`}
            value={hex}
            onChange={(e) => {
              const converted = hexToHslString(e.target.value);
              if (converted) onChange(converted);
            }}
            style={{
              width: "24px",
              height: "24px",
              padding: 0,
              border: "1px solid #4b5563",
              borderRadius: "5px",
              background: "transparent",
              cursor: "pointer",
            }}
          />

          <input
            type="text"
            aria-label={`${label} hex`}
            value={hexDraft}
            onChange={(e) => {
              const next = e.target.value;
              setHexDraft(next);
              if (/^#?[0-9a-fA-F]{6}$/.test(next.trim())) {
                const converted = hexToHslString(next);
                if (converted) onChange(converted);
              }
            }}
            onBlur={() => setHexDraft(hex)}
            style={{
              width: "68px",
              fontSize: "11px",
              fontFamily: "ui-monospace, SFMono-Regular, Menlo, monospace",
              padding: "3px 6px",
              borderRadius: "5px",
              border: "1px solid #323741",
              background: "#0f1115",
              color: "#e5e7eb",
            }}
          />
        </div>
      </div>

      {expanded && (
        <div
          style={{
            marginTop: "8px",
            padding: "8px",
            borderRadius: "6px",
            background: "#0f1115",
            display: "grid",
            gap: "6px",
          }}
        >
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              fontSize: "10px",
              color: "#9ca3af",
              fontFamily: "ui-monospace, SFMono-Regular, Menlo, monospace",
            }}
          >
            <span>--{tokenKey}</span>
            <span>hsl({value})</span>
          </div>
          {(
            [
              { axis: "h", label: "H", max: 360, unit: "°" },
              { axis: "s", label: "S", max: 100, unit: "%" },
              { axis: "l", label: "L", max: 100, unit: "%" },
            ] as const
          ).map(({ axis, label: axisLabel, max, unit }) => (
            <label
              key={axis}
              style={{
                display: "grid",
                gridTemplateColumns: "18px 1fr 38px",
                alignItems: "center",
                gap: "8px",
                fontSize: "11px",
                color: "#d1d5db",
              }}
            >
              <span>{axisLabel}</span>
              <input
                type="range"
                min={0}
                max={max}
                step={axis === "h" ? 1 : 0.5}
                value={hsl[axis]}
                onChange={(e) => {
                  const nextVal = Number.parseFloat(e.target.value);
                  onChange(formatHslString({ ...hsl, [axis]: nextVal }));
                }}
                style={{ accentColor: "#e98f23", width: "100%" }}
              />
              <span
                style={{
                  textAlign: "right",
                  fontVariantNumeric: "tabular-nums",
                  fontSize: "10px",
                  color: "#9ca3af",
                }}
              >
                {Math.round(hsl[axis])}
                {unit}
              </span>
            </label>
          ))}
        </div>
      )}
    </div>
  );
}

/**
 * Floating live theme exploration and customization workbench for evaluating
 * new color schemes across every route of Camply.
 */
export function ThemeStudio() {
  const { userTheme, setTheme, toggleTheme } = useTheme();
  const [state, setState] = React.useState<PersistedState>(loadPersistedState);
  const [savedThemes, setSavedThemes] =
    React.useState<SavedTheme[]>(loadSavedThemes);
  const [activeTab, setActiveTab] = React.useState<StudioTab>("presets");
  const [selectedCategory, setSelectedCategory] = React.useState<
    ThemeCategory | "All"
  >("All");
  const [searchQuery, setSearchQuery] = React.useState("");
  const [selectedFontCategory, setSelectedFontCategory] = React.useState<
    FontCategory | "All"
  >("All");
  const [fontSearchQuery, setFontSearchQuery] = React.useState("");
  const [comparingStock, setComparingStock] = React.useState(false);
  const [saveName, setSaveName] = React.useState("");
  const [copiedTarget, setCopiedTarget] = React.useState<string | null>(null);
  const [importDraft, setImportDraft] = React.useState("");
  const [importError, setImportError] = React.useState<string | null>(null);

  const effectivePalette = React.useMemo<ThemePalette>(() => {
    if (comparingStock) {
      return STOCK_PRESET.palette;
    }
    return {
      ...state.palette,
      light: applyMacroAdjustments(state.palette.light, state.macro),
      dark: applyMacroAdjustments(state.palette.dark, state.macro),
    };
  }, [comparingStock, state.macro, state.palette]);

  const activePreset = React.useMemo(
    () =>
      THEME_PRESETS.find((preset) => preset.id === state.activePresetId) ??
      null,
    [state.activePresetId],
  );

  const activeTypography = React.useMemo(
    () =>
      resolveTypography(
        effectivePalette.fontId,
        effectivePalette.customHeadingFontId,
        effectivePalette.customBodyFontId,
      ),
    [
      effectivePalette.fontId,
      effectivePalette.customHeadingFontId,
      effectivePalette.customBodyFontId,
    ],
  );

  // Inject live CSS overrides into <head>.
  React.useEffect(() => {
    let styleEl = document.getElementById(
      STYLE_ELEMENT_ID,
    ) as HTMLStyleElement | null;
    if (!styleEl) {
      styleEl = document.createElement("style");
      styleEl.id = STYLE_ELEMENT_ID;
      document.head.appendChild(styleEl);
    }

    styleEl.textContent = buildRuntimeStyleSheet(
      effectivePalette,
      activeTypography.headingFont.stack,
      activeTypography.bodyFont.stack,
    );
  }, [effectivePalette, activeTypography]);

  // Dynamically load optional Google Font stylesheet only when a non-system font is picked.
  React.useEffect(() => {
    const existing = document.getElementById(
      FONT_LINK_ELEMENT_ID,
    ) as HTMLLinkElement | null;
    if (!activeTypography.googleFontsHref) {
      if (existing) existing.remove();
      return;
    }
    const linkEl = existing ?? document.createElement("link");
    linkEl.id = FONT_LINK_ELEMENT_ID;
    linkEl.rel = "stylesheet";
    linkEl.href = activeTypography.googleFontsHref;
    if (!existing) {
      document.head.appendChild(linkEl);
    }
  }, [activeTypography]);

  // Persist current workbench state.
  React.useEffect(() => {
    try {
      window.localStorage.setItem(STORAGE_STATE_KEY, JSON.stringify(state));
    } catch {
      // Ignore storage quota errors.
    }
  }, [state]);

  // Persist saved custom themes.
  React.useEffect(() => {
    try {
      window.localStorage.setItem(
        STORAGE_SAVED_KEY,
        JSON.stringify(savedThemes),
      );
    } catch {
      // Ignore storage quota errors.
    }
  }, [savedThemes]);

  const selectPreset = React.useCallback((presetId: string) => {
    const preset = THEME_PRESETS.find((item) => item.id === presetId);
    if (!preset) return;
    setComparingStock(false);
    setState((prev) => ({
      ...prev,
      activePresetId: preset.id,
      palette: {
        ...clonePalette(preset.palette),
        fontId: prev.palette.fontId,
        customHeadingFontId: prev.palette.customHeadingFontId,
        customBodyFontId: prev.palette.customBodyFontId,
        headingTracking: prev.palette.headingTracking,
        fontScale: prev.palette.fontScale,
      },
      macro: { ...DEFAULT_MACRO_ADJUSTMENTS },
      isDirty: false,
    }));
  }, []);

  const cyclePreset = React.useCallback((direction: -1 | 1) => {
    setComparingStock(false);
    setState((prev) => {
      const currentIdx = THEME_PRESETS.findIndex(
        (preset) => preset.id === prev.activePresetId,
      );
      const startIdx = currentIdx === -1 ? 0 : currentIdx;
      const nextIdx =
        (startIdx + direction + THEME_PRESETS.length) % THEME_PRESETS.length;
      const nextPreset = THEME_PRESETS[nextIdx];
      return {
        ...prev,
        activePresetId: nextPreset.id,
        palette: {
          ...clonePalette(nextPreset.palette),
          fontId: prev.palette.fontId,
          customHeadingFontId: prev.palette.customHeadingFontId,
          customBodyFontId: prev.palette.customBodyFontId,
          headingTracking: prev.palette.headingTracking,
          fontScale: prev.palette.fontScale,
        },
        macro: { ...DEFAULT_MACRO_ADJUSTMENTS },
        isDirty: false,
      };
    });
  }, []);

  // Keyboard shortcuts: [ and ] cycle presets when not typing in an input.
  React.useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      const target = event.target as HTMLElement | null;
      if (
        target &&
        (target.tagName === "INPUT" ||
          target.tagName === "TEXTAREA" ||
          target.tagName === "SELECT" ||
          target.isContentEditable)
      ) {
        return;
      }
      if (event.metaKey || event.ctrlKey || event.altKey) return;
      if (event.key === "[") {
        cyclePreset(-1);
      } else if (event.key === "]") {
        cyclePreset(1);
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [cyclePreset]);

  const updateToken = (
    mode: "light" | "dark",
    key: ThemeTokenKey,
    nextValue: string,
  ) => {
    setComparingStock(false);
    setState((prev) => {
      // Bake any active macro adjustments before editing an individual token
      const baseLight = applyMacroAdjustments(prev.palette.light, prev.macro);
      const baseDark = applyMacroAdjustments(prev.palette.dark, prev.macro);
      const nextPalette: ThemePalette = {
        ...prev.palette,
        light:
          mode === "light" ? { ...baseLight, [key]: nextValue } : baseLight,
        dark: mode === "dark" ? { ...baseDark, [key]: nextValue } : baseDark,
      };
      return {
        ...prev,
        palette: nextPalette,
        macro: { ...DEFAULT_MACRO_ADJUSTMENTS },
        isDirty: true,
      };
    });
  };

  const updateMapPin = (pinKey: keyof MapPinColors, hexValue: string) => {
    setComparingStock(false);
    setState((prev) => ({
      ...prev,
      palette: {
        ...prev.palette,
        mapPins: {
          camp: prev.palette.mapPins?.camp ?? "#0d5159",
          area: prev.palette.mapPins?.area ?? "#be6f29",
          group: prev.palette.mapPins?.group ?? "#273b3e",
          [pinKey]: hexValue,
        },
      },
      isDirty: true,
    }));
  };

  const applyQuickPrimary = (swatch: QuickPrimarySwatch) => {
    setComparingStock(false);
    setState((prev) => {
      const baseLight = applyMacroAdjustments(prev.palette.light, prev.macro);
      const baseDark = applyMacroAdjustments(prev.palette.dark, prev.macro);
      return {
        ...prev,
        palette: {
          ...prev.palette,
          light: {
            ...baseLight,
            primary: swatch.lightPrimary,
            "primary-foreground": swatch.lightPrimaryFg,
            ring: swatch.lightPrimary,
          },
          dark: {
            ...baseDark,
            primary: swatch.darkPrimary,
            "primary-foreground": swatch.darkPrimaryFg,
            ring: swatch.darkPrimary,
          },
          mapPins: {
            camp: swatch.hex,
            area: prev.palette.mapPins?.area ?? "#be6f29",
            group: prev.palette.mapPins?.group ?? "#273b3e",
          },
        },
        macro: { ...DEFAULT_MACRO_ADJUSTMENTS },
        isDirty: true,
      };
    });
  };

  const applyQuickSurface = (mood: QuickSurfaceMood) => {
    setComparingStock(false);
    setState((prev) => {
      const baseLight = applyMacroAdjustments(prev.palette.light, prev.macro);
      const baseDark = applyMacroAdjustments(prev.palette.dark, prev.macro);
      return {
        ...prev,
        palette: {
          ...prev.palette,
          light: { ...baseLight, ...mood.light },
          dark: { ...baseDark, ...mood.dark },
        },
        macro: { ...DEFAULT_MACRO_ADJUSTMENTS },
        isDirty: true,
      };
    });
  };

  const updateMacro = (patch: Partial<MacroAdjustments>) => {
    setComparingStock(false);
    setState((prev) => ({
      ...prev,
      macro: { ...prev.macro, ...patch },
      isDirty: true,
    }));
  };

  const updateRadius = (radius: string) => {
    setComparingStock(false);
    setState((prev) => ({
      ...prev,
      palette: { ...prev.palette, radius },
      isDirty: true,
    }));
  };

  const updateFont = (fontId: string) => {
    setComparingStock(false);
    setState((prev) => ({
      ...prev,
      palette: {
        ...prev.palette,
        fontId,
        customHeadingFontId: undefined,
        customBodyFontId: undefined,
      },
      isDirty: true,
    }));
  };

  const updateCustomFonts = (
    patch: Partial<
      Pick<
        ThemePalette,
        | "customHeadingFontId"
        | "customBodyFontId"
        | "headingTracking"
        | "fontScale"
      >
    >,
  ) => {
    setComparingStock(false);
    setState((prev) => ({
      ...prev,
      palette: { ...prev.palette, ...patch },
      isDirty: true,
    }));
  };

  const handleRandomize = () => {
    setComparingStock(false);
    const randomPalette = generateEarthyPalette();
    setState((prev) => ({
      ...prev,
      activePresetId: "custom-random",
      palette: randomPalette,
      macro: { ...DEFAULT_MACRO_ADJUSTMENTS },
      isDirty: true,
    }));
  };

  const handleResetToPreset = () => {
    if (activePreset) {
      selectPreset(activePreset.id);
    } else {
      selectPreset(DEFAULT_PRESET.id);
    }
  };

  const handleSaveCurrent = (event: React.FormEvent) => {
    event.preventDefault();
    const trimmed = saveName.trim();
    const label =
      trimmed || `${activePreset?.name ?? "Custom"} #${savedThemes.length + 1}`;
    const entry: SavedTheme = {
      id: `saved-${Date.now()}`,
      name: label,
      createdAt: new Date().toISOString(),
      palette: clonePalette(effectivePalette),
    };
    setSavedThemes((prev) => [entry, ...prev]);
    setSaveName("");
  };

  const handleLoadSaved = (saved: SavedTheme) => {
    setComparingStock(false);
    setState((prev) => ({
      ...prev,
      activePresetId: saved.id,
      palette: clonePalette(saved.palette),
      macro: { ...DEFAULT_MACRO_ADJUSTMENTS },
      isDirty: false,
    }));
  };

  const handleDeleteSaved = (id: string) => {
    setSavedThemes((prev) => prev.filter((item) => item.id !== id));
  };

  const currentLabel = comparingStock
    ? "Comparing: Stock Default"
    : (activePreset?.name ??
      savedThemes.find((item) => item.id === state.activePresetId)?.name ??
      "Custom Earthy");

  const cssExportText = React.useMemo(
    () =>
      buildCssExport(effectivePalette, currentLabel, {
        label: activeTypography.label,
        headingStack: activeTypography.headingFont.stack,
        bodyStack: activeTypography.bodyFont.stack,
        googleFontsHref: activeTypography.googleFontsHref,
      }),
    [effectivePalette, currentLabel, activeTypography],
  );

  const jsonExportText = React.useMemo(
    () =>
      JSON.stringify(
        {
          name: currentLabel,
          typography: {
            label: activeTypography.label,
            headingFont: activeTypography.headingFont.name,
            bodyFont: activeTypography.bodyFont.name,
            googleFontsHref: activeTypography.googleFontsHref,
          },
          palette: effectivePalette,
          swatches: {
            lightPrimary: hslStringToHex(effectivePalette.light.primary),
            lightBackground: hslStringToHex(effectivePalette.light.background),
            lightAccent: hslStringToHex(effectivePalette.light.accent),
            darkPrimary: hslStringToHex(effectivePalette.dark.primary),
            darkBackground: hslStringToHex(effectivePalette.dark.background),
          },
        },
        null,
        2,
      ),
    [currentLabel, effectivePalette, activeTypography],
  );

  const copyText = async (text: string, label: string) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopiedTarget(label);
      window.setTimeout(() => setCopiedTarget(null), 1800);
    } catch {
      setCopiedTarget("failed");
      window.setTimeout(() => setCopiedTarget(null), 1800);
    }
  };

  const handleImportJson = () => {
    try {
      const parsed = JSON.parse(importDraft) as {
        palette?: ThemePalette;
        light?: ThemeTokens;
        dark?: ThemeTokens;
        radius?: string;
        fontId?: string;
        mapPins?: MapPinColors;
      };
      const imported = parsed.palette ?? (parsed as unknown as ThemePalette);
      if (!imported?.light?.primary || !imported?.dark?.primary) {
        throw new Error("Missing light/dark tokens.");
      }
      setComparingStock(false);
      setState((prev) => ({
        ...prev,
        activePresetId: "imported-custom",
        palette: {
          light: { ...DEFAULT_PRESET.palette.light, ...imported.light },
          dark: { ...DEFAULT_PRESET.palette.dark, ...imported.dark },
          radius: imported.radius ?? "0.5rem",
          fontId: imported.fontId ?? "system",
          mapPins: imported.mapPins,
        },
        macro: { ...DEFAULT_MACRO_ADJUSTMENTS },
        isDirty: true,
      }));
      setImportError(null);
      setImportDraft("");
    } catch (err) {
      setImportError(
        err instanceof Error ? err.message : "Invalid JSON format.",
      );
    }
  };

  const normalizedQuery = searchQuery.trim().toLowerCase();
  const filteredPresets = THEME_PRESETS.filter((preset) => {
    const matchesCategory =
      selectedCategory === "All" || preset.category === selectedCategory;
    if (!matchesCategory) return false;
    if (!normalizedQuery) return true;
    return (
      preset.name.toLowerCase().includes(normalizedQuery) ||
      preset.tagline.toLowerCase().includes(normalizedQuery) ||
      preset.category.toLowerCase().includes(normalizedQuery)
    );
  });

  const normalizedFontQuery = fontSearchQuery.trim().toLowerCase();
  const filteredFontPairings = FONT_PAIRINGS.filter((pairing) => {
    const matchesCategory =
      selectedFontCategory === "All" ||
      pairing.category === selectedFontCategory;
    if (!matchesCategory) return false;
    if (!normalizedFontQuery) return true;
    return (
      pairing.name.toLowerCase().includes(normalizedFontQuery) ||
      pairing.vibe.toLowerCase().includes(normalizedFontQuery) ||
      pairing.category.toLowerCase().includes(normalizedFontQuery)
    );
  });

  const activeModeTokens =
    userTheme === "dark" ? effectivePalette.dark : effectivePalette.light;

  const pillSwatches = [
    hslStringToHex(activeModeTokens.primary),
    hslStringToHex(activeModeTokens.accent),
    hslStringToHex(activeModeTokens.background),
  ];

  // Compact floating pill bar when collapsed
  if (!state.isOpen) {
    return (
      <div
        data-testid="theme-studio-launcher"
        style={{
          position: "fixed",
          bottom: "16px",
          right: "16px",
          zIndex: 9999,
          display: "flex",
          alignItems: "center",
          gap: "4px",
          padding: "5px",
          borderRadius: "9999px",
          background: "#14171c",
          color: "#f3f4f6",
          border: "1px solid #2e343e",
          boxShadow: "0 12px 32px rgba(0, 0, 0, 0.36)",
          fontFamily: "system-ui, -apple-system, sans-serif",
        }}
      >
        <button
          type="button"
          onClick={() => cyclePreset(-1)}
          aria-label="Previous theme preset"
          title="Previous theme ([)"
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            width: "28px",
            height: "28px",
            borderRadius: "9999px",
            border: "none",
            background: "transparent",
            color: "#cbd5e1",
            cursor: "pointer",
          }}
        >
          <ChevronLeft size={16} />
        </button>

        <button
          type="button"
          onClick={() => setState((prev) => ({ ...prev, isOpen: true }))}
          aria-label="Open Theme Studio"
          style={{
            display: "flex",
            alignItems: "center",
            gap: "8px",
            padding: "4px 10px",
            borderRadius: "9999px",
            border: "none",
            background: "#1f242d",
            color: "#f8fafc",
            cursor: "pointer",
            fontSize: "12px",
            fontWeight: 600,
          }}
        >
          <span style={{ display: "inline-flex", gap: "3px" }}>
            {pillSwatches.map((color, index) => (
              <span
                key={index}
                style={{
                  width: "10px",
                  height: "10px",
                  borderRadius: "9999px",
                  background: color,
                  border: "1px solid rgba(255,255,255,0.28)",
                }}
              />
            ))}
          </span>
          <span>{currentLabel}</span>
          {state.isDirty && !comparingStock && (
            <span
              style={{
                width: "6px",
                height: "6px",
                borderRadius: "9999px",
                background: "#e98f23",
              }}
              title="Customized"
            />
          )}
          <Palette size={14} style={{ color: "#94a3b8" }} />
        </button>

        <button
          type="button"
          onClick={() => cyclePreset(1)}
          aria-label="Next theme preset"
          title="Next theme (])"
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            width: "28px",
            height: "28px",
            borderRadius: "9999px",
            border: "none",
            background: "transparent",
            color: "#cbd5e1",
            cursor: "pointer",
          }}
        >
          <ChevronRight size={16} />
        </button>

        <button
          type="button"
          onClick={toggleTheme}
          aria-label="Toggle light or dark mode"
          title={`Switch to ${userTheme === "dark" ? "light" : "dark"} mode`}
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            width: "28px",
            height: "28px",
            borderRadius: "9999px",
            border: "none",
            background: "#1f242d",
            color: "#e2e8f0",
            cursor: "pointer",
          }}
        >
          {userTheme === "dark" ? <Sun size={14} /> : <Moon size={14} />}
        </button>
      </div>
    );
  }

  return (
    <aside
      data-testid="theme-studio-drawer"
      aria-label="Camply Theme Studio"
      style={{
        position: "fixed",
        top: "12px",
        bottom: "12px",
        [state.dockSide]: "12px",
        width: "min(390px, calc(100vw - 24px))",
        zIndex: 9999,
        display: "flex",
        flexDirection: "column",
        borderRadius: "14px",
        background: "#14171c",
        color: "#f3f4f6",
        border: "1px solid #2b313b",
        boxShadow: "0 20px 50px rgba(0, 0, 0, 0.45)",
        fontFamily: "system-ui, -apple-system, sans-serif",
        overflow: "hidden",
      }}
    >
      {/* Top Studio Header */}
      <div
        style={{
          padding: "12px 14px",
          borderBottom: "1px solid #262a30",
          background: "#181c22",
        }}
      >
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            gap: "8px",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            <div
              style={{
                width: "28px",
                height: "28px",
                borderRadius: "8px",
                background: "linear-gradient(135deg, #0d5159, #e98f23)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                flexShrink: 0,
              }}
            >
              <Palette size={15} color="#fff" />
            </div>
            <div>
              <div
                style={{
                  fontSize: "13px",
                  fontWeight: 700,
                  lineHeight: 1.2,
                  color: "#f9fafb",
                }}
              >
                Camply Theme Studio
              </div>
              <div
                style={{
                  fontSize: "11px",
                  color: "#9ca3af",
                  display: "flex",
                  alignItems: "center",
                  gap: "5px",
                }}
              >
                <span>{currentLabel}</span>
                {state.isDirty && !comparingStock && (
                  <span
                    style={{
                      fontSize: "10px",
                      padding: "0 5px",
                      borderRadius: "9999px",
                      background: "#3b2a14",
                      color: "#fbbf24",
                    }}
                  >
                    Edited
                  </span>
                )}
              </div>
            </div>
          </div>

          <div style={{ display: "flex", alignItems: "center", gap: "4px" }}>
            <button
              type="button"
              onClick={toggleTheme}
              title={`Switch to ${userTheme === "dark" ? "Light" : "Dark"} mode`}
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: "4px",
                padding: "5px 8px",
                borderRadius: "7px",
                border: "1px solid #323741",
                background: "#1f242d",
                color: "#f3f4f6",
                fontSize: "11px",
                fontWeight: 600,
                cursor: "pointer",
              }}
            >
              {userTheme === "dark" ? <Moon size={12} /> : <Sun size={12} />}
              <span>{userTheme === "dark" ? "Dark" : "Light"}</span>
            </button>

            <button
              type="button"
              onClick={() =>
                setState((prev) => ({
                  ...prev,
                  dockSide: prev.dockSide === "right" ? "left" : "right",
                }))
              }
              title={`Dock to ${state.dockSide === "right" ? "left" : "right"} side`}
              aria-label="Switch dock side"
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                width: "28px",
                height: "28px",
                borderRadius: "7px",
                border: "1px solid #323741",
                background: "#1f242d",
                color: "#cbd5e1",
                cursor: "pointer",
              }}
            >
              {state.dockSide === "right" ? (
                <PanelLeft size={14} />
              ) : (
                <PanelRight size={14} />
              )}
            </button>

            <button
              type="button"
              onClick={() => setState((prev) => ({ ...prev, isOpen: false }))}
              title="Minimize to floating bar"
              aria-label="Minimize Theme Studio"
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                width: "28px",
                height: "28px",
                borderRadius: "7px",
                border: "1px solid #323741",
                background: "#1f242d",
                color: "#cbd5e1",
                cursor: "pointer",
              }}
            >
              <X size={14} />
            </button>
          </div>
        </div>

        {/* Quick action strip */}
        <div
          style={{
            marginTop: "10px",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            gap: "6px",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: "4px" }}>
            <button
              type="button"
              onClick={() => cyclePreset(-1)}
              title="Previous preset ([)"
              style={{
                padding: "4px 6px",
                borderRadius: "6px",
                border: "1px solid #2e343e",
                background: "#14171c",
                color: "#d1d5db",
                cursor: "pointer",
                display: "inline-flex",
                alignItems: "center",
              }}
            >
              <ChevronLeft size={13} />
            </button>
            <button
              type="button"
              onClick={() => cyclePreset(1)}
              title="Next preset (])"
              style={{
                padding: "4px 6px",
                borderRadius: "6px",
                border: "1px solid #2e343e",
                background: "#14171c",
                color: "#d1d5db",
                cursor: "pointer",
                display: "inline-flex",
                alignItems: "center",
              }}
            >
              <ChevronRight size={13} />
            </button>
            <button
              type="button"
              onClick={handleRandomize}
              title="Generate a random earthy outdoor palette"
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: "4px",
                padding: "4px 8px",
                borderRadius: "6px",
                border: "1px solid #2e343e",
                background: "#14171c",
                color: "#e5e7eb",
                fontSize: "11px",
                fontWeight: 500,
                cursor: "pointer",
              }}
            >
              <Dices size={12} />
              <span>Shuffle</span>
            </button>
          </div>

          <div style={{ display: "flex", alignItems: "center", gap: "5px" }}>
            <button
              type="button"
              onClick={() => setComparingStock((prev) => !prev)}
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: "4px",
                padding: "4px 8px",
                borderRadius: "6px",
                border: comparingStock
                  ? "1px solid #60a5fa"
                  : "1px solid #2e343e",
                background: comparingStock ? "#1e3a5f" : "#14171c",
                color: comparingStock ? "#dbeafe" : "#cbd5e1",
                fontSize: "11px",
                fontWeight: 500,
                cursor: "pointer",
              }}
              title="Toggle between your active theme and the original stock Shadcn blue"
            >
              <Eye size={12} />
              <span>{comparingStock ? "Stock On" : "A/B Stock"}</span>
            </button>

            <a
              href={`${import.meta.env.BASE_URL}dev/preview`}
              style={{
                padding: "4px 8px",
                borderRadius: "6px",
                border: "1px solid #2e343e",
                background: "#14171c",
                color: "#cbd5e1",
                fontSize: "11px",
                fontWeight: 500,
                textDecoration: "none",
              }}
              title="Open the Design System Preview page to see all UI components at once"
            >
              Catalog ↗
            </a>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div
        role="tablist"
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(5, 1fr)",
          borderBottom: "1px solid #262a30",
          background: "#14171c",
          padding: "4px",
          gap: "3px",
        }}
      >
        {(
          [
            { id: "presets", label: "Presets", icon: Sparkles },
            { id: "customize", label: "Colors", icon: Sliders },
            { id: "fonts", label: "Fonts", icon: Type },
            {
              id: "saved",
              label:
                savedThemes.length > 0
                  ? `Saved (${savedThemes.length})`
                  : "Saved",
              icon: Heart,
            },
            { id: "export", label: "Export", icon: Copy },
          ] as const
        ).map(({ id, label, icon: Icon }) => {
          const isActive = activeTab === id;
          return (
            <button
              key={id}
              type="button"
              role="tab"
              aria-selected={isActive}
              onClick={() => setActiveTab(id)}
              style={{
                display: "inline-flex",
                alignItems: "center",
                justifyContent: "center",
                gap: "4px",
                padding: "6px 3px",
                borderRadius: "7px",
                border: "none",
                background: isActive ? "#262c36" : "transparent",
                color: isActive ? "#ffffff" : "#9ca3af",
                fontSize: "11px",
                fontWeight: isActive ? 600 : 500,
                cursor: "pointer",
                whiteSpace: "nowrap",
              }}
            >
              <Icon size={11} />
              <span>{label}</span>
            </button>
          );
        })}
      </div>

      {/* Scrollable Body */}
      <div
        style={{
          flex: 1,
          overflowY: "auto",
          padding: "12px 14px",
        }}
      >
        {/* ── PRESETS TAB ── */}
        {activeTab === "presets" && (
          <div style={{ display: "grid", gap: "10px" }}>
            {/* Search & count */}
            <div style={{ position: "relative" }}>
              <Search
                size={13}
                style={{
                  position: "absolute",
                  left: "9px",
                  top: "50%",
                  transform: "translateY(-50%)",
                  color: "#9ca3af",
                  pointerEvents: "none",
                }}
              />
              <input
                type="text"
                aria-label="Filter theme presets"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder={`Search ${THEME_PRESETS.length} themes (e.g. pine, warm, retro, blue)...`}
                style={{
                  width: "100%",
                  fontSize: "11.5px",
                  padding: "6px 28px 6px 28px",
                  borderRadius: "7px",
                  border: "1px solid #2e343e",
                  background: "#0f1115",
                  color: "#f3f4f6",
                }}
              />
              {searchQuery && (
                <button
                  type="button"
                  onClick={() => setSearchQuery("")}
                  aria-label="Clear preset search"
                  style={{
                    position: "absolute",
                    right: "6px",
                    top: "50%",
                    transform: "translateY(-50%)",
                    background: "transparent",
                    border: "none",
                    color: "#9ca3af",
                    cursor: "pointer",
                    display: "flex",
                    padding: "2px",
                  }}
                >
                  <X size={12} />
                </button>
              )}
            </div>

            <div style={{ display: "flex", flexWrap: "wrap", gap: "5px" }}>
              {(["All", ...THEME_CATEGORIES] as const).map((cat) => {
                const active = selectedCategory === cat;
                const count =
                  cat === "All"
                    ? THEME_PRESETS.length
                    : THEME_PRESETS.filter((p) => p.category === cat).length;
                return (
                  <button
                    key={cat}
                    type="button"
                    onClick={() => setSelectedCategory(cat)}
                    style={{
                      fontSize: "10.5px",
                      padding: "3px 8px",
                      borderRadius: "9999px",
                      border: active
                        ? "1px solid #e98f23"
                        : "1px solid #2e343e",
                      background: active ? "#332411" : "#1a1e25",
                      color: active ? "#fcd34d" : "#cbd5e1",
                      cursor: "pointer",
                      fontWeight: active ? 600 : 500,
                    }}
                  >
                    {cat} ({count})
                  </button>
                );
              })}
            </div>

            {filteredPresets.length === 0 && (
              <div
                style={{
                  padding: "18px 12px",
                  textAlign: "center",
                  fontSize: "12px",
                  color: "#9ca3af",
                  borderRadius: "8px",
                  border: "1px dashed #2e343e",
                }}
              >
                No themes matched &ldquo;{searchQuery}&rdquo;.
              </div>
            )}

            <div style={{ display: "grid", gap: "8px" }}>
              {filteredPresets.map((preset) => {
                const isSelected =
                  !comparingStock && state.activePresetId === preset.id;
                const previewTokens =
                  userTheme === "dark"
                    ? preset.palette.dark
                    : preset.palette.light;
                const bgHex = hslStringToHex(previewTokens.background);
                const cardHex = hslStringToHex(previewTokens.card);
                const fgHex = hslStringToHex(previewTokens.foreground);
                const primaryHex = hslStringToHex(previewTokens.primary);
                const primaryFgHex = hslStringToHex(
                  previewTokens["primary-foreground"],
                );
                const accentHex = hslStringToHex(previewTokens.accent);
                const borderHex = hslStringToHex(previewTokens.border);

                return (
                  <button
                    key={preset.id}
                    type="button"
                    onClick={() => selectPreset(preset.id)}
                    style={{
                      textAlign: "left",
                      padding: "10px",
                      borderRadius: "10px",
                      border: isSelected
                        ? "1.5px solid #e98f23"
                        : "1px solid #2a2f38",
                      background: isSelected ? "#1e232c" : "#181b21",
                      color: "#f3f4f6",
                      cursor: "pointer",
                      display: "grid",
                      gap: "8px",
                    }}
                  >
                    <div
                      style={{
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "space-between",
                        gap: "8px",
                      }}
                    >
                      <div>
                        <div
                          style={{
                            fontSize: "12.5px",
                            fontWeight: 650,
                            display: "flex",
                            alignItems: "center",
                            gap: "6px",
                          }}
                        >
                          <span>{preset.name}</span>
                          {isSelected && (
                            <Check size={13} style={{ color: "#f59e0b" }} />
                          )}
                        </div>
                        <div
                          style={{
                            fontSize: "11px",
                            color: "#9ca3af",
                            marginTop: "2px",
                            lineHeight: 1.35,
                          }}
                        >
                          {preset.tagline}
                        </div>
                      </div>
                    </div>

                    {/* Mini live preview strip in active light/dark mode */}
                    <div
                      style={{
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "space-between",
                        padding: "7px 9px",
                        borderRadius: preset.palette.radius,
                        background: bgHex,
                        border: `1px solid ${borderHex}`,
                        gap: "8px",
                      }}
                    >
                      <div
                        style={{
                          display: "flex",
                          alignItems: "center",
                          gap: "6px",
                        }}
                      >
                        <span
                          style={{
                            display: "inline-block",
                            padding: "2px 8px",
                            borderRadius: preset.palette.radius,
                            background: primaryHex,
                            color: primaryFgHex,
                            fontSize: "10px",
                            fontWeight: 700,
                          }}
                        >
                          Scan
                        </span>
                        <span
                          style={{
                            display: "inline-block",
                            padding: "2px 7px",
                            borderRadius: preset.palette.radius,
                            background: cardHex,
                            color: fgHex,
                            border: `1px solid ${borderHex}`,
                            fontSize: "10px",
                            fontWeight: 600,
                          }}
                        >
                          Card
                        </span>
                        <span
                          style={{
                            width: "14px",
                            height: "14px",
                            borderRadius: "9999px",
                            background: accentHex,
                            border: `1px solid ${borderHex}`,
                            display: "inline-block",
                          }}
                        />
                      </div>

                      <div style={{ display: "flex", gap: "4px" }}>
                        {preset.swatches.map((swatch, idx) => (
                          <span
                            key={idx}
                            style={{
                              width: "12px",
                              height: "12px",
                              borderRadius: "3px",
                              background: swatch,
                              border: "1px solid rgba(128,128,128,0.35)",
                            }}
                          />
                        ))}
                      </div>
                    </div>
                  </button>
                );
              })}
            </div>
          </div>
        )}

        {/* ── CUSTOMIZE / TUNE TAB ── */}
        {activeTab === "customize" && (
          <div style={{ display: "grid", gap: "14px" }}>
            {/* Editing mode switcher */}
            <div
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                gap: "8px",
                padding: "8px 10px",
                borderRadius: "8px",
                background: "#1a1e25",
                border: "1px solid #2b313b",
              }}
            >
              <span style={{ fontSize: "11.5px", color: "#cbd5e1" }}>
                Editing palette:
              </span>
              <div style={{ display: "flex", gap: "4px" }}>
                {(["light", "dark"] as const).map((mode) => (
                  <button
                    key={mode}
                    type="button"
                    onClick={() => setTheme(mode)}
                    style={{
                      display: "inline-flex",
                      alignItems: "center",
                      gap: "4px",
                      padding: "4px 9px",
                      borderRadius: "6px",
                      border:
                        userTheme === mode
                          ? "1px solid #e98f23"
                          : "1px solid #323741",
                      background: userTheme === mode ? "#332411" : "#14171c",
                      color: userTheme === mode ? "#fcd34d" : "#9ca3af",
                      fontSize: "11px",
                      fontWeight: 600,
                      cursor: "pointer",
                      textTransform: "capitalize",
                    }}
                  >
                    {mode === "light" ? <Sun size={11} /> : <Moon size={11} />}
                    {mode}
                  </button>
                ))}
              </div>
            </div>

            {/* Mix & Match Remixers */}
            <section
              style={{
                padding: "10px",
                borderRadius: "9px",
                background: "#181c22",
                border: "1px solid #282d36",
                display: "grid",
                gap: "10px",
              }}
            >
              <div
                style={{
                  fontSize: "11.5px",
                  fontWeight: 700,
                  color: "#e5e7eb",
                  textTransform: "uppercase",
                  letterSpacing: "0.04em",
                }}
              >
                Mix & Match Remix
              </div>

              <div style={{ display: "grid", gap: "6px" }}>
                <span style={{ fontSize: "11px", color: "#9ca3af" }}>
                  Swap primary accent (updates light & dark):
                </span>
                <div
                  style={{
                    display: "grid",
                    gridTemplateColumns: "repeat(7, 1fr)",
                    gap: "5px",
                  }}
                >
                  {QUICK_PRIMARY_SWATCHES.map((swatch) => (
                    <button
                      key={swatch.id}
                      type="button"
                      onClick={() => applyQuickPrimary(swatch)}
                      title={swatch.name}
                      aria-label={`Use ${swatch.name} primary`}
                      style={{
                        height: "24px",
                        borderRadius: "6px",
                        border: "1px solid rgba(255,255,255,0.22)",
                        background: swatch.hex,
                        cursor: "pointer",
                      }}
                    />
                  ))}
                </div>
              </div>

              <div style={{ display: "grid", gap: "6px" }}>
                <span style={{ fontSize: "11px", color: "#9ca3af" }}>
                  Swap paper / surface mood:
                </span>
                <div
                  style={{
                    display: "grid",
                    gridTemplateColumns: "repeat(3, 1fr)",
                    gap: "5px",
                  }}
                >
                  {QUICK_SURFACE_MOODS.map((mood) => (
                    <button
                      key={mood.id}
                      type="button"
                      onClick={() => applyQuickSurface(mood)}
                      style={{
                        display: "inline-flex",
                        alignItems: "center",
                        gap: "6px",
                        padding: "5px 7px",
                        borderRadius: "6px",
                        border: "1px solid #2e343e",
                        background: "#14171c",
                        color: "#e5e7eb",
                        fontSize: "10.5px",
                        fontWeight: 500,
                        cursor: "pointer",
                      }}
                    >
                      <span
                        style={{
                          width: "11px",
                          height: "11px",
                          borderRadius: "3px",
                          background: mood.swatch,
                          border: "1px solid rgba(128,128,128,0.45)",
                          flexShrink: 0,
                        }}
                      />
                      <span
                        style={{
                          overflow: "hidden",
                          textOverflow: "ellipsis",
                          whiteSpace: "nowrap",
                        }}
                      >
                        {mood.name}
                      </span>
                    </button>
                  ))}
                </div>
              </div>
            </section>

            {/* Quick Harmonizer */}
            <section
              style={{
                padding: "10px",
                borderRadius: "9px",
                background: "#181c22",
                border: "1px solid #282d36",
                display: "grid",
                gap: "10px",
              }}
            >
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                }}
              >
                <span
                  style={{
                    fontSize: "11.5px",
                    fontWeight: 700,
                    color: "#e5e7eb",
                    textTransform: "uppercase",
                    letterSpacing: "0.04em",
                  }}
                >
                  Quick Harmonizer
                </span>
                <button
                  type="button"
                  onClick={handleResetToPreset}
                  style={{
                    display: "inline-flex",
                    alignItems: "center",
                    gap: "4px",
                    fontSize: "11px",
                    padding: "2px 7px",
                    borderRadius: "5px",
                    border: "1px solid #323741",
                    background: "#14171c",
                    color: "#cbd5e1",
                    cursor: "pointer",
                  }}
                >
                  <RotateCcw size={11} />
                  Reset
                </button>
              </div>

              <label
                style={{ display: "grid", gap: "4px", fontSize: "11.5px" }}
              >
                <div
                  style={{ display: "flex", justifyContent: "space-between" }}
                >
                  <span style={{ color: "#d1d5db" }}>Hue Shift</span>
                  <span style={{ color: "#9ca3af" }}>
                    {state.macro.hueShift > 0
                      ? `+${state.macro.hueShift}°`
                      : `${state.macro.hueShift}°`}
                  </span>
                </div>
                <input
                  type="range"
                  min={-180}
                  max={180}
                  step={2}
                  value={state.macro.hueShift}
                  onChange={(e) =>
                    updateMacro({ hueShift: Number(e.target.value) })
                  }
                  style={{ accentColor: "#e98f23", width: "100%" }}
                />
              </label>

              <label
                style={{ display: "grid", gap: "4px", fontSize: "11.5px" }}
              >
                <div
                  style={{ display: "flex", justifyContent: "space-between" }}
                >
                  <span style={{ color: "#d1d5db" }}>
                    Vibrancy / Saturation
                  </span>
                  <span style={{ color: "#9ca3af" }}>
                    {state.macro.saturationScale}%
                  </span>
                </div>
                <input
                  type="range"
                  min={40}
                  max={145}
                  step={5}
                  value={state.macro.saturationScale}
                  onChange={(e) =>
                    updateMacro({ saturationScale: Number(e.target.value) })
                  }
                  style={{ accentColor: "#e98f23", width: "100%" }}
                />
              </label>

              <label
                style={{ display: "grid", gap: "4px", fontSize: "11.5px" }}
              >
                <div
                  style={{ display: "flex", justifyContent: "space-between" }}
                >
                  <span style={{ color: "#d1d5db" }}>Surface Warmth</span>
                  <span style={{ color: "#9ca3af" }}>
                    {state.macro.warmth === 0
                      ? "Preset"
                      : state.macro.warmth > 0
                        ? `Warm +${state.macro.warmth}`
                        : `Cool ${state.macro.warmth}`}
                  </span>
                </div>
                <input
                  type="range"
                  min={-100}
                  max={100}
                  step={5}
                  value={state.macro.warmth}
                  onChange={(e) =>
                    updateMacro({ warmth: Number(e.target.value) })
                  }
                  style={{ accentColor: "#e98f23", width: "100%" }}
                />
              </label>

              <label
                style={{ display: "grid", gap: "4px", fontSize: "11.5px" }}
              >
                <div
                  style={{ display: "flex", justifyContent: "space-between" }}
                >
                  <span style={{ color: "#d1d5db" }}>
                    Card & Border Separation
                  </span>
                  <span style={{ color: "#9ca3af" }}>
                    {state.macro.cardContrast === 0
                      ? "Preset"
                      : state.macro.cardContrast > 0
                        ? `Crisp +${state.macro.cardContrast}`
                        : `Flat ${state.macro.cardContrast}`}
                  </span>
                </div>
                <input
                  type="range"
                  min={-100}
                  max={100}
                  step={5}
                  value={state.macro.cardContrast}
                  onChange={(e) =>
                    updateMacro({ cardContrast: Number(e.target.value) })
                  }
                  style={{ accentColor: "#e98f23", width: "100%" }}
                />
              </label>
            </section>

            {/* Border Radius */}
            <section
              style={{
                padding: "10px",
                borderRadius: "9px",
                background: "#181c22",
                border: "1px solid #282d36",
                display: "grid",
                gap: "8px",
              }}
            >
              <div
                style={{
                  fontSize: "11.5px",
                  fontWeight: 700,
                  color: "#e5e7eb",
                  textTransform: "uppercase",
                  letterSpacing: "0.04em",
                }}
              >
                Corner Radius ({effectivePalette.radius})
              </div>
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "repeat(3, 1fr)",
                  gap: "5px",
                }}
              >
                {RADIUS_OPTIONS.map((opt) => {
                  const active = effectivePalette.radius === opt.value;
                  return (
                    <button
                      key={opt.value}
                      type="button"
                      onClick={() => updateRadius(opt.value)}
                      style={{
                        padding: "5px 6px",
                        fontSize: "11px",
                        borderRadius: "6px",
                        border: active
                          ? "1px solid #e98f23"
                          : "1px solid #2e343e",
                        background: active ? "#332411" : "#14171c",
                        color: active ? "#fcd34d" : "#cbd5e1",
                        cursor: "pointer",
                        fontWeight: active ? 600 : 500,
                      }}
                    >
                      {opt.label}
                    </button>
                  );
                })}
              </div>
            </section>

            {/* Individual Color Tokens */}
            {TOKEN_GROUPS.map((group) => (
              <section
                key={group.label}
                style={{
                  padding: "10px",
                  borderRadius: "9px",
                  background: "#181c22",
                  border: "1px solid #282d36",
                }}
              >
                <div
                  style={{
                    fontSize: "11.5px",
                    fontWeight: 700,
                    color: "#e5e7eb",
                    textTransform: "uppercase",
                    letterSpacing: "0.04em",
                    marginBottom: "6px",
                  }}
                >
                  {group.label} ({userTheme})
                </div>
                {group.tokens.map((item) => (
                  <TokenEditorRow
                    key={`${userTheme}-${item.key}`}
                    tokenKey={item.key}
                    label={item.label}
                    value={activeModeTokens[item.key]}
                    contrastTargetValue={
                      item.contrastAgainst
                        ? activeModeTokens[item.contrastAgainst]
                        : undefined
                    }
                    onChange={(nextHsl) =>
                      updateToken(userTheme, item.key, nextHsl)
                    }
                  />
                ))}
              </section>
            ))}

            {/* Map Pins */}
            <section
              style={{
                padding: "10px",
                borderRadius: "9px",
                background: "#181c22",
                border: "1px solid #282d36",
                display: "grid",
                gap: "8px",
              }}
            >
              <div
                style={{
                  fontSize: "11.5px",
                  fontWeight: 700,
                  color: "#e5e7eb",
                  textTransform: "uppercase",
                  letterSpacing: "0.04em",
                }}
              >
                Explore Map Pins
              </div>
              {(
                [
                  { key: "camp", label: "Campground Pin", fallback: "#0d5159" },
                  {
                    key: "area",
                    label: "Recreation Area Pin",
                    fallback: "#be6f29",
                  },
                  { key: "group", label: "Cluster Pin", fallback: "#273b3e" },
                ] as const
              ).map(({ key, label, fallback }) => {
                const value = effectivePalette.mapPins?.[key] ?? fallback;
                return (
                  <div
                    key={key}
                    style={{
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "space-between",
                      fontSize: "12px",
                    }}
                  >
                    <span style={{ color: "#e5e7eb" }}>{label}</span>
                    <div
                      style={{
                        display: "flex",
                        alignItems: "center",
                        gap: "6px",
                      }}
                    >
                      <input
                        type="color"
                        aria-label={label}
                        value={value}
                        onChange={(e) => updateMapPin(key, e.target.value)}
                        style={{
                          width: "24px",
                          height: "24px",
                          padding: 0,
                          border: "1px solid #4b5563",
                          borderRadius: "5px",
                          background: "transparent",
                          cursor: "pointer",
                        }}
                      />
                      <span
                        style={{
                          fontFamily:
                            "ui-monospace, SFMono-Regular, Menlo, monospace",
                          fontSize: "11px",
                          color: "#9ca3af",
                        }}
                      >
                        {value}
                      </span>
                    </div>
                  </div>
                );
              })}
            </section>
          </div>
        )}

        {/* ── FONTS TAB ── */}
        {activeTab === "fonts" && (
          <div style={{ display: "grid", gap: "12px" }}>
            {/* Active font + Custom Mix & Match */}
            <section
              style={{
                padding: "10px",
                borderRadius: "9px",
                background: "#181c22",
                border: "1px solid #282d36",
                display: "grid",
                gap: "10px",
              }}
            >
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  gap: "8px",
                }}
              >
                <span
                  style={{
                    fontSize: "11.5px",
                    fontWeight: 700,
                    color: "#e5e7eb",
                    textTransform: "uppercase",
                    letterSpacing: "0.04em",
                  }}
                >
                  Mix & Match Fonts
                </span>
                <button
                  type="button"
                  onClick={() => {
                    updateFont("system");
                    updateCustomFonts({
                      headingTracking: "0em",
                      fontScale: 100,
                    });
                  }}
                  style={{
                    display: "inline-flex",
                    alignItems: "center",
                    gap: "4px",
                    fontSize: "11px",
                    padding: "2px 7px",
                    borderRadius: "5px",
                    border: "1px solid #323741",
                    background: "#14171c",
                    color: "#cbd5e1",
                    cursor: "pointer",
                  }}
                >
                  <RotateCcw size={11} />
                  System
                </button>
              </div>

              <label style={{ display: "grid", gap: "4px", fontSize: "11px" }}>
                <span style={{ color: "#9ca3af" }}>
                  Headings ({FONT_OPTIONS.length} options)
                </span>
                <select
                  aria-label="Heading font family"
                  value={activeTypography.headingFont.id}
                  onChange={(e) =>
                    updateCustomFonts({
                      customHeadingFontId: e.target.value,
                    })
                  }
                  style={{
                    width: "100%",
                    fontSize: "12px",
                    padding: "6px 8px",
                    borderRadius: "6px",
                    border: "1px solid #323741",
                    background: "#0f1115",
                    color: "#f3f4f6",
                  }}
                >
                  {FONT_OPTIONS.map((font) => (
                    <option key={font.id} value={font.id}>
                      {font.name} ({font.style})
                    </option>
                  ))}
                </select>
              </label>

              <label style={{ display: "grid", gap: "4px", fontSize: "11px" }}>
                <span style={{ color: "#9ca3af" }}>
                  Body Copy ({BODY_FONT_OPTIONS.length} options)
                </span>
                <select
                  aria-label="Body font family"
                  value={activeTypography.bodyFont.id}
                  onChange={(e) =>
                    updateCustomFonts({
                      customBodyFontId: e.target.value,
                    })
                  }
                  style={{
                    width: "100%",
                    fontSize: "12px",
                    padding: "6px 8px",
                    borderRadius: "6px",
                    border: "1px solid #323741",
                    background: "#0f1115",
                    color: "#f3f4f6",
                  }}
                >
                  {BODY_FONT_OPTIONS.map((font) => (
                    <option key={font.id} value={font.id}>
                      {font.name} ({font.style})
                    </option>
                  ))}
                </select>
              </label>

              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "1fr 1fr",
                  gap: "8px",
                }}
              >
                <div style={{ display: "grid", gap: "4px" }}>
                  <span style={{ fontSize: "10.5px", color: "#9ca3af" }}>
                    Heading Tracking
                  </span>
                  <div
                    style={{
                      display: "grid",
                      gridTemplateColumns: "repeat(3, 1fr)",
                      gap: "4px",
                    }}
                  >
                    {(
                      [
                        { label: "Tight", value: "-0.025em" },
                        { label: "Normal", value: "0em" },
                        { label: "Airy", value: "0.02em" },
                      ] as const
                    ).map((opt) => {
                      const active =
                        (effectivePalette.headingTracking ?? "0em") ===
                        opt.value;
                      return (
                        <button
                          key={opt.value}
                          type="button"
                          onClick={() =>
                            updateCustomFonts({ headingTracking: opt.value })
                          }
                          style={{
                            padding: "4px 2px",
                            fontSize: "10.5px",
                            borderRadius: "5px",
                            border: active
                              ? "1px solid #e98f23"
                              : "1px solid #2e343e",
                            background: active ? "#332411" : "#14171c",
                            color: active ? "#fcd34d" : "#cbd5e1",
                            cursor: "pointer",
                          }}
                        >
                          {opt.label}
                        </button>
                      );
                    })}
                  </div>
                </div>

                <div style={{ display: "grid", gap: "4px" }}>
                  <span style={{ fontSize: "10.5px", color: "#9ca3af" }}>
                    Text Scale
                  </span>
                  <div
                    style={{
                      display: "grid",
                      gridTemplateColumns: "repeat(3, 1fr)",
                      gap: "4px",
                    }}
                  >
                    {(
                      [
                        { label: "94%", value: 94 },
                        { label: "100%", value: 100 },
                        { label: "106%", value: 106 },
                      ] as const
                    ).map((opt) => {
                      const active =
                        (effectivePalette.fontScale ?? 100) === opt.value;
                      return (
                        <button
                          key={opt.value}
                          type="button"
                          onClick={() =>
                            updateCustomFonts({ fontScale: opt.value })
                          }
                          style={{
                            padding: "4px 2px",
                            fontSize: "10.5px",
                            borderRadius: "5px",
                            border: active
                              ? "1px solid #e98f23"
                              : "1px solid #2e343e",
                            background: active ? "#332411" : "#14171c",
                            color: active ? "#fcd34d" : "#cbd5e1",
                            cursor: "pointer",
                          }}
                        >
                          {opt.label}
                        </button>
                      );
                    })}
                  </div>
                </div>
              </div>
            </section>

            {/* Search & filter curated pairings */}
            <div style={{ position: "relative" }}>
              <Search
                size={13}
                style={{
                  position: "absolute",
                  left: "9px",
                  top: "50%",
                  transform: "translateY(-50%)",
                  color: "#9ca3af",
                  pointerEvents: "none",
                }}
              />
              <input
                type="text"
                aria-label="Filter font pairings"
                value={fontSearchQuery}
                onChange={(e) => setFontSearchQuery(e.target.value)}
                placeholder={`Search ${FONT_PAIRINGS.length} curated pairings (serif, slab, mono)...`}
                style={{
                  width: "100%",
                  fontSize: "11.5px",
                  padding: "6px 28px 6px 28px",
                  borderRadius: "7px",
                  border: "1px solid #2e343e",
                  background: "#0f1115",
                  color: "#f3f4f6",
                }}
              />
              {fontSearchQuery && (
                <button
                  type="button"
                  onClick={() => setFontSearchQuery("")}
                  aria-label="Clear font search"
                  style={{
                    position: "absolute",
                    right: "6px",
                    top: "50%",
                    transform: "translateY(-50%)",
                    background: "transparent",
                    border: "none",
                    color: "#9ca3af",
                    cursor: "pointer",
                    display: "flex",
                    padding: "2px",
                  }}
                >
                  <X size={12} />
                </button>
              )}
            </div>

            <div style={{ display: "flex", flexWrap: "wrap", gap: "5px" }}>
              {(["All", ...FONT_CATEGORIES] as const).map((cat) => {
                const active = selectedFontCategory === cat;
                const count =
                  cat === "All"
                    ? FONT_PAIRINGS.length
                    : FONT_PAIRINGS.filter((p) => p.category === cat).length;
                return (
                  <button
                    key={cat}
                    type="button"
                    onClick={() => setSelectedFontCategory(cat)}
                    style={{
                      fontSize: "10.5px",
                      padding: "3px 8px",
                      borderRadius: "9999px",
                      border: active
                        ? "1px solid #e98f23"
                        : "1px solid #2e343e",
                      background: active ? "#332411" : "#1a1e25",
                      color: active ? "#fcd34d" : "#cbd5e1",
                      cursor: "pointer",
                      fontWeight: active ? 600 : 500,
                    }}
                  >
                    {cat} ({count})
                  </button>
                );
              })}
            </div>

            <div style={{ display: "grid", gap: "6px" }}>
              {filteredFontPairings.map((pairing) => {
                const active =
                  !effectivePalette.customHeadingFontId &&
                  !effectivePalette.customBodyFontId &&
                  effectivePalette.fontId === pairing.id;
                return (
                  <button
                    key={pairing.id}
                    type="button"
                    onClick={() => updateFont(pairing.id)}
                    style={{
                      textAlign: "left",
                      padding: "8px 10px",
                      borderRadius: "8px",
                      border: active
                        ? "1.5px solid #e98f23"
                        : "1px solid #2a2f38",
                      background: active ? "#272018" : "#181b21",
                      color: "#f3f4f6",
                      cursor: "pointer",
                      display: "grid",
                      gap: "3px",
                    }}
                  >
                    <div
                      style={{
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "space-between",
                        gap: "6px",
                      }}
                    >
                      <span style={{ fontSize: "12px", fontWeight: 650 }}>
                        {pairing.name}
                      </span>
                      <span
                        style={{
                          fontSize: "10px",
                          color: active ? "#fcd34d" : "#9ca3af",
                        }}
                      >
                        {pairing.category}
                      </span>
                    </div>
                    <span style={{ fontSize: "11px", color: "#9ca3af" }}>
                      {pairing.vibe}
                    </span>
                  </button>
                );
              })}
            </div>
          </div>
        )}

        {/* ── SAVED TAB ── */}
        {activeTab === "saved" && (
          <div style={{ display: "grid", gap: "12px" }}>
            <form
              onSubmit={handleSaveCurrent}
              style={{
                display: "flex",
                gap: "6px",
                padding: "10px",
                borderRadius: "9px",
                background: "#181c22",
                border: "1px solid #282d36",
              }}
            >
              <input
                type="text"
                value={saveName}
                onChange={(e) => setSaveName(e.target.value)}
                placeholder="Name your contender..."
                style={{
                  flex: 1,
                  fontSize: "12px",
                  padding: "6px 9px",
                  borderRadius: "6px",
                  border: "1px solid #323741",
                  background: "#0f1115",
                  color: "#f3f4f6",
                }}
              />
              <button
                type="submit"
                style={{
                  padding: "6px 12px",
                  borderRadius: "6px",
                  border: "none",
                  background: "#e98f23",
                  color: "#111827",
                  fontSize: "12px",
                  fontWeight: 700,
                  cursor: "pointer",
                }}
              >
                Save
              </button>
            </form>

            {savedThemes.length === 0 ? (
              <div
                style={{
                  padding: "24px 16px",
                  textAlign: "center",
                  borderRadius: "9px",
                  border: "1px dashed #2e343e",
                  color: "#9ca3af",
                  fontSize: "12px",
                  lineHeight: 1.5,
                }}
              >
                Bookmark 2–3 contenders here so you can rapidly click between
                them across Home, Explore, and Dashboard.
              </div>
            ) : (
              <div style={{ display: "grid", gap: "8px" }}>
                {savedThemes.map((saved) => {
                  const isSelected = state.activePresetId === saved.id;
                  const swatches = [
                    hslStringToHex(saved.palette.light.primary),
                    hslStringToHex(saved.palette.light.background),
                    hslStringToHex(saved.palette.dark.primary),
                    hslStringToHex(saved.palette.dark.background),
                  ];
                  return (
                    <div
                      key={saved.id}
                      style={{
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "space-between",
                        gap: "8px",
                        padding: "9px 10px",
                        borderRadius: "9px",
                        border: isSelected
                          ? "1.5px solid #e98f23"
                          : "1px solid #282d36",
                        background: "#181c22",
                      }}
                    >
                      <button
                        type="button"
                        onClick={() => handleLoadSaved(saved)}
                        style={{
                          flex: 1,
                          background: "transparent",
                          border: "none",
                          color: "#f3f4f6",
                          textAlign: "left",
                          cursor: "pointer",
                          padding: 0,
                          display: "grid",
                          gap: "5px",
                        }}
                      >
                        <span style={{ fontSize: "12.5px", fontWeight: 600 }}>
                          {saved.name}
                        </span>
                        <span style={{ display: "flex", gap: "4px" }}>
                          {swatches.map((hex, i) => (
                            <span
                              key={i}
                              style={{
                                width: "16px",
                                height: "10px",
                                borderRadius: "3px",
                                background: hex,
                                border: "1px solid rgba(255,255,255,0.2)",
                              }}
                            />
                          ))}
                        </span>
                      </button>
                      <button
                        type="button"
                        onClick={() => handleDeleteSaved(saved.id)}
                        aria-label={`Delete ${saved.name}`}
                        style={{
                          padding: "5px",
                          borderRadius: "6px",
                          border: "1px solid #323741",
                          background: "#14171c",
                          color: "#f87171",
                          cursor: "pointer",
                        }}
                      >
                        <Trash2 size={13} />
                      </button>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        )}

        {/* ── EXPORT / IMPORT TAB ── */}
        {activeTab === "export" && (
          <div style={{ display: "grid", gap: "12px" }}>
            <div
              style={{
                fontSize: "12px",
                color: "#cbd5e1",
                lineHeight: 1.45,
              }}
            >
              When you find a palette you love, copy the CSS or JSON below and
              paste it back so we can apply it cleanly across the app (and
              remove this studio tool).
            </div>

            <div style={{ display: "flex", gap: "6px" }}>
              <button
                type="button"
                onClick={() => void copyText(cssExportText, "css")}
                style={{
                  flex: 1,
                  display: "inline-flex",
                  alignItems: "center",
                  justifyContent: "center",
                  gap: "6px",
                  padding: "8px 10px",
                  borderRadius: "7px",
                  border: "none",
                  background: "#e98f23",
                  color: "#111827",
                  fontSize: "12px",
                  fontWeight: 700,
                  cursor: "pointer",
                }}
              >
                {copiedTarget === "css" ? (
                  <Check size={14} />
                ) : (
                  <Copy size={14} />
                )}
                <span>
                  {copiedTarget === "css" ? "Copied CSS!" : "Copy index.css"}
                </span>
              </button>

              <button
                type="button"
                onClick={() => void copyText(jsonExportText, "json")}
                style={{
                  flex: 1,
                  display: "inline-flex",
                  alignItems: "center",
                  justifyContent: "center",
                  gap: "6px",
                  padding: "8px 10px",
                  borderRadius: "7px",
                  border: "1px solid #323741",
                  background: "#1f242d",
                  color: "#f3f4f6",
                  fontSize: "12px",
                  fontWeight: 600,
                  cursor: "pointer",
                }}
              >
                {copiedTarget === "json" ? (
                  <Check size={14} />
                ) : (
                  <Copy size={14} />
                )}
                <span>
                  {copiedTarget === "json" ? "Copied JSON!" : "Copy JSON"}
                </span>
              </button>
            </div>

            <pre
              style={{
                margin: 0,
                padding: "10px",
                borderRadius: "8px",
                background: "#0d0f13",
                border: "1px solid #262a30",
                color: "#d1d5db",
                fontSize: "10.5px",
                lineHeight: 1.45,
                overflowX: "auto",
                maxHeight: "250px",
                fontFamily: "ui-monospace, SFMono-Regular, Menlo, monospace",
              }}
            >
              {cssExportText}
            </pre>

            <div
              style={{
                display: "grid",
                gap: "6px",
                paddingTop: "8px",
                borderTop: "1px solid #262a30",
              }}
            >
              <span
                style={{
                  fontSize: "11.5px",
                  fontWeight: 600,
                  color: "#e5e7eb",
                }}
              >
                Import Theme JSON
              </span>
              <textarea
                rows={4}
                value={importDraft}
                onChange={(e) => {
                  setImportDraft(e.target.value);
                  setImportError(null);
                }}
                placeholder="Paste exported JSON here..."
                style={{
                  width: "100%",
                  fontSize: "11px",
                  fontFamily: "ui-monospace, SFMono-Regular, Menlo, monospace",
                  padding: "8px",
                  borderRadius: "7px",
                  border: "1px solid #323741",
                  background: "#0f1115",
                  color: "#e5e7eb",
                  resize: "vertical",
                }}
              />
              {importError && (
                <div style={{ fontSize: "11px", color: "#f87171" }}>
                  {importError}
                </div>
              )}
              <button
                type="button"
                onClick={handleImportJson}
                disabled={!importDraft.trim()}
                style={{
                  padding: "6px 10px",
                  borderRadius: "7px",
                  border: "1px solid #323741",
                  background: importDraft.trim() ? "#262c36" : "#181b21",
                  color: importDraft.trim() ? "#f3f4f6" : "#6b7280",
                  fontSize: "11.5px",
                  fontWeight: 600,
                  cursor: importDraft.trim() ? "pointer" : "not-allowed",
                }}
              >
                Load JSON Palette
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Footer tip */}
      <div
        style={{
          padding: "8px 14px",
          borderTop: "1px solid #262a30",
          background: "#181c22",
          fontSize: "10.5px",
          color: "#9ca3af",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
        }}
      >
        <span>Tip: press [ and ] to flip themes</span>
        <span>Temporary local tool</span>
      </div>
    </aside>
  );
}
