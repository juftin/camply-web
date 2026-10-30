import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { useScans } from "@/hooks/useScans";
import type { ScanResponse } from "@/lib/structs";
import { Dashboard } from "./Dashboard";

vi.mock("@/hooks/useAuth", () => ({
  useAuth: () => ({
    user: { scanning_enabled: true },
    isReady: true,
    autoLogin: true,
  }),
}));
vi.mock("@/hooks/useScans", () => ({
  useScans: vi.fn(),
  useUpdateScan: () => ({}),
  useDeleteScan: () => ({}),
}));
vi.mock("@/components/ScanForm", () => ({ ScanForm: () => null }));
vi.mock("@/components/ScanCard", () => ({
  ScanCard: ({ scan }: { scan: ScanResponse }) => (
    <a href={`/dashboard/scans/${scan.id}`}>Scan {scan.id}</a>
  ),
}));

const baseScan: ScanResponse = {
  id: "one",
  provider_id: 1,
  campground_id: "camp",
  campground_name: "Synthetic Pines",
  recreation_area_name: "Synthetic Park",
  start_date: "2027-07-01",
  end_date: "2027-07-05",
  is_active: true,
  min_stay_length: 1,
  preferred_types: [],
  require_electric: false,
  last_checked_at: null,
  found_count: 10,
  created_at: "2027-01-01T00:00:00Z",
};

describe("Dashboard campground groups", () => {
  beforeEach(() => {
    vi.mocked(useScans).mockReturnValue({
      data: {
        scans: [baseScan, { ...baseScan, id: "two", found_count: 0 }],
        total: 2,
      },
    } as ReturnType<typeof useScans>);
  });

  it("collapses scans into one campground summary and expands their links", async () => {
    const user = userEvent.setup();
    render(
      <MemoryRouter>
        <Dashboard />
      </MemoryRouter>,
    );
    const heading = screen.getByText("Synthetic Pines");
    const group = heading.closest("details");
    expect(group).not.toBeNull();
    expect(group).not.toHaveAttribute("open");
    expect(screen.getByText("2 scans")).toBeInTheDocument();
    expect(screen.getByText("1 scan with openings")).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: "Scan one", hidden: true }),
    ).not.toBeVisible();
    await user.click(heading);
    expect(group).toHaveAttribute("open");
    expect(screen.getByRole("link", { name: "Scan one" })).toHaveAttribute(
      "href",
      "/dashboard/scans/one",
    );
    expect(screen.getByRole("link", { name: "Scan two" })).toBeVisible();
    await user.click(heading);
    expect(group).not.toHaveAttribute("open");
  });

  it("keeps distinct campground and provider identities separate even when names match", () => {
    vi.mocked(useScans).mockReturnValue({
      data: {
        scans: [
          baseScan,
          { ...baseScan, id: "two", provider_id: 2 },
          { ...baseScan, id: "three", campground_id: "other" },
        ],
        total: 3,
      },
    } as ReturnType<typeof useScans>);
    const { container } = render(
      <MemoryRouter>
        <Dashboard />
      </MemoryRouter>,
    );
    const groups = container.querySelectorAll("details");
    expect(groups).toHaveLength(3);
    groups.forEach((group) =>
      expect(within(group).getAllByRole("link", { hidden: true })).toHaveLength(
        1,
      ),
    );
  });
});
