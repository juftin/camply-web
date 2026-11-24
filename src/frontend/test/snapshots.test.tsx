/**
 * Automated DOM snapshot tests for Camply UI components.
 *
 * Verifies DOM structure, layout primitives, and component variants
 * to catch unintended markup regressions during frontend builds.
 */

import { render as renderUI } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactNode } from "react";
import { MemoryRouter } from "react-router-dom";
import { afterAll, beforeAll, describe, expect, it, vi } from "vitest";

import { CamplyLogo } from "@/components/CamplyLogo";
import { CollapsibleDescription } from "@/components/CollapsibleDescription";
import { DismissibleBanner } from "@/components/DismissibleBanner";
import { Header } from "@/components/Header";
import { SearchDropdown } from "@/components/SearchDropdown";
import { AdminNav } from "@/components/AdminNav";
import { AdminFeedback } from "@/components/admin/AdminFeedback";
import { AdminPagination } from "@/components/admin/AdminPagination";
import { ScanCard } from "@/components/ScanCard";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Switch } from "@/components/ui/switch";
import { ThemeProviderContext } from "@/hooks/use-theme";
import type { AuthState } from "@/hooks/useAuth";
import type { ScanResponse, SearchResult } from "@/lib/structs";
import { DevPreview } from "@/pages/DevPreview";

const render = (ui: ReactNode) =>
  renderUI(
    <QueryClientProvider client={new QueryClient()}>{ui}</QueryClientProvider>,
  );

let mockAuthState: AuthState = {
  user: null,
  isLoading: false,
  error: null,
  isInvited: true,
  isAdmin: false,
  isScanningEnabled: true,
  isReady: true,
  refresh: vi.fn(),
  updatePushoverToken: vi.fn(),
  signOut: vi.fn(),
  login: vi.fn(),
  authMode: "session",
  inviteOnly: false,
  autoLogin: false,
  signupEnabled: true,
  accountPath: "/profile",
};

vi.mock("@/hooks/useAuth", () => ({
  useAuth: () => mockAuthState,
}));

const mockThemeContext = {
  theme: "light" as const,
  userTheme: "light" as const,
  setTheme: vi.fn(),
  toggleTheme: vi.fn(),
};

const FIXED_TIME = "2026-10-10T12:00:00Z";

const mockActiveScan: ScanResponse = {
  id: "snap-scan-1",
  provider_id: 1,
  campground_id: "232447",
  campground_name: "Upper Pines Campground",
  recreation_area_name: "Yosemite National Park",
  start_date: "2026-11-15",
  end_date: "2026-11-19",
  is_active: true,
  min_stay_length: 2,
  preferred_types: ["STANDARD NONELECTRIC", "TENT ONLY"],
  require_electric: true,
  last_checked_at: FIXED_TIME,
  found_count: 3,
  created_at: "2026-10-01T12:00:00Z",
};

const mockPausedScan: ScanResponse = {
  id: "snap-scan-2",
  provider_id: 1,
  campground_id: "232450",
  campground_name: "Camp 4 Walk-In",
  recreation_area_name: "Yosemite National Park",
  start_date: "2026-11-01",
  end_date: "2026-11-03",
  is_active: false,
  min_stay_length: 1,
  preferred_types: [],
  require_electric: false,
  last_checked_at: FIXED_TIME,
  found_count: 0,
  created_at: "2026-10-05T12:00:00Z",
};

const mockEndedScan: ScanResponse = {
  id: "snap-scan-3",
  provider_id: 1,
  campground_id: "232449",
  campground_name: "Lower Pines",
  recreation_area_name: "Yosemite National Park",
  start_date: "2026-09-01",
  end_date: "2026-09-05",
  is_active: false,
  min_stay_length: 1,
  preferred_types: [],
  require_electric: false,
  last_checked_at: null,
  found_count: 0,
  created_at: "2026-08-15T10:00:00Z",
};

const mockSearchResults: SearchResult[] = [
  {
    id: "camp-1",
    entity_type: "Campground",
    provider_id: 1,
    provider_name: "Recreation.gov",
    recreation_area_id: "rec-1",
    recreation_area_name: "Yosemite National Park",
    campground_id: "camp-1",
    campground_name: "Upper Pines Campground",
  },
  {
    id: "rec-1",
    entity_type: "RecreationArea",
    provider_id: 1,
    provider_name: "Recreation.gov",
    recreation_area_id: "rec-1",
    recreation_area_name: "Yosemite National Park",
    campground_id: null,
    campground_name: null,
  },
];

const mockRegularUser = {
  id: "user-1",
  email: "camper@camply.app",
  is_invited: true,
  is_admin: false,
  scanning_enabled: true,
  pushover_token: null,
};

const mockAdminUser = {
  id: "admin-1",
  email: "admin@camply.app",
  is_invited: true,
  is_admin: true,
  scanning_enabled: true,
  pushover_token: null,
};

describe("UI Component DOM Snapshots", () => {
  beforeAll(() => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date(FIXED_TIME));
    window.HTMLElement.prototype.scrollIntoView = vi.fn();
    window.scrollTo = vi.fn();
  });

  afterAll(() => {
    vi.useRealTimers();
  });

  describe("CamplyLogo", () => {
    it("matches snapshot for horizontal variant", () => {
      const { asFragment } = render(<CamplyLogo height={40} />);
      expect(asFragment()).toMatchSnapshot();
    });

    it("matches snapshot for stacked variant", () => {
      const { asFragment } = render(
        <CamplyLogo variant="stacked" height={128} className="custom-class" />,
      );
      expect(asFragment()).toMatchSnapshot();
    });

    it("matches snapshot for icon-only variant", () => {
      const { asFragment } = render(<CamplyLogo variant="icon" height={48} />);
      expect(asFragment()).toMatchSnapshot();
    });
  });

  describe("DismissibleBanner", () => {
    it("matches snapshot when visible", () => {
      const { asFragment } = render(
        <DismissibleBanner id="test-banner" storageType="session">
          <p>Important update announcement</p>
        </DismissibleBanner>,
      );
      expect(asFragment()).toMatchSnapshot();
    });
  });

  describe("AdminFeedback", () => {
    it("matches snapshot for success message", () => {
      const { asFragment } = render(
        <AdminFeedback message="User privileges updated successfully." />,
      );
      expect(asFragment()).toMatchSnapshot();
    });

    it("matches snapshot for error message", () => {
      const { asFragment } = render(
        <AdminFeedback
          message="Failed to communicate with provider API."
          error
        />,
      );
      expect(asFragment()).toMatchSnapshot();
    });
  });

  describe("AdminPagination", () => {
    it("matches snapshot for first page", () => {
      const { asFragment } = render(
        <AdminPagination page={0} pageSize={25} total={100} onPage={vi.fn()} />,
      );
      expect(asFragment()).toMatchSnapshot();
    });

    it("matches snapshot for last page", () => {
      const { asFragment } = render(
        <AdminPagination page={3} pageSize={25} total={100} onPage={vi.fn()} />,
      );
      expect(asFragment()).toMatchSnapshot();
    });

    it("matches snapshot for empty records", () => {
      const { asFragment } = render(
        <AdminPagination page={0} pageSize={25} total={0} onPage={vi.fn()} />,
      );
      expect(asFragment()).toMatchSnapshot();
    });
  });

  describe("AdminNav", () => {
    it("matches snapshot on admin overview", () => {
      const { asFragment } = render(
        <MemoryRouter initialEntries={["/admin"]}>
          <AdminNav />
        </MemoryRouter>,
      );
      expect(asFragment()).toMatchSnapshot();
    });

    it("matches snapshot on admin operations", () => {
      const { asFragment } = render(
        <MemoryRouter initialEntries={["/admin/operations"]}>
          <AdminNav />
        </MemoryRouter>,
      );
      expect(asFragment()).toMatchSnapshot();
    });
  });

  describe("ScanCard", () => {
    it("matches snapshot for active scan with filters", () => {
      const { asFragment } = render(
        <MemoryRouter>
          <ScanCard
            scan={mockActiveScan}
            onToggleActive={vi.fn()}
            onDelete={vi.fn()}
          />
        </MemoryRouter>,
      );
      expect(asFragment()).toMatchSnapshot();
    });

    it("matches snapshot for paused scan", () => {
      const { asFragment } = render(
        <MemoryRouter>
          <ScanCard
            scan={mockPausedScan}
            onToggleActive={vi.fn()}
            onDelete={vi.fn()}
          />
        </MemoryRouter>,
      );
      expect(asFragment()).toMatchSnapshot();
    });

    it("matches snapshot for ended scan", () => {
      const { asFragment } = render(
        <MemoryRouter>
          <ScanCard
            scan={mockEndedScan}
            onToggleActive={vi.fn()}
            onDelete={vi.fn()}
          />
        </MemoryRouter>,
      );
      expect(asFragment()).toMatchSnapshot();
    });
  });

  describe("Header", () => {
    it("matches snapshot for unauthenticated visitor", () => {
      mockAuthState = { ...mockAuthState, user: null, isAdmin: false };
      const { asFragment } = render(
        <ThemeProviderContext.Provider value={mockThemeContext}>
          <MemoryRouter>
            <Header />
          </MemoryRouter>
        </ThemeProviderContext.Provider>,
      );
      expect(asFragment()).toMatchSnapshot();
    });

    it("matches snapshot for authenticated user", () => {
      mockAuthState = {
        ...mockAuthState,
        user: mockRegularUser,
        isAdmin: false,
      };
      const { asFragment } = render(
        <ThemeProviderContext.Provider value={mockThemeContext}>
          <MemoryRouter>
            <Header />
          </MemoryRouter>
        </ThemeProviderContext.Provider>,
      );
      expect(asFragment()).toMatchSnapshot();
    });

    it("matches snapshot for authenticated admin", () => {
      mockAuthState = { ...mockAuthState, user: mockAdminUser, isAdmin: true };
      const { asFragment } = render(
        <ThemeProviderContext.Provider value={mockThemeContext}>
          <MemoryRouter>
            <Header />
          </MemoryRouter>
        </ThemeProviderContext.Provider>,
      );
      expect(asFragment()).toMatchSnapshot();
    });

    it("matches snapshot without logo", () => {
      mockAuthState = { ...mockAuthState, user: null, isAdmin: false };
      const { asFragment } = render(
        <ThemeProviderContext.Provider value={mockThemeContext}>
          <MemoryRouter>
            <Header showLogo={false} />
          </MemoryRouter>
        </ThemeProviderContext.Provider>,
      );
      expect(asFragment()).toMatchSnapshot();
    });
  });

  describe("SearchDropdown", () => {
    it("matches snapshot for loading state", () => {
      const { asFragment } = render(
        <SearchDropdown
          results={[]}
          isLoading={true}
          error={null}
          query="yosemite"
          isOpen={true}
          onSelect={vi.fn()}
        />,
      );
      expect(asFragment()).toMatchSnapshot();
    });

    it("matches snapshot for empty results", () => {
      const { asFragment } = render(
        <SearchDropdown
          results={[]}
          isLoading={false}
          error={null}
          query="nonexistent"
          isOpen={true}
          onSelect={vi.fn()}
        />,
      );
      expect(asFragment()).toMatchSnapshot();
    });

    it("matches snapshot with search results", () => {
      const { asFragment } = render(
        <SearchDropdown
          results={mockSearchResults}
          isLoading={false}
          error={null}
          query="yosemite"
          isOpen={true}
          onSelect={vi.fn()}
        />,
      );
      expect(asFragment()).toMatchSnapshot();
    });

    it("matches snapshot with selected index", () => {
      const { asFragment } = render(
        <SearchDropdown
          results={mockSearchResults}
          isLoading={false}
          error={null}
          query="yosemite"
          isOpen={true}
          selectedIndex={0}
          onSelect={vi.fn()}
        />,
      );
      expect(asFragment()).toMatchSnapshot();
    });

    it("matches snapshot for error state", () => {
      const { asFragment } = render(
        <SearchDropdown
          results={[]}
          isLoading={false}
          error={new Error("Network failed")}
          query="yosemite"
          isOpen={true}
          onSelect={vi.fn()}
        />,
      );
      expect(asFragment()).toMatchSnapshot();
    });
  });

  describe("CollapsibleDescription", () => {
    it("matches snapshot for empty description fallback", () => {
      const { asFragment } = render(
        <CollapsibleDescription
          description={null}
          fallback="No description provided"
        />,
      );
      expect(asFragment()).toMatchSnapshot();
    });

    it("matches snapshot for short plain text", () => {
      const { asFragment } = render(
        <CollapsibleDescription description="Short description text." />,
      );
      expect(asFragment()).toMatchSnapshot();
    });

    it("matches snapshot for long plain text", () => {
      const longText =
        "This is an extensive campground description detailing the scenic views, surrounding pine trees, nearby hiking trails, river access points, campfire rings, check-in requirements, and seasonal closures across Yosemite National Park.";
      const { asFragment } = render(
        <CollapsibleDescription description={longText} />,
      );
      expect(asFragment()).toMatchSnapshot();
    });

    it("matches snapshot for HTML content", () => {
      const htmlText =
        "<p>Upper Pines is nestled in <strong>Yosemite Valley</strong>.</p><p>Features running water and fire pits.</p>";
      const { asFragment } = render(
        <CollapsibleDescription description={htmlText} />,
      );
      expect(asFragment()).toMatchSnapshot();
    });
  });

  describe("UI Primitives", () => {
    it("matches snapshot for button variants and sizes", () => {
      const { asFragment } = render(
        <div className="flex flex-col gap-2">
          <Button variant="default">Default</Button>
          <Button variant="secondary">Secondary</Button>
          <Button variant="destructive">Destructive</Button>
          <Button variant="outline">Outline</Button>
          <Button variant="ghost">Ghost</Button>
          <Button variant="link">Link</Button>
          <Button size="sm">Small</Button>
          <Button size="lg">Large</Button>
          <Button size="icon">Icon</Button>
        </div>,
      );
      expect(asFragment()).toMatchSnapshot();
    });

    it("matches snapshot for badge variants", () => {
      const { asFragment } = render(
        <div className="flex gap-2">
          <Badge variant="default">Default</Badge>
          <Badge variant="secondary">Secondary</Badge>
          <Badge variant="destructive">Destructive</Badge>
          <Badge variant="outline">Outline</Badge>
        </div>,
      );
      expect(asFragment()).toMatchSnapshot();
    });

    it("matches snapshot for card structure", () => {
      const { asFragment } = render(
        <Card className="w-[350px]">
          <CardHeader>
            <CardTitle>Card Title</CardTitle>
            <CardDescription>Card Description</CardDescription>
          </CardHeader>
          <CardContent>
            <p>Card content text.</p>
          </CardContent>
          <CardFooter>
            <Button size="sm">Footer Action</Button>
          </CardFooter>
        </Card>,
      );
      expect(asFragment()).toMatchSnapshot();
    });

    it("matches snapshot for switch states", () => {
      const { asFragment } = render(
        <div className="flex flex-col gap-2">
          <Switch checked={true} aria-label="Checked switch" />
          <Switch checked={false} aria-label="Unchecked switch" />
          <Switch disabled aria-label="Disabled switch" />
        </div>,
      );
      expect(asFragment()).toMatchSnapshot();
    });
  });

  describe("DevPreview Catalog", () => {
    it("matches snapshot for design system catalog", () => {
      const { asFragment } = render(
        <MemoryRouter>
          <DevPreview />
        </MemoryRouter>,
      );
      expect(asFragment()).toMatchSnapshot();
    });
  });
});
