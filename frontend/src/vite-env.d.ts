// SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0

/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_URL?: string;
  readonly VITE_AUTH0_DOMAIN?: string;
  readonly VITE_AUTH0_CLIENT_ID?: string;
  readonly VITE_AUTH0_AUDIENCE?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
