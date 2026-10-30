import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi, beforeEach } from "vitest";

import { ScanForm } from "./ScanForm";
import type { Campground } from "@/lib/structs";

const mockCreateScanMutate = vi.fn();

vi.mock("@/hooks/useScans", () => ({
  useUpdateScan: () => ({ mutateAsync: vi.fn(), isPending: false }),
  useCreateScan: () => ({
    mutateAsync: mockCreateScanMutate,
    isPending: false,
  }),
}));

vi.mock("@/hooks/useAuth", () => ({
  useAuth: () => ({
    user: {
      id: "test-user-1",
      email: "camper@example.com",
      scanning_enabled: true,
    },
    isInvited: true,
  }),
}));

const mockCampground: Campground = {
  id: "232447",
  provider_id: 1,
  recreation_area_id: "1001",
  name: "Upper Pines",
  description: "Yosemite Valley campground",
  country: "USA",
  state: "CA",
  longitude: -119.56,
  latitude: 37.74,
  reservable: true,
  enabled: true,
  url: "https://recreation.gov",
};

describe("ScanForm date picker interactions", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("opens the modal and shows check-in and check-out date pickers", async () => {
    const user = userEvent.setup();
    render(
      <ScanForm
        preselectedCampground={mockCampground}
        preselectedProviderId={1}
      />,
    );

    // Open modal
    await user.click(screen.getByRole("button", { name: /new scan/i }));
    expect(screen.getByText("Create a New Scan")).toBeInTheDocument();

    expect(screen.getByLabelText("Check-in")).toBeInTheDocument();
    expect(screen.getByLabelText("Check-out")).toBeInTheDocument();
  });

  it("automatically uses start date as input for end date when start date is 3 months in the future", async () => {
    const user = userEvent.setup();
    render(
      <ScanForm
        preselectedCampground={mockCampground}
        preselectedProviderId={1}
      />,
    );

    await user.click(screen.getByRole("button", { name: /new scan/i }));

    // Click check-in date picker
    const checkInBtn = screen.getByLabelText("Check-in");
    await user.click(checkInBtn);

    // Select month = April (3 months out) and year = 2027
    const monthSelect = screen.getByRole("combobox", { name: /select month/i });
    const yearSelect = screen.getByRole("combobox", { name: /select year/i });

    fireEvent.change(yearSelect, { target: { value: "2027" } });
    fireEvent.change(monthSelect, { target: { value: "3" } }); // April

    // Pick day 15 (2027-04-15)
    const day15Btn = screen.getByRole("button", { name: "15" });
    await user.click(day15Btn);

    // Check-in should now display Apr 15, 2027
    expect(screen.getByLabelText("Check-in")).toHaveTextContent(
      /apr 15, 2027/i,
    );

    // Check-out should automatically use start date as input and default to Apr 16, 2027
    expect(screen.getByLabelText("Check-out")).toHaveTextContent(
      /apr 16, 2027/i,
    );

    // The stay preview should show "1 night"
    expect(screen.getByText(/1 night/i)).toBeInTheDocument();

    // Now open the Check-out date picker: it should open directly on April 2027!
    const checkOutBtn = screen.getByLabelText("Check-out");
    await user.click(checkOutBtn);

    const checkOutMonthSelect = screen.getByRole("combobox", {
      name: /select month/i,
    }) as HTMLSelectElement;
    const checkOutYearSelect = screen.getByRole("combobox", {
      name: /select year/i,
    }) as HTMLSelectElement;

    expect(checkOutMonthSelect.value).toBe("3"); // April
    expect(checkOutYearSelect.value).toBe("2027");

    // April 15 (check-in) should be disabled for check-out
    expect(screen.getByRole("button", { name: "15" })).toBeDisabled();

    // Pick a duration preset: "3 nights" (Apr 18, 2027)
    const threeNightsPreset = screen.getByRole("button", { name: "3 nights" });
    await user.click(threeNightsPreset);

    // Check-out is now Apr 18, 2027 and stay summary shows 3 nights
    expect(screen.getByLabelText("Check-out")).toHaveTextContent(
      /apr 18, 2027/i,
    );
    expect(screen.getByText(/3 nights/i)).toBeInTheDocument();
  });

  it("automatically advances end date when start date is changed to after current end date", async () => {
    const user = userEvent.setup();
    render(
      <ScanForm
        preselectedCampground={mockCampground}
        preselectedProviderId={1}
      />,
    );

    await user.click(screen.getByRole("button", { name: /new scan/i }));

    // Select start date: 2027-04-15
    await user.click(screen.getByLabelText("Check-in"));
    fireEvent.change(screen.getByRole("combobox", { name: /select year/i }), {
      target: { value: "2027" },
    });
    fireEvent.change(screen.getByRole("combobox", { name: /select month/i }), {
      target: { value: "3" },
    });
    await user.click(screen.getByRole("button", { name: "15" }));

    // End date is Apr 16, 2027
    expect(screen.getByLabelText("Check-out")).toHaveTextContent(
      /apr 16, 2027/i,
    );

    // Now change start date to 2027-05-20 (past April 16)
    await user.click(screen.getByLabelText("Check-in"));
    fireEvent.change(screen.getByRole("combobox", { name: /select month/i }), {
      target: { value: "4" },
    }); // May
    await user.click(screen.getByRole("button", { name: "20" }));

    // End date should have automatically advanced to May 21, 2027
    expect(screen.getByLabelText("Check-in")).toHaveTextContent(
      /may 20, 2027/i,
    );
    expect(screen.getByLabelText("Check-out")).toHaveTextContent(
      /may 21, 2027/i,
    );
  });

  it("submits the form with chosen dates and campground", async () => {
    const user = userEvent.setup();
    mockCreateScanMutate.mockResolvedValue({ id: "new-scan-123" });

    render(
      <ScanForm
        preselectedCampground={mockCampground}
        preselectedProviderId={1}
      />,
    );

    await user.click(screen.getByRole("button", { name: /new scan/i }));

    // Select check-in date
    await user.click(screen.getByLabelText("Check-in"));
    fireEvent.change(screen.getByRole("combobox", { name: /select year/i }), {
      target: { value: "2027" },
    });
    fireEvent.change(screen.getByRole("combobox", { name: /select month/i }), {
      target: { value: "6" },
    }); // July
    await user.click(screen.getByRole("button", { name: "10" })); // 2027-07-10

    // Submit
    await user.click(screen.getByRole("button", { name: "Create Scan" }));

    await waitFor(() => {
      expect(mockCreateScanMutate).toHaveBeenCalledWith(
        expect.objectContaining({
          provider_id: 1,
          campground_id: "232447",
          start_date: "2027-07-10",
          end_date: "2027-07-11",
          min_stay_length: 1,
        }),
      );
    });
  });
});
