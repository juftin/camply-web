import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { beforeEach, describe, expect, it, vi } from "vitest";
import {
  createScan,
  listScans,
  searchCampgrounds,
  updateScan,
} from "@/lib/api";
import { useScans } from "@/hooks/useScans";
import type { ScanListResponse, ScanResponse } from "@/lib/structs";
import { ScanForm } from "./ScanForm";

let scanningEnabled = true;
vi.mock("@/hooks/useAuth", () => ({
  useAuth: () => ({ user: { scanning_enabled: scanningEnabled } }),
}));
vi.mock("@/lib/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/api")>()),
  createScan: vi.fn(),
  listScans: vi.fn(),
  updateScan: vi.fn(),
  searchCampgrounds: vi.fn(),
}));

const savedScan: ScanResponse = {
  id: "editable-scan",
  provider_id: 1,
  campground_id: "original-campground",
  campground_name: "Original Campground",
  recreation_area_name: "Synthetic Park",
  start_date: "2027-07-01",
  end_date: "2027-07-08",
  min_stay_length: 2,
  preferred_types: ["RV", "CUSTOM TYPE"],
  require_electric: true,
  is_active: false,
  last_checked_at: null,
  found_count: 0,
  created_at: "2027-01-01T00:00:00Z",
};

function renderForm(scan: ScanResponse | undefined = savedScan) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  const props = scan ? { scan } : {};
  const view = render(
    <QueryClientProvider client={client}>
      <ScanForm {...props} />
    </QueryClientProvider>,
  );
  return { client, ...view };
}

beforeEach(() => {
  vi.clearAllMocks();
  scanningEnabled = true;
  vi.mocked(updateScan).mockResolvedValue(savedScan);
  vi.mocked(createScan).mockResolvedValue(savedScan);
  vi.mocked(listScans).mockResolvedValue({ scans: [savedScan], total: 1 });
});

describe("ScanForm editing", () => {
  it("waits for active scan queries to refresh before closing", async () => {
    const user = userEvent.setup();
    let complete!: (list: ScanListResponse) => void;
    const initialList = { scans: [savedScan], total: 1 };
    vi.mocked(listScans)
      .mockResolvedValueOnce(initialList)
      .mockReturnValueOnce(
        new Promise((resolve) => {
          complete = resolve;
        }),
      );
    const ActiveList = () => {
      useScans();
      return null;
    };
    render(
      <QueryClientProvider client={new QueryClient()}>
        <ActiveList />
        <ScanForm scan={savedScan} />
      </QueryClientProvider>,
    );
    await waitFor(() => expect(listScans).toHaveBeenCalledTimes(1));
    await user.click(screen.getByRole("button", { name: "Edit Scan" }));
    await user.click(screen.getByRole("button", { name: "Save Changes" }));
    await waitFor(() => expect(listScans).toHaveBeenCalledTimes(2));
    expect(screen.getByRole("button", { name: "Saving..." })).toBeDisabled();
    expect(screen.getByRole("dialog")).toBeInTheDocument();
    complete(initialList);
    await waitFor(() =>
      expect(screen.queryByRole("dialog")).not.toBeInTheDocument(),
    );
  });

  it("prefills saved values and saves through PATCH, refreshing list and detail caches", async () => {
    const user = userEvent.setup();
    const { client } = renderForm();
    const listKey = ["scans", "list"];
    const detailKey = ["scans", "detail", savedScan.id];
    client.setQueryData(listKey, { scans: [savedScan], total: 1 });
    client.setQueryData(detailKey, { ...savedScan, results: [] });
    await user.click(screen.getByRole("button", { name: "Edit Scan" }));
    expect(screen.getByText("Original Campground")).toBeInTheDocument();
    expect(screen.getByLabelText("Check-in")).toHaveValue(savedScan.start_date);
    expect(screen.getByLabelText("Check-out")).toHaveValue(savedScan.end_date);
    expect(screen.getByLabelText("Minimum Stay (nights)")).toHaveValue(2);
    expect(screen.getByRole("switch")).toBeChecked();

    fireEvent.change(screen.getByLabelText("Check-out"), {
      target: { value: "2027-07-10" },
    });
    fireEvent.change(screen.getByLabelText("Minimum Stay (nights)"), {
      target: { value: "3" },
    });
    await user.click(screen.getByText("Tent", { selector: "div" }));
    await user.click(screen.getByRole("switch"));
    await user.click(screen.getByRole("button", { name: "Save Changes" }));
    await waitFor(() =>
      expect(updateScan).toHaveBeenCalledWith(savedScan.id, {
        provider_id: 1,
        campground_id: savedScan.campground_id,
        start_date: savedScan.start_date,
        end_date: "2027-07-10",
        min_stay_length: 3,
        preferred_types: ["RV", "CUSTOM TYPE", "TENT"],
        require_electric: false,
      }),
    );
    expect(createScan).not.toHaveBeenCalled();
    await waitFor(() =>
      expect(screen.queryByRole("dialog")).not.toBeInTheDocument(),
    );
    expect(client.getQueryState(listKey)?.isInvalidated).toBe(true);
    expect(client.getQueryState(detailKey)?.isInvalidated).toBe(true);
  });

  it("changes campground and provider using the existing search", async () => {
    const user = userEvent.setup();
    vi.mocked(searchCampgrounds).mockResolvedValue([
      {
        id: "Campground/3/new-campground",
        entity_type: "Campground",
        provider_id: 3,
        provider_name: "Synthetic Provider",
        campground_id: "new-campground",
        campground_name: "New Campground",
        recreation_area_id: null,
        recreation_area_name: null,
      },
    ]);
    renderForm();
    await user.click(screen.getByRole("button", { name: "Edit Scan" }));
    await user.click(screen.getByRole("button", { name: "Change" }));
    await user.type(
      screen.getByPlaceholderText("Search for a campground..."),
      "new",
    );
    await user.click(
      await screen.findByRole("button", { name: "New Campground" }),
    );
    await user.click(screen.getByRole("button", { name: "Save Changes" }));
    await waitFor(() =>
      expect(updateScan).toHaveBeenCalledWith(
        savedScan.id,
        expect.objectContaining({
          provider_id: 3,
          campground_id: "new-campground",
        }),
      ),
    );
  });

  it("discards cancelled edits and refreshes saved values when reopened", async () => {
    const user = userEvent.setup();
    const { rerender, client } = renderForm();
    await user.click(screen.getByRole("button", { name: "Edit Scan" }));
    fireEvent.change(screen.getByLabelText("Check-in"), {
      target: { value: "2027-07-03" },
    });
    await user.click(screen.getByRole("button", { name: "Change" }));
    await user.click(screen.getByRole("button", { name: "Cancel" }));
    expect(updateScan).not.toHaveBeenCalled();
    rerender(
      <QueryClientProvider client={client}>
        <ScanForm scan={{ ...savedScan, end_date: "2027-07-12" }} />
      </QueryClientProvider>,
    );
    await user.click(screen.getByRole("button", { name: "Edit Scan" }));
    expect(screen.getByLabelText("Check-in")).toHaveValue(savedScan.start_date);
    expect(screen.getByLabelText("Check-out")).toHaveValue("2027-07-12");
    expect(screen.getByText("Original Campground")).toBeInTheDocument();
  });

  it("validates dates before submitting", async () => {
    const user = userEvent.setup();
    renderForm();
    await user.click(screen.getByRole("button", { name: "Edit Scan" }));
    fireEvent.change(screen.getByLabelText("Check-out"), {
      target: { value: savedScan.start_date },
    });
    await user.click(screen.getByRole("button", { name: "Save Changes" }));
    expect(
      await screen.findByText("Check-out must be after check-in"),
    ).toBeInTheDocument();
    expect(updateScan).not.toHaveBeenCalled();
  });

  it("preserves edits on failure and allows retry", async () => {
    const user = userEvent.setup();
    vi.mocked(updateScan).mockRejectedValueOnce(
      new Error("A scan already exists"),
    );
    renderForm();
    await user.click(screen.getByRole("button", { name: "Edit Scan" }));
    fireEvent.change(screen.getByLabelText("Check-out"), {
      target: { value: "2027-07-10" },
    });
    await user.click(screen.getByRole("button", { name: "Save Changes" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "A scan already exists",
    );
    expect(screen.getByLabelText("Check-out")).toHaveValue("2027-07-10");
    await user.click(screen.getByRole("button", { name: "Save Changes" }));
    await waitFor(() =>
      expect(screen.queryByRole("dialog")).not.toBeInTheDocument(),
    );
    expect(updateScan).toHaveBeenCalledTimes(2);
  });

  it("disables repeat saves and closing while the update is pending", async () => {
    const user = userEvent.setup();
    let complete!: (scan: ScanResponse) => void;
    vi.mocked(updateScan).mockReturnValue(
      new Promise((resolve) => {
        complete = resolve;
      }),
    );
    renderForm();
    await user.click(screen.getByRole("button", { name: "Edit Scan" }));
    await user.click(screen.getByRole("button", { name: "Save Changes" }));
    expect(screen.getByRole("button", { name: "Saving..." })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Cancel" })).toBeDisabled();
    await user.keyboard("{Escape}");
    expect(screen.getByRole("dialog")).toBeInTheDocument();
    complete(savedScan);
    await waitFor(() =>
      expect(screen.queryByRole("dialog")).not.toBeInTheDocument(),
    );
    expect(updateScan).toHaveBeenCalledTimes(1);
  });

  it("allows suspended users to edit saved scans", async () => {
    const user = userEvent.setup();
    scanningEnabled = false;
    renderForm();
    await user.click(screen.getByRole("button", { name: "Edit Scan" }));
    await user.click(screen.getByRole("button", { name: "Save Changes" }));
    await waitFor(() => expect(updateScan).toHaveBeenCalledTimes(1));
  });

  it("still creates new scans with POST", async () => {
    const user = userEvent.setup();
    const { client, rerender } = renderForm();
    rerender(
      <QueryClientProvider client={client}>
        <ScanForm
          preselectedCampground={{
            id: "new-campground",
            provider_id: 3,
            name: "New Campground",
            recreation_area_id: null,
            description: null,
            country: null,
            state: null,
            longitude: null,
            latitude: null,
            reservable: true,
            enabled: true,
            url: "",
          }}
          preselectedProviderId={3}
        />
      </QueryClientProvider>,
    );
    await user.click(screen.getByRole("button", { name: "New Scan" }));
    fireEvent.change(screen.getByLabelText("Check-in"), {
      target: { value: "2027-08-01" },
    });
    fireEvent.change(screen.getByLabelText("Check-out"), {
      target: { value: "2027-08-05" },
    });
    await user.click(screen.getByRole("button", { name: "Create Scan" }));
    await waitFor(() =>
      expect(createScan).toHaveBeenCalledWith(
        expect.objectContaining({
          provider_id: 3,
          campground_id: "new-campground",
          start_date: "2027-08-01",
          end_date: "2027-08-05",
        }),
      ),
    );
    expect(updateScan).not.toHaveBeenCalled();
  });
});
