import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import {
  normalizeFoundSites,
  type DateSelection,
  type MonthRef,
} from "@/lib/availability";
import { AvailabilityCalendar } from "./AvailabilityCalendar";

const sites = normalizeFoundSites(
  [
    {
      provider_id: 1,
      campground_id: "cg-1",
      campground_name: "Upper Pines",
      campsite_id: "1",
      campsite_name: "Site 1",
      available_dates: ["2027-07-02", "2027-07-03"], // Fri Jul 2, Sat Jul 3
      booking_url: "https://book.example/1",
    },
    {
      provider_id: 1,
      campground_id: "cg-1",
      campground_name: "Upper Pines",
      campsite_id: "2",
      campsite_name: "Site 2",
      available_dates: ["2027-07-02", "2027-07-03", "2027-07-04"],
      booking_url: "https://book.example/2",
    },
  ],
  2,
);

function renderCalendar(overrides?: {
  scanStartDate?: string;
  scanEndDate?: string;
  visibleMonth?: MonthRef;
  selection?: DateSelection;
  onVisibleMonthChange?: (next: MonthRef) => void;
  onSelectDate?: (iso: string) => void;
  onClearSelection?: () => void;
}) {
  const onVisibleMonthChange = overrides?.onVisibleMonthChange ?? vi.fn();
  const onSelectDate = overrides?.onSelectDate ?? vi.fn();
  const onClearSelection = overrides?.onClearSelection ?? vi.fn();

  render(
    <AvailabilityCalendar
      scanStartDate={overrides?.scanStartDate ?? "2027-07-01"}
      scanEndDate={overrides?.scanEndDate ?? "2027-08-10"}
      sites={sites}
      visibleMonth={overrides?.visibleMonth ?? { year: 2027, month: 6 }}
      onVisibleMonthChange={onVisibleMonthChange}
      selection={overrides?.selection ?? null}
      onSelectDate={onSelectDate}
      onClearSelection={onClearSelection}
    />,
  );

  return { onVisibleMonthChange, onSelectDate, onClearSelection };
}

describe("AvailabilityCalendar", () => {
  it("renders month heading, per-night counts, bounded month navigation, and accessible labels", async () => {
    const user = userEvent.setup();
    const { onVisibleMonthChange } = renderCalendar();

    expect(screen.getByText("July 2027")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Previous month" }),
    ).toBeDisabled();
    expect(screen.getByRole("button", { name: "Next month" })).toBeEnabled();

    const jul2 = screen.getByRole("button", {
      name: /Jul 2, 2027 — 2 sites available/i,
    });
    expect(jul2).toBeEnabled();
    expect(jul2).toHaveAttribute("aria-pressed", "false");

    const jul1 = screen.getByRole("button", {
      name: /Jul 1, 2027 — no openings/i,
    });
    expect(jul1).toBeEnabled();

    await user.click(screen.getByRole("button", { name: "Next month" }));
    expect(onVisibleMonthChange).toHaveBeenCalledWith({ year: 2027, month: 7 });
  });

  it("enables scan.end_date checkout boundary only when a start date is active", () => {
    const { rerender } = render(
      <AvailabilityCalendar
        scanStartDate="2027-07-01"
        scanEndDate="2027-07-05"
        sites={sites}
        visibleMonth={{ year: 2027, month: 6 }}
        onVisibleMonthChange={vi.fn()}
        selection={null}
        onSelectDate={vi.fn()}
        onClearSelection={vi.fn()}
      />,
    );

    const jul5Unselected = screen.getByRole("button", {
      name: /Jul 5, 2027/i,
    });
    expect(jul5Unselected).toBeDisabled();

    rerender(
      <AvailabilityCalendar
        scanStartDate="2027-07-01"
        scanEndDate="2027-07-05"
        sites={sites}
        visibleMonth={{ year: 2027, month: 6 }}
        onVisibleMonthChange={vi.fn()}
        selection={{ start: "2027-07-02", end: null }}
        onSelectDate={vi.fn()}
        onClearSelection={vi.fn()}
      />,
    );

    const jul5WithStart = screen.getByRole("button", {
      name: /Jul 5, 2027/i,
    });
    expect(jul5WithStart).toBeEnabled();
  });

  it("calls onSelectDate on click and shows active filter summary with Clear dates button", async () => {
    const user = userEvent.setup();
    const { onSelectDate, onClearSelection } = renderCalendar({
      selection: { start: "2027-07-02", end: "2027-07-04" },
    });

    expect(screen.getByText(/2 nights/i)).toBeInTheDocument();
    const jul2 = screen.getByRole("button", {
      name: /Jul 2, 2027 — 2 sites available/i,
    });
    expect(jul2).toHaveAttribute("aria-pressed", "true");

    await user.click(jul2);
    expect(onSelectDate).toHaveBeenCalledWith("2027-07-02");

    await user.click(screen.getByRole("button", { name: "Clear dates" }));
    expect(onClearSelection).toHaveBeenCalledTimes(1);
  });
});
