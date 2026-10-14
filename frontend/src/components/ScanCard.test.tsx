import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, useLocation } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { describe, expect, it, vi } from "vitest";
import React from "react";
import { ScanCard } from "./ScanCard";
import type { ScanResponse } from "@/lib/structs";

function renderWithRouter(ui: React.ReactElement) {
  function Location() {
    return <output data-testid="location">{useLocation().pathname}</output>;
  }
  return render(
    <QueryClientProvider client={new QueryClient()}>
      <MemoryRouter initialEntries={["/dashboard"]}>
        {ui}
        <Location />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

vi.mock("@/hooks/useAuth", () => ({
  useAuth: () => ({ user: { scanning_enabled: true } }),
}));

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
      <ScanCard scan={baseScan} onToggleActive={vi.fn()} onDelete={vi.fn()} />,
    );
    expect(screen.getByText("Lower Pines Campground")).toBeInTheDocument();
  });

  it("shows recreation area name", () => {
    renderWithRouter(
      <ScanCard scan={baseScan} onToggleActive={vi.fn()} onDelete={vi.fn()} />,
    );
    expect(screen.getByText("Yosemite National Park")).toBeInTheDocument();
  });

  it("shows active badge for active scan", () => {
    renderWithRouter(
      <ScanCard scan={baseScan} onToggleActive={vi.fn()} onDelete={vi.fn()} />,
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

  it("renders last checked time correctly for naive UTC timestamps without producing future relative time", () => {
    const naiveUtc = new Date(Date.now() - 30 * 1000)
      .toISOString()
      .replace("Z", "");
    renderWithRouter(
      <ScanCard
        scan={{ ...baseScan, last_checked_at: naiveUtc }}
        onToggleActive={vi.fn()}
        onDelete={vi.fn()}
      />,
    );
    expect(screen.getByText(/Last checked:/)).toBeInTheDocument();
    expect(screen.queryByText(/Last checked: in /)).not.toBeInTheDocument();
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
      <ScanCard scan={baseScan} onToggleActive={onToggle} onDelete={vi.fn()} />,
    );
    // The switch should have an id matching active-{scan.id}
    const switchEl = screen.getByRole("switch");
    switchEl.click();
    expect(onToggle).toHaveBeenCalledWith("test-scan-1", false);
  });

  it("calls onDelete after confirmation", async () => {
    const onDelete = vi.fn();
    renderWithRouter(
      <ScanCard scan={baseScan} onToggleActive={vi.fn()} onDelete={onDelete} />,
    );
    // Click the trash icon button to open the confirmation dialog
    const trashBtn = screen.getByRole("button", { name: "Delete scan" });
    trashBtn.click();
    // Wait for the confirmation dialog to appear and click "Delete"
    const confirmBtn = await screen.findByRole("button", { name: "Delete" });
    confirmBtn.click();
    expect(onDelete).toHaveBeenCalledWith("test-scan-1");
  });

  it("keeps controls and confirmation interactions on the dashboard", async () => {
    const user = userEvent.setup();
    const onDelete = vi.fn().mockResolvedValue(undefined);
    renderWithRouter(
      <ScanCard scan={baseScan} onToggleActive={vi.fn()} onDelete={onDelete} />,
    );
    await user.click(screen.getByRole("switch"));
    await user.click(screen.getByText("Active", { selector: "label" }));
    expect(screen.getByTestId("location")).toHaveTextContent(/^\/dashboard$/);
    await user.click(screen.getByRole("button", { name: "Delete scan" }));
    await user.click(screen.getByRole("button", { name: "Cancel" }));
    expect(onDelete).not.toHaveBeenCalled();
    expect(screen.getByTestId("location")).toHaveTextContent(/^\/dashboard$/);
    await user.click(screen.getByRole("button", { name: "Delete scan" }));
    await user.click(screen.getByRole("button", { name: "Delete" }));
    await waitFor(() =>
      expect(screen.queryByRole("dialog")).not.toBeInTheDocument(),
    );
    expect(screen.getByTestId("location")).toHaveTextContent(/^\/dashboard$/);
  });

  it("shows delete errors and lets the user retry", async () => {
    const user = userEvent.setup();
    const onDelete = vi
      .fn()
      .mockRejectedValueOnce(new Error("Delete failed"))
      .mockResolvedValueOnce(undefined);
    renderWithRouter(
      <ScanCard scan={baseScan} onToggleActive={vi.fn()} onDelete={onDelete} />,
    );
    await user.click(screen.getByRole("button", { name: "Delete scan" }));
    await user.click(screen.getByRole("button", { name: "Delete" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Delete failed");
    expect(screen.getByRole("dialog")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Delete" }));
    await waitFor(() =>
      expect(screen.queryByRole("dialog")).not.toBeInTheDocument(),
    );
    expect(onDelete).toHaveBeenCalledTimes(2);
  });

  it("keeps deletion pending until the request succeeds", async () => {
    const user = userEvent.setup();
    let complete!: () => void;
    const onDelete = vi.fn(
      () =>
        new Promise<void>((resolve) => {
          complete = resolve;
        }),
    );
    renderWithRouter(
      <ScanCard scan={baseScan} onToggleActive={vi.fn()} onDelete={onDelete} />,
    );
    await user.click(screen.getByRole("button", { name: "Delete scan" }));
    await user.click(screen.getByRole("button", { name: "Delete" }));
    expect(screen.getByRole("button", { name: "Deleting..." })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Cancel" })).toBeDisabled();
    expect(screen.getByRole("dialog")).toBeInTheDocument();
    complete();
    await waitFor(() =>
      expect(screen.queryByRole("dialog")).not.toBeInTheDocument(),
    );
    expect(onDelete).toHaveBeenCalledTimes(1);
  });

  it("opens the edit form without navigating and still links the scan body", async () => {
    const user = userEvent.setup();
    renderWithRouter(
      <ScanCard scan={baseScan} onToggleActive={vi.fn()} onDelete={vi.fn()} />,
    );
    await user.click(screen.getByRole("button", { name: "Edit scan" }));
    expect(
      screen.getByRole("dialog", { name: "Edit Scan" }),
    ).toBeInTheDocument();
    expect(screen.getByTestId("location")).toHaveTextContent(/^\/dashboard$/);
    await user.click(screen.getByRole("button", { name: "Cancel" }));
    await user.click(screen.getByRole("link"));
    expect(screen.getByTestId("location")).toHaveTextContent(
      "/dashboard/scans/test-scan-1",
    );
  });
});
