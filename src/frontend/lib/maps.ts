import type {
  Campground,
  RecreationArea,
  SearchResult,
  MapSearchResult,
} from "./structs";

export interface GeoBounds {
  west: number;
  south: number;
  east: number;
  north: number;
}
export interface MapCamera {
  lat: number;
  lng: number;
  zoom: number;
}
export interface MapPin {
  id: string;
  lat: number;
  lng: number;
  label: string;
  description?: string;
  type?: "campground" | "recreation-area";
  count?: number;
  onSelect?: () => void;
}
export const MERCATOR_LIMIT = 85.05112878;
export const validCoordinates = (
  lat: number | null | undefined,
  lng: number | null | undefined,
): boolean =>
  typeof lat === "number" &&
  typeof lng === "number" &&
  Number.isFinite(lat) &&
  Number.isFinite(lng) &&
  Math.abs(lat) <= 90 &&
  Math.abs(lng) <= 180;
export const hasMappableCoordinates = (
  item?: {
    latitude?: number | null;
    longitude?: number | null;
  } | null,
): boolean =>
  item != null &&
  validCoordinates(item.latitude, item.longitude) &&
  !(item.latitude === 0 && item.longitude === 0);

/** Use the parent's complete coordinate pair when a campground cannot be mapped. */
export const withRecreationAreaCoordinates = (
  campground: Campground,
  recreationArea?: RecreationArea | null,
): Campground =>
  !hasMappableCoordinates(campground) &&
  recreationArea &&
  hasMappableCoordinates(recreationArea)
    ? {
        ...campground,
        latitude: recreationArea.latitude,
        longitude: recreationArea.longitude,
      }
    : campground;

export const normalizeLongitude = (lng: number): number =>
  ((((lng + 180) % 360) + 360) % 360) - 180;
export const displayLatitude = (lat: number): number =>
  Math.max(-MERCATOR_LIMIT, Math.min(MERCATOR_LIMIT, lat));
export const nearestLongitude = (lng: number, center: number): number =>
  lng + 360 * Math.round((center - lng) / 360);

export const viewportBounds = (
  west: number,
  south: number,
  east: number,
  north: number,
): GeoBounds => ({
  west: east - west >= 360 ? -180 : normalizeLongitude(west),
  east: east - west >= 360 ? 180 : normalizeLongitude(east),
  south: south <= -MERCATOR_LIMIT + 0.00001 ? -90 : Math.max(-90, south),
  north: north >= MERCATOR_LIMIT - 0.00001 ? 90 : Math.min(90, north),
});

export const fitLocations = (
  locations: { lat: number; lng: number }[],
): GeoBounds | null => {
  const valid = locations.filter((p) => validCoordinates(p.lat, p.lng));
  if (!valid.length) return null;
  const longitudes = [
    ...new Set(valid.map((p) => normalizeLongitude(p.lng))),
  ].sort((a, b) => a - b);
  let gap = -1,
    start = longitudes[0],
    end = longitudes[0];
  longitudes.forEach((lng, i) => {
    const next =
      longitudes[(i + 1) % longitudes.length] +
      (i === longitudes.length - 1 ? 360 : 0);
    if (next - lng > gap) {
      gap = next - lng;
      start = normalizeLongitude(next);
      end = lng;
    }
  });
  return {
    west: start,
    east: end,
    south: Math.min(...valid.map((p) => p.lat)),
    north: Math.max(...valid.map((p) => p.lat)),
  };
};

export const DEFAULT_MAP_STYLE_URL =
  "https://tiles.openfreemap.org/styles/liberty";

export interface VectorStyleBasemapConfig {
  kind: "style";
  styleUrl: string;
}

export interface RasterTileBasemapConfig {
  kind: "raster";
  url: string;
  text: string;
  link: string;
  maxNativeZoom: number;
}

export type BasemapConfig = VectorStyleBasemapConfig | RasterTileBasemapConfig;

const hasWhitespaceOrControl = (value: string): boolean => {
  for (let i = 0; i < value.length; i += 1) {
    const code = value.charCodeAt(i);
    if (code <= 0x20 || code === 0x7f) return true;
  }
  return /\s/.test(value);
};

const isHttpsOrRootRelative = (value: string): boolean =>
  value.startsWith("https://") ||
  (value.startsWith("/") && !value.startsWith("//"));

export const basemapConfig = (
  env: Record<string, string | undefined> = import.meta.env,
): BasemapConfig => {
  const customTileUrl = env.VITE_MAP_TILE_URL?.trim() ?? "";
  if (customTileUrl) {
    const text = env.VITE_MAP_ATTRIBUTION_TEXT?.trim() ?? "";
    const link = env.VITE_MAP_ATTRIBUTION_URL?.trim() ?? "";
    const maxNativeZoom = Number(env.VITE_MAP_MAX_NATIVE_ZOOM?.trim() || "19");
    if (!text || !link)
      throw new Error("Custom map source requires attribution text and URL.");
    if (!/^https:\/\//.test(link) || hasWhitespaceOrControl(link))
      throw new Error("Map attribution must use an HTTPS URL.");
    const parsedLink = new URL(link);
    if (
      parsedLink.protocol !== "https:" ||
      parsedLink.username ||
      parsedLink.password
    )
      throw new Error("Map attribution must use a public HTTPS URL.");
    if (
      hasWhitespaceOrControl(customTileUrl) ||
      !isHttpsOrRootRelative(customTileUrl) ||
      !["{z}", "{x}", "{y}"].every((token) => customTileUrl.includes(token))
    )
      throw new Error(
        "Map source must be an HTTPS or same-origin XYZ tile URL.",
      );
    const parsedUrl = new URL(
      customTileUrl.replace(/\{[zxy]\}/g, "0"),
      "https://camply.invalid",
    );
    if (
      parsedUrl.protocol !== "https:" ||
      parsedUrl.username ||
      parsedUrl.password ||
      (customTileUrl.startsWith("/") &&
        parsedUrl.origin !== "https://camply.invalid")
    )
      throw new Error(
        "Map source must be a public HTTPS or same-origin XYZ tile URL.",
      );
    if (
      !Number.isInteger(maxNativeZoom) ||
      maxNativeZoom < 0 ||
      maxNativeZoom > 19
    )
      throw new Error("Map native zoom must be an integer from 0 to 19.");
    return { kind: "raster", url: customTileUrl, text, link, maxNativeZoom };
  }

  const styleUrl = env.VITE_MAP_STYLE_URL?.trim() || DEFAULT_MAP_STYLE_URL;
  if (hasWhitespaceOrControl(styleUrl) || !isHttpsOrRootRelative(styleUrl))
    throw new Error("Map style must be a public HTTPS or same-origin URL.");
  let parsedStyleUrl: URL;
  try {
    parsedStyleUrl = new URL(styleUrl, "https://camply.invalid");
  } catch {
    throw new Error("Map style must be a valid HTTPS or same-origin URL.");
  }
  if (
    parsedStyleUrl.protocol !== "https:" ||
    parsedStyleUrl.username ||
    parsedStyleUrl.password ||
    (styleUrl.startsWith("/") &&
      parsedStyleUrl.origin !== "https://camply.invalid")
  )
    throw new Error("Map style must be a public HTTPS or same-origin URL.");
  return { kind: "style", styleUrl };
};

export const toCampground = (
  item: SearchResult | MapSearchResult,
): Campground => ({
  id: item.campground_id || item.id,
  provider_id: item.provider_id,
  recreation_area_id: item.recreation_area_id ?? null,
  name: item.campground_name || "Campground",
  description: null,
  country: item.country ?? null,
  state: item.state ?? null,
  latitude: item.latitude ?? null,
  longitude: item.longitude ?? null,
  reservable: item.reservable ?? true,
  enabled: true,
  url: "",
});
export const detailUrl = (item: SearchResult | MapSearchResult): string =>
  item.entity_type === "Campground" && item.campground_id
    ? `/campground/${item.provider_id}/${encodeURIComponent(item.campground_id)}`
    : `/rec-area/${item.provider_id}/${encodeURIComponent(item.recreation_area_id || "")}`;

/** Start nearby discovery with a broad regional area around approximate coordinates. */
export const regionalBounds = (lat: number, lng: number): GeoBounds => ({
  west: normalizeLongitude(lng - 3),
  east: normalizeLongitude(lng + 3),
  south: Math.max(-90, lat - 2),
  north: Math.min(90, lat + 2),
});
