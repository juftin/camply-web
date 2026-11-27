export type FontCategory =
  | "Outdoor & Heritage"
  | "Editorial Serif"
  | "Humanist Sans"
  | "Modern Geometric"
  | "Topo & Mono"
  | "Default";

export interface FontOption {
  id: string;
  name: string;
  style: "serif" | "slab" | "sans" | "display" | "mono" | "system";
  stack: string | null;
  googleFamilyParam: string | null;
}

export interface FontPairing {
  id: string;
  name: string;
  category: FontCategory;
  vibe: string;
  headingFontId: string;
  bodyFontId: string;
}

export const FONT_OPTIONS: readonly FontOption[] = [
  {
    id: "system",
    name: "System Default",
    style: "system",
    stack: null,
    googleFamilyParam: null,
  },
  // ── Serifs & Slabs (Headings / Editorial) ──
  {
    id: "fraunces",
    name: "Fraunces",
    style: "serif",
    stack: '"Fraunces", Georgia, serif',
    googleFamilyParam: "Fraunces:opsz,wght@9..144,600;9..144,700",
  },
  {
    id: "bitter",
    name: "Bitter",
    style: "slab",
    stack: '"Bitter", Georgia, serif',
    googleFamilyParam: "Bitter:wght@500;600;700",
  },
  {
    id: "arvo",
    name: "Arvo",
    style: "slab",
    stack: '"Arvo", Georgia, serif',
    googleFamilyParam: "Arvo:wght@400;700",
  },
  {
    id: "zilla-slab",
    name: "Zilla Slab",
    style: "slab",
    stack: '"Zilla Slab", Georgia, serif',
    googleFamilyParam: "Zilla+Slab:wght@500;600;700",
  },
  {
    id: "rokkitt",
    name: "Rokkitt",
    style: "slab",
    stack: '"Rokkitt", Georgia, serif',
    googleFamilyParam: "Rokkitt:wght@500;600;700",
  },
  {
    id: "young-serif",
    name: "Young Serif",
    style: "serif",
    stack: '"Young Serif", Georgia, serif',
    googleFamilyParam: "Young+Serif",
  },
  {
    id: "patua-one",
    name: "Patua One",
    style: "slab",
    stack: '"Patua One", Georgia, serif',
    googleFamilyParam: "Patua+One",
  },
  {
    id: "newsreader",
    name: "Newsreader",
    style: "serif",
    stack: '"Newsreader", Georgia, serif',
    googleFamilyParam: "Newsreader:opsz,wght@6..72,500;6..72,600;6..72,700",
  },
  {
    id: "lora",
    name: "Lora",
    style: "serif",
    stack: '"Lora", Georgia, serif',
    googleFamilyParam: "Lora:wght@500;600;700",
  },
  {
    id: "merriweather",
    name: "Merriweather",
    style: "serif",
    stack: '"Merriweather", Georgia, serif',
    googleFamilyParam: "Merriweather:wght@400;700",
  },
  {
    id: "instrument-serif",
    name: "Instrument Serif",
    style: "serif",
    stack: '"Instrument Serif", Georgia, serif',
    googleFamilyParam: "Instrument+Serif",
  },
  {
    id: "playfair-display",
    name: "Playfair Display",
    style: "serif",
    stack: '"Playfair Display", Georgia, serif',
    googleFamilyParam: "Playfair+Display:wght@600;700",
  },
  {
    id: "libre-baskerville",
    name: "Libre Baskerville",
    style: "serif",
    stack: '"Libre Baskerville", Georgia, serif',
    googleFamilyParam: "Libre+Baskerville:wght@400;700",
  },
  {
    id: "crimson-pro",
    name: "Crimson Pro",
    style: "serif",
    stack: '"Crimson Pro", Georgia, serif',
    googleFamilyParam: "Crimson+Pro:wght@500;600;700",
  },
  {
    id: "spectral",
    name: "Spectral",
    style: "serif",
    stack: '"Spectral", Georgia, serif',
    googleFamilyParam: "Spectral:wght@500;600;700",
  },
  {
    id: "vollkorn",
    name: "Vollkorn",
    style: "serif",
    stack: '"Vollkorn", Georgia, serif',
    googleFamilyParam: "Vollkorn:wght@500;600;700",
  },
  // ── Display & Characterful Sans ──
  {
    id: "bricolage-grotesque",
    name: "Bricolage Grotesque",
    style: "display",
    stack: '"Bricolage Grotesque", system-ui, sans-serif',
    googleFamilyParam: "Bricolage+Grotesque:wght@500;600;700",
  },
  {
    id: "oswald",
    name: "Oswald",
    style: "display",
    stack: '"Oswald", system-ui, sans-serif',
    googleFamilyParam: "Oswald:wght@500;600;700",
  },
  {
    id: "syne",
    name: "Syne",
    style: "display",
    stack: '"Syne", system-ui, sans-serif',
    googleFamilyParam: "Syne:wght@600;700",
  },
  {
    id: "space-grotesk",
    name: "Space Grotesk",
    style: "display",
    stack: '"Space Grotesk", system-ui, sans-serif',
    googleFamilyParam: "Space+Grotesk:wght@500;600;700",
  },
  {
    id: "outfit",
    name: "Outfit",
    style: "sans",
    stack: '"Outfit", system-ui, sans-serif',
    googleFamilyParam: "Outfit:wght@400;500;600;700",
  },
  {
    id: "archivo",
    name: "Archivo",
    style: "sans",
    stack: '"Archivo", system-ui, sans-serif',
    googleFamilyParam: "Archivo:wght@500;600;700",
  },
  {
    id: "sora",
    name: "Sora",
    style: "sans",
    stack: '"Sora", system-ui, sans-serif',
    googleFamilyParam: "Sora:wght@400;500;600;700",
  },
  // ── Clean Humanist & UI Body Sans ──
  {
    id: "plus-jakarta-sans",
    name: "Plus Jakarta Sans",
    style: "sans",
    stack: '"Plus Jakarta Sans", system-ui, sans-serif',
    googleFamilyParam: "Plus+Jakarta+Sans:wght@400;500;600;700",
  },
  {
    id: "dm-sans",
    name: "DM Sans",
    style: "sans",
    stack: '"DM Sans", system-ui, sans-serif',
    googleFamilyParam: "DM+Sans:wght@400;500;600;700",
  },
  {
    id: "source-sans-3",
    name: "Source Sans 3",
    style: "sans",
    stack: '"Source Sans 3", system-ui, sans-serif',
    googleFamilyParam: "Source+Sans+3:wght@400;500;600;700",
  },
  {
    id: "inter",
    name: "Inter",
    style: "sans",
    stack: '"Inter", system-ui, sans-serif',
    googleFamilyParam: "Inter:wght@400;500;600;700",
  },
  {
    id: "cabin",
    name: "Cabin",
    style: "sans",
    stack: '"Cabin", system-ui, sans-serif',
    googleFamilyParam: "Cabin:wght@400;500;600;700",
  },
  {
    id: "figtree",
    name: "Figtree",
    style: "sans",
    stack: '"Figtree", system-ui, sans-serif',
    googleFamilyParam: "Figtree:wght@400;500;600;700",
  },
  {
    id: "manrope",
    name: "Manrope",
    style: "sans",
    stack: '"Manrope", system-ui, sans-serif',
    googleFamilyParam: "Manrope:wght@400;500;600;700",
  },
  {
    id: "work-sans",
    name: "Work Sans",
    style: "sans",
    stack: '"Work Sans", system-ui, sans-serif',
    googleFamilyParam: "Work+Sans:wght@400;500;600;700",
  },
  {
    id: "instrument-sans",
    name: "Instrument Sans",
    style: "sans",
    stack: '"Instrument Sans", system-ui, sans-serif',
    googleFamilyParam: "Instrument+Sans:wght@400;500;600;700",
  },
  {
    id: "karla",
    name: "Karla",
    style: "sans",
    stack: '"Karla", system-ui, sans-serif',
    googleFamilyParam: "Karla:wght@400;500;600;700",
  },
  {
    id: "nunito-sans",
    name: "Nunito Sans",
    style: "sans",
    stack: '"Nunito Sans", system-ui, sans-serif',
    googleFamilyParam: "Nunito+Sans:wght@400;500;600;700",
  },
  {
    id: "nunito",
    name: "Nunito",
    style: "sans",
    stack: '"Nunito", system-ui, sans-serif',
    googleFamilyParam: "Nunito:wght@400;500;600;700",
  },
  {
    id: "quicksand",
    name: "Quicksand",
    style: "sans",
    stack: '"Quicksand", system-ui, sans-serif',
    googleFamilyParam: "Quicksand:wght@500;600;700",
  },
  {
    id: "lato",
    name: "Lato",
    style: "sans",
    stack: '"Lato", system-ui, sans-serif',
    googleFamilyParam: "Lato:wght@400;700",
  },
  {
    id: "open-sans",
    name: "Open Sans",
    style: "sans",
    stack: '"Open Sans", system-ui, sans-serif',
    googleFamilyParam: "Open+Sans:wght@400;500;600;700",
  },
  {
    id: "ibm-plex-sans",
    name: "IBM Plex Sans",
    style: "sans",
    stack: '"IBM Plex Sans", system-ui, sans-serif',
    googleFamilyParam: "IBM+Plex+Sans:wght@400;500;600;700",
  },
  {
    id: "public-sans",
    name: "Public Sans",
    style: "sans",
    stack: '"Public Sans", system-ui, sans-serif',
    googleFamilyParam: "Public+Sans:wght@400;500;600;700",
  },
  {
    id: "atkinson-hyperlegible",
    name: "Atkinson Hyperlegible",
    style: "sans",
    stack: '"Atkinson Hyperlegible", system-ui, sans-serif',
    googleFamilyParam: "Atkinson+Hyperlegible:wght@400;700",
  },
  {
    id: "lexend",
    name: "Lexend",
    style: "sans",
    stack: '"Lexend", system-ui, sans-serif',
    googleFamilyParam: "Lexend:wght@400;500;600;700",
  },
  {
    id: "rubik",
    name: "Rubik",
    style: "sans",
    stack: '"Rubik", system-ui, sans-serif',
    googleFamilyParam: "Rubik:wght@400;500;600;700",
  },
  {
    id: "albert-sans",
    name: "Albert Sans",
    style: "sans",
    stack: '"Albert Sans", system-ui, sans-serif',
    googleFamilyParam: "Albert+Sans:wght@400;500;600;700",
  },
  {
    id: "geist",
    name: "Geist",
    style: "sans",
    stack: '"Geist", system-ui, sans-serif',
    googleFamilyParam: "Geist:wght@400;500;600;700",
  },
  // ── Monospace / Topo ──
  {
    id: "jetbrains-mono",
    name: "JetBrains Mono",
    style: "mono",
    stack: '"JetBrains Mono", ui-monospace, monospace',
    googleFamilyParam: "JetBrains+Mono:wght@500;600;700",
  },
  {
    id: "ibm-plex-mono",
    name: "IBM Plex Mono",
    style: "mono",
    stack: '"IBM Plex Mono", ui-monospace, monospace',
    googleFamilyParam: "IBM+Plex+Mono:wght@500;600;700",
  },
  {
    id: "fira-code",
    name: "Fira Code",
    style: "mono",
    stack: '"Fira Code", ui-monospace, monospace',
    googleFamilyParam: "Fira+Code:wght@500;600;700",
  },
];

export const BODY_FONT_OPTIONS: readonly FontOption[] = FONT_OPTIONS.filter(
  (font) =>
    font.style === "system" ||
    font.style === "sans" ||
    font.id === "lora" ||
    font.id === "newsreader" ||
    font.id === "bitter" ||
    font.id === "merriweather" ||
    font.id === "spectral",
);

export const FONT_CATEGORIES: readonly FontCategory[] = [
  "Outdoor & Heritage",
  "Editorial Serif",
  "Humanist Sans",
  "Modern Geometric",
  "Topo & Mono",
  "Default",
];

export const FONT_PAIRINGS: readonly FontPairing[] = [
  // ── Outdoor & Heritage ──
  {
    id: "national-park",
    name: "National Park",
    category: "Outdoor & Heritage",
    vibe: "Bitter slab + Source Sans 3 — classic park guide",
    headingFontId: "bitter",
    bodyFontId: "source-sans-3",
  },
  {
    id: "alpine-slab",
    name: "Alpine Slab",
    category: "Outdoor & Heritage",
    vibe: "Arvo slab + Karla — sturdy trailhead signage",
    headingFontId: "arvo",
    bodyFontId: "karla",
  },
  {
    id: "trail-sign",
    name: "Trail Sign",
    category: "Outdoor & Heritage",
    vibe: "Oswald condensed + Source Sans 3 — bold NPS poster",
    headingFontId: "oswald",
    bodyFontId: "source-sans-3",
  },
  {
    id: "ranger-station",
    name: "Ranger Station",
    category: "Outdoor & Heritage",
    vibe: "Zilla Slab + Inter — warm institutional clarity",
    headingFontId: "zilla-slab",
    bodyFontId: "inter",
  },
  {
    id: "campground-poster",
    name: "Campground Poster",
    category: "Outdoor & Heritage",
    vibe: "Young Serif + DM Sans — vintage parks lithograph",
    headingFontId: "young-serif",
    bodyFontId: "dm-sans",
  },
  {
    id: "timber-canvas",
    name: "Timber & Canvas",
    category: "Outdoor & Heritage",
    vibe: "Patua One + Cabin — rugged heritage outfitter",
    headingFontId: "patua-one",
    bodyFontId: "cabin",
  },
  {
    id: "outfitter-classic",
    name: "Outfitter Classic",
    category: "Outdoor & Heritage",
    vibe: "Rokkitt slab + Lato — crisp 1970s gear catalog",
    headingFontId: "rokkitt",
    bodyFontId: "lato",
  },
  {
    id: "woodcut-guide",
    name: "Woodcut Guide",
    category: "Outdoor & Heritage",
    vibe: "Vollkorn + Work Sans — hearty field manual",
    headingFontId: "vollkorn",
    bodyFontId: "work-sans",
  },

  // ── Editorial Serif ──
  {
    id: "field-guide",
    name: "Field Guide",
    category: "Editorial Serif",
    vibe: "Fraunces soft serif + Plus Jakarta Sans",
    headingFontId: "fraunces",
    bodyFontId: "plus-jakarta-sans",
  },
  {
    id: "cabin-editorial",
    name: "Cabin Editorial",
    category: "Editorial Serif",
    vibe: "Newsreader + Inter — refined modern print",
    headingFontId: "newsreader",
    bodyFontId: "inter",
  },
  {
    id: "outdoor-magazine",
    name: "Outdoor Magazine",
    category: "Editorial Serif",
    vibe: "Lora + Work Sans — warm editorial storytelling",
    headingFontId: "lora",
    bodyFontId: "work-sans",
  },
  {
    id: "woodland-book",
    name: "Woodland Book",
    category: "Editorial Serif",
    vibe: "Merriweather + Open Sans — cozy & super readable",
    headingFontId: "merriweather",
    bodyFontId: "open-sans",
  },
  {
    id: "botanical-journal",
    name: "Botanical Journal",
    category: "Editorial Serif",
    vibe: "Instrument Serif + Instrument Sans — stylish boutique",
    headingFontId: "instrument-serif",
    bodyFontId: "instrument-sans",
  },
  {
    id: "sierra-literary",
    name: "Sierra Literary",
    category: "Editorial Serif",
    vibe: "Playfair Display + Lato — high-contrast classic",
    headingFontId: "playfair-display",
    bodyFontId: "lato",
  },
  {
    id: "pacific-essay",
    name: "Pacific Essay",
    category: "Editorial Serif",
    vibe: "Libre Baskerville + Source Sans 3 — timeless bookish",
    headingFontId: "libre-baskerville",
    bodyFontId: "source-sans-3",
  },
  {
    id: "almanac-print",
    name: "Almanac Print",
    category: "Editorial Serif",
    vibe: "Crimson Pro + Public Sans — crisp farmer's almanac",
    headingFontId: "crimson-pro",
    bodyFontId: "public-sans",
  },
  {
    id: "warm-chronicle",
    name: "Warm Chronicle",
    category: "Editorial Serif",
    vibe: "Spectral + Karla — graceful & understated",
    headingFontId: "spectral",
    bodyFontId: "karla",
  },

  // ── Humanist Sans ──
  {
    id: "trailhead",
    name: "Trailhead",
    category: "Humanist Sans",
    vibe: "Bricolage Grotesque + DM Sans — expressive & human",
    headingFontId: "bricolage-grotesque",
    bodyFontId: "dm-sans",
  },
  {
    id: "cabin-sans",
    name: "Cabin Humanist",
    category: "Humanist Sans",
    vibe: "Cabin + Cabin — warm humanist signage sans",
    headingFontId: "cabin",
    bodyFontId: "cabin",
  },
  {
    id: "compass-friendly",
    name: "Compass Friendly",
    category: "Humanist Sans",
    vibe: "Figtree + Figtree — clean, friendly modern UI",
    headingFontId: "figtree",
    bodyFontId: "figtree",
  },
  {
    id: "friendly-modern",
    name: "Friendly Modern",
    category: "Humanist Sans",
    vibe: "Outfit + Nunito Sans — approachable & crisp",
    headingFontId: "outfit",
    bodyFontId: "nunito-sans",
  },
  {
    id: "parkway-accessible",
    name: "Parkway Clear",
    category: "Humanist Sans",
    vibe: "Atkinson Hyperlegible — built for effortless reading",
    headingFontId: "atkinson-hyperlegible",
    bodyFontId: "atkinson-hyperlegible",
  },
  {
    id: "open-trail",
    name: "Open Trail",
    category: "Humanist Sans",
    vibe: "Lexend + Inter — wide, calm, easy-scanning",
    headingFontId: "lexend",
    bodyFontId: "inter",
  },
  {
    id: "soft-horizon",
    name: "Soft Horizon",
    category: "Humanist Sans",
    vibe: "Quicksand + Nunito — rounded & playful camp vibe",
    headingFontId: "quicksand",
    bodyFontId: "nunito",
  },
  {
    id: "camp-rubik",
    name: "Warm Rounded",
    category: "Humanist Sans",
    vibe: "Rubik + Albert Sans — slightly rounded, modern warmth",
    headingFontId: "rubik",
    bodyFontId: "albert-sans",
  },

  // ── Modern Geometric ──
  {
    id: "swiss-poster",
    name: "Swiss Poster",
    category: "Modern Geometric",
    vibe: "Archivo + Inter — crisp alpine graphic design",
    headingFontId: "archivo",
    bodyFontId: "inter",
  },
  {
    id: "nordic-minimal",
    name: "Nordic Minimal",
    category: "Modern Geometric",
    vibe: "Manrope + Manrope — quiet Scandinavian craft",
    headingFontId: "manrope",
    bodyFontId: "manrope",
  },
  {
    id: "peak-geometric",
    name: "Peak Geometric",
    category: "Modern Geometric",
    vibe: "Sora + Plus Jakarta Sans — sharp contemporary",
    headingFontId: "sora",
    bodyFontId: "plus-jakarta-sans",
  },
  {
    id: "modern-outfitter",
    name: "Modern Outfitter",
    category: "Modern Geometric",
    vibe: "Syne + DM Sans — bold indie outdoor brand",
    headingFontId: "syne",
    bodyFontId: "dm-sans",
  },
  {
    id: "clean-geist",
    name: "Clean Studio",
    category: "Modern Geometric",
    vibe: "Geist + Geist — refined technical clarity",
    headingFontId: "geist",
    bodyFontId: "geist",
  },

  // ── Topo & Mono ──
  {
    id: "topo-utility",
    name: "Topo Utility",
    category: "Topo & Mono",
    vibe: "Space Grotesk + IBM Plex Sans — utilitarian map feel",
    headingFontId: "space-grotesk",
    bodyFontId: "ibm-plex-sans",
  },
  {
    id: "map-coordinates",
    name: "Map Coordinates",
    category: "Topo & Mono",
    vibe: "JetBrains Mono + Plus Jakarta Sans — topo data aesthetic",
    headingFontId: "jetbrains-mono",
    bodyFontId: "plus-jakarta-sans",
  },
  {
    id: "surveyor-log",
    name: "Surveyor Log",
    category: "Topo & Mono",
    vibe: "IBM Plex Mono + IBM Plex Sans — classic USGS field log",
    headingFontId: "ibm-plex-mono",
    bodyFontId: "ibm-plex-sans",
  },
  {
    id: "compass-grid",
    name: "Compass Grid",
    category: "Topo & Mono",
    vibe: "Fira Code + Work Sans — technical trail utility",
    headingFontId: "fira-code",
    bodyFontId: "work-sans",
  },

  // ── Default ──
  {
    id: "system",
    name: "System Default",
    category: "Default",
    vibe: "Current app OS system font stack",
    headingFontId: "system",
    bodyFontId: "system",
  },
];

export function getFontOption(fontId: string | undefined): FontOption {
  return FONT_OPTIONS.find((font) => font.id === fontId) ?? FONT_OPTIONS[0];
}

export function resolveTypography(
  fontId: string,
  customHeadingFontId?: string,
  customBodyFontId?: string,
): {
  label: string;
  headingFont: FontOption;
  bodyFont: FontOption;
  googleFontsHref: string | null;
} {
  const pairing =
    FONT_PAIRINGS.find((item) => item.id === fontId) ??
    FONT_PAIRINGS[FONT_PAIRINGS.length - 1];

  const headingFont = getFontOption(
    customHeadingFontId ?? pairing.headingFontId,
  );
  const bodyFont = getFontOption(customBodyFontId ?? pairing.bodyFontId);

  const params = Array.from(
    new Set(
      [headingFont.googleFamilyParam, bodyFont.googleFamilyParam].filter(
        (param): param is string => Boolean(param),
      ),
    ),
  );

  const googleFontsHref =
    params.length > 0
      ? `https://fonts.googleapis.com/css2?${params.map((p) => `family=${p}`).join("&")}&display=swap`
      : null;

  const isCustomMix = Boolean(customHeadingFontId || customBodyFontId);
  const label = isCustomMix
    ? `${headingFont.name} + ${bodyFont.name}`
    : pairing.name;

  return {
    label,
    headingFont,
    bodyFont,
    googleFontsHref,
  };
}
