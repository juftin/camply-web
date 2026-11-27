import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import "./index.css";
import App from "./App.tsx";
import { ThemeProvider } from "@/components/theme-provider";
import { Button } from "@/components/ui/button";
import { loadMobileServer } from "@/lib/mobile-server";
import { configureMobileApi } from "@/lib/api";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});

const root = createRoot(document.getElementById("root")!);

async function start() {
  try {
    configureMobileApi(await loadMobileServer());
  } catch {
    root.render(
      <main className="space-y-3 p-8 text-center">
        <p role="alert">Could not load server settings.</p>
        <Button onClick={() => void start()}>Try again</Button>
      </main>,
    );
    return;
  }

  root.render(
    <StrictMode>
      <QueryClientProvider client={queryClient}>
        <ThemeProvider storageKey="camply-ui-theme">
          <App />
        </ThemeProvider>
      </QueryClientProvider>
    </StrictMode>,
  );
}

void start();
