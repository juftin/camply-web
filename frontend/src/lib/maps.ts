import type { Campground, SearchResult, MapSearchResult } from "./structs";

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

export const basemapConfig = (
  env: Record<string, string | undefined> = import.meta.env,
) => {
  const custom = env.VITE_MAP_TILE_URL;
  const url = custom || "https://tile.openstreetmap.org/{z}/{x}/{y}.png";
  const text =
    env.VITE_MAP_ATTRIBUTION_TEXT ||
    (custom ? "" : "© OpenStreetMap contributors");
  const link =
    env.VITE_MAP_ATTRIBUTION_URL ||
    (custom ? "" : "https://www.openstreetmap.org/copyright");
  const maxNativeZoom = Number(env.VITE_MAP_MAX_NATIVE_ZOOM || "19");
  if (!text || !link)
    throw new Error("Custom map source requires attribution text and URL.");
  if (!/^https:\/\//.test(link))
    throw new Error("Map attribution must use an HTTPS URL.");
  new URL(link);
  if (
    !(
      url.startsWith("https://") ||
      (url.startsWith("/") && !url.startsWith("//"))
    ) ||
    !["{z}", "{x}", "{y}"].every((token) => url.includes(token))
  )
    throw new Error("Map source must be an HTTPS or same-origin XYZ tile URL.");
  const parsedUrl = new URL(
    url.replace(/\{[zxy]\}/g, "0"),
    "https://camply.invalid",
  );
  if (
    parsedUrl.protocol !== "https:" ||
    parsedUrl.username ||
    parsedUrl.password
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
  return { url, text, link, maxNativeZoom };
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
