import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { expect, it, vi } from "vitest";
import { useState } from "react";
import { AreaCoveragePicker } from "./AreaCoveragePicker";
import { getMonitoringCampgrounds } from "@/lib/api";

vi.mock("@/lib/api", () => ({ getMonitoringCampgrounds: vi.fn() }));
it("retains selected IDs across choice pages and queries", async () => {
  vi.mocked(getMonitoringCampgrounds).mockImplementation(
    async (_provider, area, params = {}) => ({
      items: [
        {
          id: params.offset ? "051" : "001",
          provider_id: 1,
          recreation_area_id: area,
          name: params.offset ? "Second page" : "First page",
        },
      ],
      total: 51,
      eligible_total: 51,
      has_more: !params.offset,
      limit: 50,
      offset: params.offset ?? 0,
      catalog_revision: 1,
    }),
  );
  function Draft() {
    const [selected, setSelected] = useState<Record<string, string>>({});
    return (
      <AreaCoveragePicker
        providerId={1}
        areaId="area"
        mode="selected"
        onModeChange={() => {}}
        selected={selected}
        onSelectedChange={setSelected}
      />
    );
  }
  render(
    <QueryClientProvider client={new QueryClient()}>
      <Draft />
    </QueryClientProvider>,
  );
  const user = userEvent.setup();
  expect(
    await screen.findByText("51 eligible campgrounds."),
  ).toBeInTheDocument();
  expect(
    screen.queryByText(/automatically includes future eligible campgrounds/i),
  ).not.toBeInTheDocument();

  const trigger = screen.getByRole("button", { name: "Select campgrounds…" });
  expect(trigger).toHaveAttribute("aria-expanded", "false");
  await user.click(trigger);
  expect(trigger).toHaveAttribute("aria-expanded", "true");

  await user.click(await screen.findByRole("checkbox", { name: "First page" }));
  await user.click(screen.getByRole("button", { name: "Next campgrounds" }));
  await user.click(
    await screen.findByRole("checkbox", { name: "Second page" }),
  );
  expect(screen.getByRole("status")).toHaveTextContent("2 selected");
  expect(
    screen.getByRole("button", { name: "2 campgrounds selected" }),
  ).toBeInTheDocument();
  await user.type(screen.getByRole("searchbox"), "other");
  await waitFor(() =>
    expect(
      screen.getByRole("button", { name: "Remove First page" }),
    ).toBeInTheDocument(),
  );
  await user.keyboard("{Escape}");
  expect(screen.queryByRole("searchbox")).not.toBeInTheDocument();
  expect(
    screen.getByRole("button", { name: "Remove First page" }),
  ).toBeInTheDocument();
});
