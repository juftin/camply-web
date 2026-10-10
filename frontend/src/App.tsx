import { useState, useEffect } from "react";
import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import { Auth0Provider } from "@auth0/auth0-react";
import { ProtectedRoute } from "@/components/ProtectedRoute";
import { Layout } from "@/components/Layout";
import { Home } from "@/pages/Home";
import { Providers } from "@/pages/Providers";
import { Auth } from "@/pages/Auth";
import { Dashboard } from "@/pages/Dashboard";
import { Profile } from "@/pages/Profile";
import { PrivacyPolicy } from "@/pages/PrivacyPolicy";
import { TermsOfService } from "@/pages/TermsOfService";
import { Contact } from "@/pages/Contact";
import { Contribute } from "@/pages/Contribute";
import { FAQ } from "@/pages/FAQ";
import { Ethos } from "@/pages/Ethos";
import { HowItWorks } from "@/pages/HowItWorks";
import { Campground } from "@/pages/Campground";
import { RecreationArea } from "@/pages/RecreationArea";
import { ScanDetail } from "@/pages/ScanDetail";
import { DevPreview } from "@/pages/DevPreview";
import { AuthProvider, AuthConfigContext } from "@/hooks/useAuth";
import { fetchAuthConfig, type AuthConfig } from "@/lib/api";

const basename = import.meta.env.BASE_URL.replace(/\/$/, "");

function AppRoutes() {
  return (
    <Router basename={basename}>
      <Routes>
        <Route path="/auth" element={<Auth />} />

        <Route
          path="/*"
          element={
            <Layout>
              <Routes>
                <Route path="/" element={<Home />} />
                <Route path="/providers" element={<Providers />} />
                <Route path="/ethos" element={<Ethos />} />
                <Route path="/how-it-works" element={<HowItWorks />} />
                <Route path="/contribute" element={<Contribute />} />
                <Route path="/faq" element={<FAQ />} />
                <Route path="/privacy" element={<PrivacyPolicy />} />
                <Route path="/terms" element={<TermsOfService />} />
                <Route path="/contact" element={<Contact />} />
                <Route
                  path="/dashboard"
                  element={
                    <ProtectedRoute requireInvite>
                      <Dashboard />
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="/profile"
                  element={
                    <ProtectedRoute>
                      <Profile />
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="/dashboard/scans/:scanId"
                  element={
                    <ProtectedRoute requireInvite>
                      <ScanDetail />
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="/campground/:providerId/:campgroundId"
                  element={<Campground />}
                />
                <Route
                  path="/rec-area/:providerId/:recreationAreaId"
                  element={<RecreationArea />}
                />
                <Route path="/dev/preview" element={<DevPreview />} />
              </Routes>
            </Layout>
          }
        />
      </Routes>
    </Router>
  );
}

function App() {
  const [config, setConfig] = useState<AuthConfig | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchAuthConfig()
      .then((loaded) => {
        if (!["none", "session", "auth0"].includes(loaded.auth_mode)) {
          throw new Error("Unsupported authentication configuration.");
        }
        if (
          !loaded.auto_login &&
          loaded.auth_mode === "auth0" &&
          (!loaded.auth0_domain ||
            !loaded.auth0_client_id ||
            !loaded.auth0_audience)
        ) {
          throw new Error("Auth0 configuration is incomplete.");
        }
        setConfig(loaded);
      })
      .catch(() =>
        setError(
          "Unable to load authentication configuration. Please reload to try again.",
        ),
      );
  }, []);

  if (error) {
    return (
      <div role="alert" className="p-8 text-center">
        {error}
      </div>
    );
  }

  if (!config) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-background">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
      </div>
    );
  }

  const isAuth0 = !config.auto_login && config.auth_mode === "auth0";

  if (isAuth0) {
    return (
      <Auth0Provider
        domain={config.auth0_domain!}
        clientId={config.auth0_client_id!}
        authorizationParams={{
          redirect_uri: new URL(
            import.meta.env.BASE_URL,
            window.location.origin,
          ).href,
          audience: config.auth0_audience!,
        }}
        cacheLocation="localstorage"
      >
        <AuthConfigContext.Provider value={config}>
          <AuthProvider>
            <AppRoutes />
          </AuthProvider>
        </AuthConfigContext.Provider>
      </Auth0Provider>
    );
  }

  return (
    <AuthConfigContext.Provider value={config}>
      <AuthProvider>
        <AppRoutes />
      </AuthProvider>
    </AuthConfigContext.Provider>
  );
}

export default App;
