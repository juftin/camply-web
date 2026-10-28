import React from "react";
import {
  Palette,
  Check,
  Copy,
  RotateCcw,
  AlertTriangle,
  Sun,
  Moon,
} from "lucide-react";
import { PRESET_PALETTES, type PalettePreset } from "@/lib/color-utils";
import { usePaletteStudio } from "@/hooks/usePaletteStudio";
import { useTheme } from "@/hooks/use-theme";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";

interface PaletteStudioProps {
  compact?: boolean;
  onClose?: () => void;
}

export const PaletteStudio: React.FC<PaletteStudioProps> = ({
  compact = false,
  onClose,
}) => {
  const { userTheme, toggleTheme } = useTheme();
  const isDark = userTheme === "dark";

  const {
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
  } = usePaletteStudio();

  return (
    <Card className="border shadow-lg">
      <CardHeader className="pb-3 border-b bg-muted/20">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <div
              className="w-7 h-7 rounded-md flex items-center justify-center text-primary-foreground shadow-sm transition-colors duration-200"
              style={{ backgroundColor: activeHex }}
            >
              <Palette className="h-4 w-4" />
            </div>
            <div>
              <CardTitle className="text-lg font-bold flex items-center gap-2">
                Theme Palette Studio
                {isCustom && (
                  <Badge variant="outline" className="text-xs font-normal">
                    Customized
                  </Badge>
                )}
              </CardTitle>
              <CardDescription className="text-xs">
                Interactive real-time theme experimenter &amp; optical glare
                tuner
              </CardDescription>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <Button
              size="sm"
              variant="outline"
              onClick={toggleTheme}
              className="h-8 px-2.5 text-xs flex items-center gap-1.5"
            >
              {isDark ? (
                <>
                  <Moon className="h-3.5 w-3.5" /> Dark Mode
                </>
              ) : (
                <>
                  <Sun className="h-3.5 w-3.5" /> Light Mode
                </>
              )}
            </Button>
            <Button
              size="sm"
              variant="outline"
              onClick={copyCss}
              className="h-8 px-2.5 text-xs flex items-center gap-1.5"
            >
              {copiedCss ? (
                <>
                  <Check className="h-3.5 w-3.5 text-emerald-500" /> Copied!
                </>
              ) : (
                <>
                  <Copy className="h-3.5 w-3.5" /> Copy CSS
                </>
              )}
            </Button>
            {isCustom && (
              <Button
                size="sm"
                variant="ghost"
                onClick={resetToDefault}
                className="h-8 px-2 text-xs text-muted-foreground hover:text-foreground"
                title="Reset to default theme"
              >
                <RotateCcw className="h-3.5 w-3.5 mr-1" />
                Reset
              </Button>
            )}
            {onClose && (
              <Button
                size="sm"
                variant="ghost"
                onClick={onClose}
                className="h-8 w-8 p-0"
              >
                ✕
              </Button>
            )}
          </div>
        </div>
      </CardHeader>

      <CardContent className="pt-4 space-y-6">
        {/* Presets Row */}
        <div>
          <Label className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2 block">
            Curated Palettes
          </Label>
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-2">
            {PRESET_PALETTES.map((preset: PalettePreset) => {
              const presetColor = isDark ? preset.dark : preset.light;
              const isSelected =
                activeHsl.h === presetColor.h &&
                Math.abs(activeHsl.s - presetColor.s) <= 2 &&
                Math.abs(activeHsl.l - presetColor.l) <= 2;

              return (
                <button
                  key={preset.id}
                  type="button"
                  onClick={() => applyPreset(preset)}
                  className={`flex items-center gap-2 p-2 rounded-lg border text-left transition-all text-xs hover:border-primary/50 hover:bg-muted/40 ${
                    isSelected
                      ? "ring-2 ring-primary border-transparent bg-muted/60 font-semibold"
                      : "bg-card"
                  }`}
                >
                  <span
                    className="w-4 h-4 rounded-full shrink-0 border border-black/10 shadow-sm"
                    style={{
                      backgroundColor: `hsl(${presetColor.h}, ${presetColor.s}%, ${presetColor.l}%)`,
                    }}
                  />
                  <div className="truncate flex-1">
                    <div className="truncate">{preset.name}</div>
                  </div>
                  {preset.badge && (
                    <span className="text-[10px] px-1 py-0.5 rounded bg-primary/10 text-primary font-medium shrink-0">
                      {preset.badge}
                    </span>
                  )}
                </button>
              );
            })}
          </div>
        </div>

        {/* Sliders & Color Picker */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 pt-2 border-t">
          {/* Column 1: Color Picker & Hex */}
          <div className="space-y-3">
            <Label className="text-xs font-semibold text-muted-foreground uppercase tracking-wider block">
              Color Picker
            </Label>
            <div className="flex items-center gap-3">
              <div className="relative">
                <input
                  type="color"
                  value={activeHex}
                  onChange={(e) => setHex(e.target.value)}
                  className="w-12 h-12 rounded-lg cursor-pointer border border-border p-1 bg-card shadow-sm"
                  aria-label="Choose color"
                />
              </div>
              <div className="flex-1 space-y-1">
                <div className="text-sm font-mono font-bold">
                  {activeHex.toUpperCase()}
                </div>
                <div className="text-xs text-muted-foreground font-mono">
                  hsl({activeHsl.h}, {activeHsl.s}%, {activeHsl.l}%)
                </div>
              </div>
            </div>

            <div className="pt-2">
              <div className="flex items-center space-x-2">
                <Switch
                  id="auto-tune-dark"
                  checked={autoTuneDark}
                  onCheckedChange={setAutoTuneDark}
                />
                <Label
                  htmlFor="auto-tune-dark"
                  className="text-xs cursor-pointer"
                >
                  Auto-tune dark mode glare
                </Label>
              </div>
              <p className="text-[11px] text-muted-foreground mt-1">
                Automatically lowers dark-mode saturation to stop neon optical
                vibration.
              </p>
            </div>
          </div>

          {/* Column 2: Sliders */}
          <div className="md:col-span-2 space-y-4">
            {/* Hue */}
            <div className="space-y-1.5">
              <div className="flex justify-between text-xs">
                <Label htmlFor="slider-hue">Hue (Angle)</Label>
                <span className="font-mono text-muted-foreground">
                  {activeHsl.h}°
                </span>
              </div>
              <input
                id="slider-hue"
                type="range"
                min="0"
                max="360"
                value={activeHsl.h}
                onChange={(e) => setHue(Number(e.target.value))}
                className="w-full h-2 rounded-lg appearance-none cursor-pointer"
                style={{
                  background:
                    "linear-gradient(to right, #ef4444, #eab308, #22c55e, #06b6d4, #3b82f6, #a855f7, #ef4444)",
                }}
              />
            </div>

            {/* Saturation */}
            <div className="space-y-1.5">
              <div className="flex justify-between text-xs">
                <Label htmlFor="slider-sat">Saturation (Vibrancy)</Label>
                <span className="font-mono text-muted-foreground">
                  {activeHsl.s}%
                </span>
              </div>
              <input
                id="slider-sat"
                type="range"
                min="0"
                max="100"
                value={activeHsl.s}
                onChange={(e) => setSaturation(Number(e.target.value))}
                className="w-full h-2 rounded-lg appearance-none cursor-pointer bg-muted"
              />
              <div className="flex justify-between text-[10px] text-muted-foreground">
                <span>0% (Muted Slate)</span>
                <span className="text-primary font-medium">
                  40-50% (Recommended)
                </span>
                <span className="text-amber-500 font-medium">
                  80%+ (High Glare)
                </span>
              </div>
            </div>

            {/* Lightness */}
            <div className="space-y-1.5">
              <div className="flex justify-between text-xs">
                <Label htmlFor="slider-light">Lightness</Label>
                <span className="font-mono text-muted-foreground">
                  {activeHsl.l}%
                </span>
              </div>
              <input
                id="slider-light"
                type="range"
                min="15"
                max="85"
                value={activeHsl.l}
                onChange={(e) => setLightness(Number(e.target.value))}
                className="w-full h-2 rounded-lg appearance-none cursor-pointer bg-muted"
              />
            </div>
          </div>
        </div>

        {/* Glare Risk Alert */}
        {glareAssessment.hasRisk && (
          <div className="flex items-start gap-2 p-3 rounded-lg border border-amber-500/30 bg-amber-500/10 text-amber-600 dark:text-amber-400 text-xs">
            <AlertTriangle className="h-4 w-4 shrink-0 mt-0.5" />
            <div>
              <span className="font-semibold">Optical Glare Warning: </span>
              {glareAssessment.message}
            </div>
          </div>
        )}

        {/* Accessibility & Floating Options */}
        <div className="flex flex-wrap items-center justify-between gap-4 p-3 rounded-lg bg-muted/40 border text-xs">
          <div className="flex items-center gap-4">
            <div>
              <span className="text-muted-foreground mr-1">WCAG Contrast:</span>
              <span className="font-bold">{contrast.ratio}:1</span>
            </div>
            <div>
              <Badge
                variant={contrast.pass ? "default" : "destructive"}
                className="text-[10px] py-0 px-2"
              >
                {contrast.scoreLabel}
              </Badge>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <Switch
              id="enable-floating"
              checked={isFloatingEnabled}
              onCheckedChange={setFloatingEnabled}
            />
            <Label htmlFor="enable-floating" className="cursor-pointer text-xs">
              Show floating tool across all pages
            </Label>
          </div>
        </div>

        {/* Component Sandbox */}
        {!compact && (
          <div className="pt-2 border-t space-y-3">
            <Label className="text-xs font-semibold text-muted-foreground uppercase tracking-wider block">
              Live Component Preview
            </Label>
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4 p-4 rounded-lg border bg-card/60">
              {/* Button */}
              <div className="space-y-1.5 text-center">
                <span className="text-[11px] text-muted-foreground block">
                  Primary Button
                </span>
                <Button size="sm" className="w-full">
                  Primary Action
                </Button>
              </div>

              {/* Outline Button */}
              <div className="space-y-1.5 text-center">
                <span className="text-[11px] text-muted-foreground block">
                  Outline Button
                </span>
                <Button size="sm" variant="outline" className="w-full">
                  Outline
                </Button>
              </div>

              {/* Badges */}
              <div className="space-y-1.5 text-center">
                <span className="text-[11px] text-muted-foreground block">
                  Status Badges
                </span>
                <div className="flex items-center justify-center gap-1.5 pt-1">
                  <Badge variant="default">Active</Badge>
                  <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-primary/10 text-primary">
                    Available
                  </span>
                </div>
              </div>

              {/* Switch */}
              <div className="space-y-1.5 text-center">
                <span className="text-[11px] text-muted-foreground block">
                  Toggle Switch
                </span>
                <div className="flex items-center justify-center gap-2 pt-1">
                  <Switch checked={true} />
                  <span className="text-xs font-medium">On</span>
                </div>
              </div>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
};
