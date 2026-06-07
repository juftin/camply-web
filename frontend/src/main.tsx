// SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0

import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Auth0Provider } from "@auth0/auth0-react";
import "./index.css";
import App from "./App.tsx";
import { ThemeProvider } from "@/components/theme-provider";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});

// Conditionally enable Auth0 when the required env vars are set
const auth0Domain = import.meta.env.VITE_AUTH0_DOMAIN;
const auth0ClientId = import.meta.env.VITE_AUTH0_CLIENT_ID;
const auth0Audience = import.meta.env.VITE_AUTH0_AUDIENCE;
const hasAuth0 = Boolean(auth0Domain && auth0ClientId);

function Root() {
  const app = (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider storageKey="camply-ui-theme">
        <App />
      </ThemeProvider>
    </QueryClientProvider>
  );

  if (hasAuth0) {
    return (
      <Auth0Provider
        domain={auth0Domain!}
        clientId={auth0ClientId!}
        authorizationParams={{
          redirect_uri: window.location.origin,
          audience: auth0Audience || undefined,
        }}
      >
        {app}
      </Auth0Provider>
    );
  }

  return app;
}

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <Root />
  </StrictMode>,
);
