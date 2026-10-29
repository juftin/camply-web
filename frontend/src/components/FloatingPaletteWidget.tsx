import React, { useState } from "react";
import { Palette, X } from "lucide-react";
import { usePaletteStudio } from "@/hooks/usePaletteStudio";
import { PaletteStudio } from "@/components/PaletteStudio";

export const FloatingPaletteWidget: React.FC = () => {
  const { isFloatingEnabled, activeHex } = usePaletteStudio();
  const [isOpen, setIsOpen] = useState(false);

  // If floating is not enabled by user preference, do not render in DOM
  if (!isFloatingEnabled) {
    return null;
  }

  return (
    <div className="fixed bottom-6 right-6 z-50 flex flex-col items-end">
      {isOpen && (
        <div className="mb-3 w-[360px] sm:w-[480px] max-h-[85vh] overflow-y-auto rounded-xl shadow-2xl border bg-background animate-in fade-in slide-in-from-bottom-4 duration-200">
          <PaletteStudio compact onClose={() => setIsOpen(false)} />
        </div>
      )}

      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-2 px-3.5 py-2.5 rounded-full shadow-xl border bg-card/95 backdrop-blur hover:bg-muted text-xs font-semibold text-foreground transition-all duration-200 hover:scale-105 active:scale-95"
        style={{
          boxShadow: `0 4px 20px -2px ${activeHex}40`,
        }}
        aria-label="Open Theme Palette Studio"
      >
        <span
          className="w-3.5 h-3.5 rounded-full shrink-0 shadow-sm border border-black/10"
          style={{ backgroundColor: activeHex }}
        />
        <Palette className="h-4 w-4" />
        <span>Theme Studio</span>
        {isOpen && <X className="h-3.5 w-3.5 text-muted-foreground ml-1" />}
      </button>
    </div>
  );
};
