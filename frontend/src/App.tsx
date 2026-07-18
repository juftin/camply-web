import { useState, useEffect } from "react";
import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import { Auth0Provider } from "@auth0/auth0-react";
import { Layout } from "@/components/Layout";
import { Home } from "@/pages/Home";
import { Providers } from "@/pages/Providers";
import { Auth } from "@/pages/Auth";
import { Dashboard } from "@/pages/Dashboard";
import { EarlyAccess } from "@/pages/EarlyAccess";
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
import { AuthProvider, AuthModeContext } from "@/hooks/useAuth";
import { fetchAuthConfig, type AuthConfig } from "@/lib/api";

const basename = import.meta.env.BASE_URL.replace(/\/$/, "");

function AppRoutes() {
  return (
    <Router basename={basename}>
      <Routes>
        <Route path="/auth" element={<Auth />} />
        <Route path="/early-access" element={<EarlyAccess />} />

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
                <Route path="/dashboard" element={<Dashboard />} />
                <Route path="/profile" element={<Profile />} />
                <Route
                  path="/dashboard/scans/:scanId"
                  element={<ScanDetail />}
                />
                <Route
                  path="/campground/:providerId/:campgroundId"
                  element={<Campground />}
                />
                <Route
                  path="/rec-area/:providerId/:recreationAreaId"
                  element={<RecreationArea />}
                />
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

  useEffect(() => {
    fetchAuthConfig().then(setConfig).catch(() => setConfig({ auth_mode: "basic", auth0_domain: null, auth0_client_id: null }));
  }, []);

  if (!config) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-background">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
      </div>
    );
  }

  const isAuth0 = config.auth_mode === "auth0" && config.auth0_domain && config.auth0_client_id;

  if (isAuth0) {
    return (
      <Auth0Provider
        domain={config.auth0_domain!}
        clientId={config.auth0_client_id!}
        authorizationParams={{
          redirect_uri: window.location.origin,
        }}
        cacheLocation="localstorage"
      >
        <AuthModeContext.Provider value="auth0">
          <AuthProvider>
            <AppRoutes />
          </AuthProvider>
        </AuthModeContext.Provider>
      </Auth0Provider>
    );
  }

  return (
    <AuthModeContext.Provider value="basic">
      <AuthProvider>
        <AppRoutes />
      </AuthProvider>
    </AuthModeContext.Provider>
  );
}

export default App;
