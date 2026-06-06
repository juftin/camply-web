import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { ScanCard } from "./ScanCard";
import type { ScanResponse } from "@/lib/structs";

const baseScan: ScanResponse = {
  id: "test-scan-1",
  provider_id: 1,
  campground_id: "cg-1",
  campground_name: "Lower Pines Campground",
  recreation_area_name: "Yosemite National Park",
  start_date: "2026-07-01",
  end_date: "2026-07-05",
  is_active: true,
  min_stay_length: 1,
  preferred_types: [],
  require_electric: false,
  last_checked_at: null,
  found_count: 0,
  created_at: "2026-06-01T00:00:00Z",
};

describe("ScanCard", () => {
  it("renders campground name", () => {
    render(
      <ScanCard
        scan={baseScan}
        onToggleActive={vi.fn()}
        onDelete={vi.fn()}
      />,
    );
    expect(screen.getByText("Lower Pines Campground")).toBeInTheDocument();
  });

  it("shows recreation area name", () => {
    render(
      <ScanCard
        scan={baseScan}
        onToggleActive={vi.fn()}
        onDelete={vi.fn()}
      />,
    );
    expect(screen.getByText("Yosemite National Park")).toBeInTheDocument();
  });

  it("shows active badge for active scan", () => {
    render(
      <ScanCard
        scan={baseScan}
        onToggleActive={vi.fn()}
        onDelete={vi.fn()}
      />,
    );
    // Both the Badge and the switch label say "Active" — get the badge div
    const badges = screen.getAllByText("Active");
    expect(badges.length).toBeGreaterThanOrEqual(1);
  });

  it("shows paused badge for inactive scan", () => {
    render(
      <ScanCard
        scan={{ ...baseScan, is_active: false }}
        onToggleActive={vi.fn()}
        onDelete={vi.fn()}
      />,
    );
    const badges = screen.getAllByText("Paused");
    expect(badges.length).toBeGreaterThanOrEqual(1);
  });

  it("shows found count", () => {
    render(
      <ScanCard
        scan={{ ...baseScan, found_count: 5 }}
        onToggleActive={vi.fn()}
        onDelete={vi.fn()}
      />,
    );
    expect(screen.getByText("5")).toBeInTheDocument();
  });

  it("renders last checked time when available", () => {
    const now = new Date().toISOString();
    render(
      <ScanCard
        scan={{ ...baseScan, last_checked_at: now }}
        onToggleActive={vi.fn()}
        onDelete={vi.fn()}
      />,
    );
    expect(screen.getByText(/Last checked:/)).toBeInTheDocument();
  });

  it("shows electric badge when required", () => {
    render(
      <ScanCard
        scan={{ ...baseScan, require_electric: true }}
        onToggleActive={vi.fn()}
        onDelete={vi.fn()}
      />,
    );
    expect(screen.getByText(/Electric/)).toBeInTheDocument();
  });

  it("shows min stay badge when > 1", () => {
    render(
      <ScanCard
        scan={{ ...baseScan, min_stay_length: 3 }}
        onToggleActive={vi.fn()}
        onDelete={vi.fn()}
      />,
    );
    expect(screen.getByText(/Min 3 nights/)).toBeInTheDocument();
  });

  it("calls onToggleActive when switch is clicked", async () => {
    const onToggle = vi.fn();
    render(
      <ScanCard
        scan={baseScan}
        onToggleActive={onToggle}
        onDelete={vi.fn()}
      />,
    );
    // The switch should have an id matching active-{scan.id}
    const switchEl = screen.getByRole("switch");
    switchEl.click();
    expect(onToggle).toHaveBeenCalledWith("test-scan-1", false);
  });

  it("calls onDelete when delete button is clicked", () => {
    const onDelete = vi.fn();
    render(
      <ScanCard
        scan={baseScan}
        onToggleActive={vi.fn()}
        onDelete={onDelete}
      />,
    );
    const deleteBtn = screen.getByRole("button", { name: "" });
    deleteBtn.click();
    expect(onDelete).toHaveBeenCalledWith("test-scan-1");
  });
});
