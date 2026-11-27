/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_ENABLE_COMMUNITY_PAGES?: string;
  readonly VITE_MAP_TILE_URL?: string;
  readonly VITE_MAP_ATTRIBUTION_TEXT?: string;
  readonly VITE_MAP_ATTRIBUTION_URL?: string;
  readonly VITE_MAP_MAX_NATIVE_ZOOM?: string;
  readonly VITE_MOBILE_AUTH0_CLIENT_ID?: string;
}
