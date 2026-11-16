import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { beforeEach, describe, expect, it, vi } from "vitest";
import {
  createScan,
  getMonitoringCampgrounds,
  listProviders,
  listScans,
  searchCampgrounds,
  updateScan,
} from "@/lib/api";
import { useScans } from "@/hooks/useScans";
import type { ScanListResponse, ScanResponse } from "@/lib/structs";
import { ScanForm } from "./ScanForm";
import { formatDisplayDate } from "@/lib/utils";

let scanningEnabled = true;
vi.mock("@/hooks/useAuth", () => ({
  useAuth: () => ({
    isReady: true,
    user: { scanning_enabled: scanningEnabled },
  }),
}));
vi.mock("@/lib/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/api")>()),
  createScan: vi.fn(),
  getMonitoringCampgrounds: vi.fn(),
  listProviders: vi.fn(),
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

async function selectDate(
  user: ReturnType<typeof userEvent.setup>,
  label: string,
  date: string,
) {
  const [year, month, day] = date.split("-").map(Number);
  await user.click(screen.getByLabelText(label));
  fireEvent.change(screen.getByRole("combobox", { name: "Select year" }), {
    target: { value: String(year) },
  });
  fireEvent.change(screen.getByRole("combobox", { name: "Select month" }), {
    target: { value: String(month - 1) },
  });
  await user.click(screen.getByRole("button", { name: String(day) }));
}

beforeEach(() => {
  vi.clearAllMocks();
  scanningEnabled = true;
  vi.mocked(updateScan).mockResolvedValue(savedScan);
  vi.mocked(createScan).mockResolvedValue(savedScan);
  vi.mocked(listProviders).mockResolvedValue([]);
  vi.mocked(listScans).mockResolvedValue({ scans: [savedScan], total: 1 });
});

describe("ScanForm editing", () => {
  it("anchors checkout to an edited check-in and preserves the minimum stay", async () => {
    const user = userEvent.setup();
    renderForm();
    await user.click(screen.getByRole("button", { name: "Edit Scan" }));
    await selectDate(user, "Check-in", "2027-07-20");
    expect(screen.getByLabelText("Check-out")).toHaveTextContent(
      formatDisplayDate("2027-07-22"),
    );
    await user.click(screen.getByLabelText("Check-out"));
    expect(screen.getByRole("combobox", { name: "Select month" })).toHaveValue(
      "6",
    );
    expect(screen.getByRole("button", { name: "20" })).toBeDisabled();
    await user.click(screen.getByRole("button", { name: "3 nights" }));
    await user.click(screen.getByRole("button", { name: "Save Changes" }));
    await waitFor(() =>
      expect(updateScan).toHaveBeenCalledWith(
        savedScan.id,
        expect.objectContaining({
          start_date: "2027-07-20",
          end_date: "2027-07-23",
          min_stay_length: 2,
        }),
      ),
    );
  });

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
    expect(screen.getByLabelText("Check-in")).toHaveTextContent(
      formatDisplayDate(savedScan.start_date),
    );
    expect(screen.getByLabelText("Check-out")).toHaveTextContent(
      formatDisplayDate(savedScan.end_date),
    );
    expect(screen.getByLabelText("Minimum Stay (nights)")).toHaveValue(2);
    expect(
      screen.getByRole("switch", { name: "Electric Hookup Required" }),
    ).toBeChecked();

    await selectDate(user, "Check-out", "2027-07-10");
    fireEvent.change(screen.getByLabelText("Minimum Stay (nights)"), {
      target: { value: "3" },
    });
    await user.click(screen.getByText("Tent", { selector: "div" }));
    await user.click(
      screen.getByRole("switch", { name: "Electric Hookup Required" }),
    );
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
        require_accessible: false,
        min_rv_length: null,
        allowed_weekdays: [0, 1, 2, 3, 4, 5, 6],
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
    await selectDate(user, "Check-in", "2027-07-03");
    await user.click(screen.getByRole("button", { name: "Change" }));
    await user.click(screen.getByRole("button", { name: "Cancel" }));
    expect(updateScan).not.toHaveBeenCalled();
    rerender(
      <QueryClientProvider client={client}>
        <ScanForm scan={{ ...savedScan, end_date: "2027-07-12" }} />
      </QueryClientProvider>,
    );
    await user.click(screen.getByRole("button", { name: "Edit Scan" }));
    expect(screen.getByLabelText("Check-in")).toHaveTextContent(
      formatDisplayDate(savedScan.start_date),
    );
    expect(screen.getByLabelText("Check-out")).toHaveTextContent(
      formatDisplayDate("2027-07-12"),
    );
    expect(screen.getByText("Original Campground")).toBeInTheDocument();
  });

  it("rejects a cleared checkout before submitting", async () => {
    const user = userEvent.setup();
    renderForm();
    await user.click(screen.getByRole("button", { name: "Edit Scan" }));
    await user.click(screen.getAllByRole("button", { name: "Clear date" })[1]);
    await user.click(screen.getByRole("button", { name: "Save Changes" }));
    expect(
      await screen.findByText("Check-out date is required"),
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
    await selectDate(user, "Check-out", "2027-07-10");
    await user.click(screen.getByRole("button", { name: "Save Changes" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "A scan already exists",
    );
    expect(screen.getByLabelText("Check-out")).toHaveTextContent(
      formatDisplayDate("2027-07-10"),
    );
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
    await selectDate(user, "Check-in", "2027-08-01");
    await selectDate(user, "Check-out", "2027-08-05");
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

  it("creates selected recreation area scan and supports editing coverage mode", async () => {
    const user = userEvent.setup();
    vi.mocked(getMonitoringCampgrounds).mockResolvedValue({
      items: [
        {
          id: "cg-10",
          provider_id: 1,
          recreation_area_id: "area-1",
          name: "Pine Creek",
        },
      ],
      total: 1,
      eligible_total: 2,
      limit: 50,
      offset: 0,
      has_more: false,
      catalog_revision: 1,
    });
    vi.mocked(createScan).mockResolvedValue({
      ...savedScan,
      destination_type: "recreation_area",
      recreation_area_id: "area-1",
      campground_id: null,
      coverage_mode: "selected",
      campground_ids: ["cg-10"],
    });
    const client = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
        mutations: { retry: false },
      },
    });
    const { rerender } = render(
      <QueryClientProvider client={client}>
        <ScanForm
          preselectedArea={{
            id: "area-1",
            name: "Synthetic Area",
            provider_id: 1,
          }}
          trigger={<button type="button">Monitor area</button>}
        />
      </QueryClientProvider>,
    );
    await user.click(screen.getByRole("button", { name: "Monitor area" }));
    await user.click(screen.getByLabelText("Selected campgrounds"));
    await user.click(
      screen.getByRole("button", { name: "Select campgrounds…" }),
    );
    await user.click(
      await screen.findByRole("checkbox", { name: "Pine Creek" }),
    );
    await user.keyboard("{Escape}");
    await selectDate(user, "Check-in", "2027-07-01");
    await selectDate(user, "Check-out", "2027-07-04");
    await user.click(screen.getByRole("button", { name: "Create Scan" }));
    await waitFor(() =>
      expect(createScan).toHaveBeenCalledWith(
        expect.objectContaining({
          provider_id: 1,
          destination_type: "recreation_area",
          recreation_area_id: "area-1",
          coverage_mode: "selected",
          campground_ids: ["cg-10"],
        }),
      ),
    );

    vi.mocked(updateScan).mockResolvedValue({
      ...savedScan,
      destination_type: "recreation_area",
      recreation_area_id: "area-1",
      campground_id: null,
      coverage_mode: "all",
    });
    rerender(
      <QueryClientProvider client={client}>
        <ScanForm
          scan={{
            ...savedScan,
            destination_type: "recreation_area",
            recreation_area_id: "area-1",
            destination_name: "Synthetic Area",
            campground_id: null,
            campground_name: null,
            coverage_mode: "selected",
            campground_ids: ["cg-10"],
            row_version: 3,
          }}
        />
      </QueryClientProvider>,
    );
    await user.click(screen.getByRole("button", { name: "Edit Scan" }));
    await user.click(screen.getByLabelText("All campgrounds"));
    await user.click(screen.getByRole("button", { name: "Save Changes" }));
    await waitFor(() =>
      expect(updateScan).toHaveBeenCalledWith(
        savedScan.id,
        expect.objectContaining({
          destination_type: "recreation_area",
          recreation_area_id: "area-1",
          coverage_mode: "all",
          row_version: 3,
        }),
      ),
    );
  });
});

describe("ScanForm nights of the week", () => {
  it("defaults legacy scans to any night and applies weekends without changing dates or stay length", async () => {
    const user = userEvent.setup();
    renderForm();
    await user.click(screen.getByRole("button", { name: "Edit Scan" }));
    for (const day of [
      "Monday",
      "Tuesday",
      "Wednesday",
      "Thursday",
      "Friday",
      "Saturday",
      "Sunday",
    ]) {
      expect(screen.getByRole("button", { name: day })).toHaveAttribute(
        "aria-pressed",
        "true",
      );
    }
    await user.click(screen.getByRole("button", { name: "Weekends" }));
    expect(screen.getByRole("button", { name: "Monday" })).toHaveAttribute(
      "aria-pressed",
      "false",
    );
    expect(screen.getByRole("button", { name: "Friday" })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
    expect(screen.getByRole("button", { name: "Saturday" })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
    expect(screen.getByLabelText("Minimum Stay (nights)")).toHaveValue(2);
    expect(screen.getByLabelText("Check-in")).toHaveTextContent(
      formatDisplayDate(savedScan.start_date),
    );
    expect(screen.getByLabelText("Check-out")).toHaveTextContent(
      formatDisplayDate(savedScan.end_date),
    );
    await user.click(screen.getByRole("button", { name: "Save Changes" }));
    await waitFor(() =>
      expect(updateScan).toHaveBeenCalledWith(
        savedScan.id,
        expect.objectContaining({ allowed_weekdays: [4, 5] }),
      ),
    );
  });

  it("restores saved nights and supports keyboard changes, cancel and any-night reset", async () => {
    const user = userEvent.setup();
    renderForm({ ...savedScan, allowed_weekdays: [0, 2], min_stay_length: 1 });
    await user.click(screen.getByRole("button", { name: "Edit Scan" }));
    const monday = screen.getByRole("button", { name: "Monday" });
    expect(monday).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByRole("button", { name: "Tuesday" })).toHaveAttribute(
      "aria-pressed",
      "false",
    );
    monday.focus();
    await user.keyboard(" ");
    expect(monday).toHaveAttribute("aria-pressed", "false");
    await user.click(screen.getByRole("button", { name: "Cancel" }));
    await user.click(screen.getByRole("button", { name: "Edit Scan" }));
    expect(screen.getByRole("button", { name: "Monday" })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
    await user.click(screen.getByRole("button", { name: "Any night" }));
    await user.click(screen.getByRole("button", { name: "Save Changes" }));
    await waitFor(() =>
      expect(updateScan).toHaveBeenCalledWith(
        savedScan.id,
        expect.objectContaining({ allowed_weekdays: [0, 1, 2, 3, 4, 5, 6] }),
      ),
    );
  });

  it("rejects an empty night selection without submitting", async () => {
    const user = userEvent.setup();
    renderForm({ ...savedScan, allowed_weekdays: [0], min_stay_length: 1 });
    await user.click(screen.getByRole("button", { name: "Edit Scan" }));
    await user.click(screen.getByRole("button", { name: "Monday" }));
    await user.click(screen.getByRole("button", { name: "Save Changes" }));
    expect(
      await screen.findByText("Select at least one night."),
    ).toBeInTheDocument();
    expect(updateScan).not.toHaveBeenCalled();
  });

  it("rejects impossible weekend stay lengths without silently widening the selection", async () => {
    const user = userEvent.setup();
    renderForm();
    await user.click(screen.getByRole("button", { name: "Edit Scan" }));
    await user.click(screen.getByRole("button", { name: "Weekends" }));
    fireEvent.change(screen.getByLabelText("Minimum Stay (nights)"), {
      target: { value: "3" },
    });
    await user.click(screen.getByRole("button", { name: "Save Changes" }));
    expect(
      await screen.findByText(
        /Extend the dates, select more nights, or reduce the stay length/,
      ),
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Sunday" })).toHaveAttribute(
      "aria-pressed",
      "false",
    );
    expect(updateScan).not.toHaveBeenCalled();
  });

  it("preserves custom nights through quick dates and a failed save", async () => {
    const user = userEvent.setup();
    vi.mocked(updateScan).mockRejectedValueOnce(new Error("Save unavailable"));
    renderForm({ ...savedScan, allowed_weekdays: [4, 5] });
    await user.click(screen.getByRole("button", { name: "Edit Scan" }));
    await user.click(screen.getByRole("button", { name: "Next Weekend" }));
    await user.click(screen.getByRole("button", { name: "Save Changes" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Save unavailable",
    );
    expect(screen.getByRole("button", { name: "Friday" })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
    expect(screen.getByRole("button", { name: "Sunday" })).toHaveAttribute(
      "aria-pressed",
      "false",
    );
    await user.click(screen.getByRole("button", { name: "Save Changes" }));
    await waitFor(() => expect(updateScan).toHaveBeenCalledTimes(2));
  });

  it("preserves selected_campgrounds labels and switches area scans to campground", async () => {
    const user = userEvent.setup();
    vi.mocked(getMonitoringCampgrounds).mockResolvedValue({
      items: [
        {
          id: "cg-other",
          provider_id: 1,
          recreation_area_id: "area-1",
          name: "Lower Pines",
        },
      ],
      total: 1,
      limit: 50,
      offset: 0,
      has_more: false,
      catalog_revision: 1,
      eligible_total: 2,
    });
    vi.mocked(searchCampgrounds).mockResolvedValue([
      {
        id: "new-cg",
        entity_type: "Campground",
        provider_id: 1,
        provider_name: "Recreation.gov",
        recreation_area_id: "area-1",
        recreation_area_name: "Yosemite",
        campground_id: "new-cg",
        campground_name: "Camp 4",
      },
    ]);
    const areaScan: ScanResponse = {
      ...savedScan,
      destination_type: "recreation_area",
      destination_name: "Yosemite",
      campground_id: null,
      campground_name: null,
      recreation_area_id: "area-1",
      coverage_mode: "selected",
      campground_ids: ["cg-1"],
      selected_campgrounds: [{ id: "cg-1", name: "Upper Pines" }],
      row_version: 2,
    };
    renderForm(areaScan);
    await user.click(screen.getByRole("button", { name: "Edit Scan" }));
    expect(
      screen.getByRole("button", { name: "Remove Upper Pines" }),
    ).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Change" }));
    const searchInput = screen.getByPlaceholderText(
      "Search for a campground...",
    );
    await user.type(searchInput, "Camp 4");
    await user.click(await screen.findByRole("button", { name: /Camp 4/ }));
    await user.click(screen.getByRole("button", { name: "Save Changes" }));
    await waitFor(() =>
      expect(updateScan).toHaveBeenCalledWith(
        areaScan.id,
        expect.objectContaining({
          destination_type: "campground",
          campground_id: "new-cg",
          provider_id: 1,
          row_version: 2,
        }),
      ),
    );
  });

  it("supports optional min_rv_length (1..200, clear to null, validation) and require_accessible", async () => {
    const user = userEvent.setup();
    renderForm({
      ...savedScan,
      min_rv_length: 32,
      require_accessible: true,
    });
    await user.click(screen.getByRole("button", { name: "Edit Scan" }));
    const lengthInput = screen.getByLabelText(
      "Minimum RV / Trailer Length (ft)",
    );
    const adaSwitch = screen.getByRole("switch", {
      name: "ADA Accessible Required",
    });
    expect(lengthInput).toHaveValue(32);
    expect(adaSwitch).toBeChecked();

    // Out-of-bounds value fails client validation before calling updateScan
    await user.clear(lengthInput);
    await user.type(lengthInput, "201");
    await user.click(screen.getByRole("button", { name: "Save Changes" }));
    expect(await screen.findByText(/200 ft/i)).toBeInTheDocument();
    expect(updateScan).not.toHaveBeenCalled();

    // Clearing blank sends min_rv_length: null; toggling ADA switch sets false
    await user.clear(lengthInput);
    await user.click(adaSwitch);
    await user.click(screen.getByRole("button", { name: "Save Changes" }));
    await waitFor(() =>
      expect(updateScan).toHaveBeenCalledWith(
        savedScan.id,
        expect.objectContaining({
          min_rv_length: null,
          require_accessible: false,
        }),
      ),
    );
  });

  it("hides unsupported filters per provider, explains why, and clears stale values on switch", async () => {
    const user = userEvent.setup();
    vi.mocked(listProviders).mockResolvedValue([
      {
        id: 1,
        name: "Recreation.gov",
        description: null,
        url: "https://recreation.gov",
        enabled: true,
        filter_capabilities: {
          preferred_types: true,
          require_electric: true,
          require_accessible: true,
          min_rv_length: true,
        },
      },
      {
        id: 2,
        name: "Limited Parks",
        description: null,
        url: "https://limited.example.com",
        enabled: true,
        filter_capabilities: {
          preferred_types: true,
          require_electric: false,
          require_accessible: true,
          min_rv_length: false,
        },
      },
    ]);
    vi.mocked(searchCampgrounds).mockReset();
    vi.mocked(searchCampgrounds).mockImplementation(async (term: string) =>
      term.toLowerCase().includes("limited")
        ? [
            {
              id: "cg-lim",
              entity_type: "Campground",
              provider_id: 2,
              provider_name: "Limited Parks",
              recreation_area_id: "area-2",
              recreation_area_name: "Park Two",
              campground_id: "cg-2",
              campground_name: "Limited Camp",
              city: null,
              state: "OR",
              country: "US",
            },
          ]
        : [
            {
              id: "cg-rec",
              entity_type: "Campground",
              provider_id: 1,
              provider_name: "Recreation.gov",
              recreation_area_id: "area-1",
              recreation_area_name: "Park One",
              campground_id: "cg-1",
              campground_name: "Full Support Camp",
              city: null,
              state: "CA",
              country: "US",
            },
          ],
    );

    render(
      <QueryClientProvider
        client={
          new QueryClient({
            defaultOptions: {
              queries: { retry: false },
              mutations: { retry: false },
            },
          })
        }
      >
        <ScanForm />
      </QueryClientProvider>,
    );
    await user.click(screen.getByRole("button", { name: "New Scan" }));

    // Select provider 1 (supports all filters) and configure RV length + electric
    await user.type(
      screen.getByPlaceholderText("Search for a campground..."),
      "Full",
    );
    await user.click(await screen.findByText("Full Support Camp"));
    expect(screen.getByText(/Provider: Recreation\.gov/)).toBeInTheDocument();

    await user.click(
      screen.getByRole("switch", { name: "Electric Hookup Required" }),
    );
    await user.type(
      screen.getByLabelText("Minimum RV / Trailer Length (ft)"),
      "250",
    );

    // Switch to provider 2 (no electric, no min_rv_length) — even with an active Zod error
    await user.click(screen.getByRole("button", { name: "Change" }));
    await user.type(
      screen.getByPlaceholderText("Search for a campground..."),
      "Limited",
    );
    await user.click(await screen.findByText("Limited Camp"));

    await waitFor(() => {
      expect(
        screen.queryByLabelText("Minimum RV / Trailer Length (ft)"),
      ).not.toBeInTheDocument();
      expect(
        screen.queryByRole("switch", { name: "Electric Hookup Required" }),
      ).not.toBeInTheDocument();
    });
    expect(
      screen.getByRole("switch", { name: "ADA Accessible Required" }),
    ).toBeInTheDocument();

    const status = screen.getByRole("status");
    expect(status).toHaveTextContent(/Limited Parks/);
    expect(status).toHaveTextContent(
      /Electric Hookup, Minimum RV \/ Trailer Length/,
    );
    expect(status).toHaveTextContent(/Cleared unsupported selection/);

    await selectDate(user, "Check-in", "2027-07-01");
    await selectDate(user, "Check-out", "2027-07-04");
    await user.click(screen.getByRole("button", { name: "Create Scan" }));

    await waitFor(() =>
      expect(createScan).toHaveBeenCalledWith(
        expect.objectContaining({
          provider_id: 2,
          campground_id: "cg-2",
          require_electric: false,
          min_rv_length: null,
        }),
      ),
    );
  });

  it("clears legacy unsupported filters when editing a scan", async () => {
    const user = userEvent.setup();
    vi.mocked(listProviders).mockResolvedValue([
      {
        id: 1,
        name: "Recreation.gov",
        description: null,
        url: "https://recreation.gov",
        enabled: true,
        filter_capabilities: {
          preferred_types: true,
          require_electric: false,
          require_accessible: true,
          min_rv_length: false,
        },
      },
    ]);

    renderForm({
      ...savedScan,
      require_electric: true,
      min_rv_length: 26,
    });
    await user.click(screen.getByRole("button", { name: "Edit Scan" }));

    await waitFor(() => {
      expect(
        screen.queryByLabelText("Minimum RV / Trailer Length (ft)"),
      ).not.toBeInTheDocument();
      expect(
        screen.queryByRole("switch", { name: "Electric Hookup Required" }),
      ).not.toBeInTheDocument();
    });
    expect(screen.getByRole("status")).toHaveTextContent(
      /Cleared unsupported selection\(s\): Electric Hookup, Minimum RV \/ Trailer Length/,
    );

    await user.click(screen.getByRole("button", { name: "Save Changes" }));
    await waitFor(() =>
      expect(updateScan).toHaveBeenCalledWith(
        savedScan.id,
        expect.objectContaining({
          require_electric: false,
          min_rv_length: null,
        }),
      ),
    );
  });

  it("hides preferred_types and require_accessible when unsupported by provider", async () => {
    const user = userEvent.setup();
    vi.mocked(listProviders).mockResolvedValue([
      {
        id: 1,
        name: "Recreation.gov",
        description: null,
        url: "https://recreation.gov",
        enabled: true,
        filter_capabilities: {
          preferred_types: false,
          require_electric: true,
          require_accessible: false,
          min_rv_length: true,
        },
      },
    ]);

    renderForm({
      ...savedScan,
      preferred_types: ["RV"],
      require_accessible: true,
    });
    await user.click(screen.getByRole("button", { name: "Edit Scan" }));

    await waitFor(() => {
      expect(
        screen.queryByText("Preferred Campsite Types"),
      ).not.toBeInTheDocument();
      expect(
        screen.queryByRole("switch", { name: "ADA Accessible Required" }),
      ).not.toBeInTheDocument();
    });
    expect(screen.getByRole("status")).toHaveTextContent(
      /Cleared unsupported selection\(s\): Preferred Campsite Types, ADA Accessible/,
    );

    await user.click(screen.getByRole("button", { name: "Save Changes" }));
    await waitFor(() =>
      expect(updateScan).toHaveBeenCalledWith(
        savedScan.id,
        expect.objectContaining({
          preferred_types: [],
          require_accessible: false,
        }),
      ),
    );
  });
});
