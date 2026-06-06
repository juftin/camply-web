import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import React from "react";
import { ScanCard } from "./ScanCard";
import type { ScanResponse } from "@/lib/structs";

function renderWithRouter(ui: React.ReactElement) {
  return render(ui, { wrapper: MemoryRouter });
}

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
    renderWithRouter(
      <ScanCard
        scan={baseScan}
        onToggleActive={vi.fn()}
        onDelete={vi.fn()}
      />,
    );
    expect(screen.getByText("Lower Pines Campground")).toBeInTheDocument();
  });

  it("shows recreation area name", () => {
    renderWithRouter(
      <ScanCard
        scan={baseScan}
        onToggleActive={vi.fn()}
        onDelete={vi.fn()}
      />,
    );
    expect(screen.getByText("Yosemite National Park")).toBeInTheDocument();
  });

  it("shows active badge for active scan", () => {
    renderWithRouter(
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
    renderWithRouter(
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
    renderWithRouter(
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
    renderWithRouter(
      <ScanCard
        scan={{ ...baseScan, last_checked_at: now }}
        onToggleActive={vi.fn()}
        onDelete={vi.fn()}
      />,
    );
    expect(screen.getByText(/Last checked:/)).toBeInTheDocument();
  });

  it("shows electric badge when required", () => {
    renderWithRouter(
      <ScanCard
        scan={{ ...baseScan, require_electric: true }}
        onToggleActive={vi.fn()}
        onDelete={vi.fn()}
      />,
    );
    expect(screen.getByText(/Electric/)).toBeInTheDocument();
  });

  it("shows min stay badge when > 1", () => {
    renderWithRouter(
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
    renderWithRouter(
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

  it("calls onDelete after confirmation", async () => {
    const onDelete = vi.fn();
    renderWithRouter(
      <ScanCard
        scan={baseScan}
        onToggleActive={vi.fn()}
        onDelete={onDelete}
      />,
    );
    // Click the trash icon button to open the confirmation dialog
    const trashBtn = screen.getByRole("button", { name: "" });
    trashBtn.click();
    // Wait for the confirmation dialog to appear and click "Delete"
    const confirmBtn = await screen.findByRole("button", { name: "Delete" });
    confirmBtn.click();
    expect(onDelete).toHaveBeenCalledWith("test-scan-1");
  });
});
