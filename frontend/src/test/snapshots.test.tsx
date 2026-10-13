/**
 * Automated DOM snapshot tests for Camply UI components.
 *
 * Verifies DOM structure, layout primitives, and component variants
 * to catch unintended markup regressions during frontend builds.
 */

import { render } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterAll, beforeAll, describe, expect, it, vi } from "vitest";

import { CamplyLogo } from "@/components/CamplyLogo";
import { DismissibleBanner } from "@/components/DismissibleBanner";
import { AdminNav } from "@/components/AdminNav";
import { AdminFeedback } from "@/components/admin/AdminFeedback";
import { AdminPagination } from "@/components/admin/AdminPagination";
import { ScanCard } from "@/components/ScanCard";
import { DevPreview } from "@/pages/DevPreview";
import type { ScanResponse } from "@/lib/structs";

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

describe("UI Component DOM Snapshots", () => {
  beforeAll(() => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date(FIXED_TIME));
  });

  afterAll(() => {
    vi.useRealTimers();
  });

  describe("CamplyLogo", () => {
    it("matches snapshot for SVG variant", () => {
      const { asFragment } = render(<CamplyLogo width={40} height={40} />);
      expect(asFragment()).toMatchSnapshot();
    });

    it("matches snapshot for PNG variant", () => {
      const { asFragment } = render(
        <CamplyLogo
          variant="png"
          width={48}
          height={48}
          className="custom-class"
        />,
      );
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
