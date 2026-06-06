import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import { Layout } from "@/components/Layout";
import { Home } from "@/pages/Home";
import { Providers } from "@/pages/Providers";
import { Auth } from "@/pages/Auth";
import { Dashboard } from "@/pages/Dashboard";
import { EarlyAccess } from "@/pages/EarlyAccess";
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
import { AuthProvider } from "@/hooks/useAuth";

const basename = import.meta.env.BASE_URL.replace(/\/$/, "");

function App() {
  return (
    <AuthProvider>
      <Router basename={basename}>
        <Routes>
          {/* Auth page without layout */}
          <Route path="/auth" element={<Auth />} />
          <Route path="/early-access" element={<EarlyAccess />} />

          {/* Pages with layout */}
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
    </AuthProvider>
  );
}

export default App;
