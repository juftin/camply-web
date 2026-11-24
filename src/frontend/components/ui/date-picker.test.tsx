import { render, screen, fireEvent } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { DatePicker } from "./date-picker";

describe("DatePicker", () => {
  it("renders with placeholder when no value is provided", () => {
    render(<DatePicker id="test-date" placeholder="Choose check-in" />);
    expect(
      screen.getByRole("button", { name: /choose check-in/i }),
    ).toBeInTheDocument();
  });

  it("renders human-formatted date when value is provided", () => {
    render(<DatePicker id="test-date" value="2027-01-15" />);
    // 2027-01-15 was Friday
    expect(
      screen.getByRole("button", { name: /jan 15, 2027/i }),
    ).toBeInTheDocument();
  });

  it("opens popover on click and closes on Escape", async () => {
    const user = userEvent.setup();
    render(<DatePicker id="test-date" value="2027-01-15" />);

    const trigger = screen.getByRole("button", { name: /jan 15, 2027/i });
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();

    await user.click(trigger);
    expect(screen.getByRole("dialog")).toBeInTheDocument();

    await user.keyboard("{Escape}");
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("opens directly to defaultMonth when value is empty", async () => {
    const user = userEvent.setup();
    // Start date is 3 months out: April 2027
    render(
      <DatePicker
        id="end-date"
        defaultMonth="2027-04-10"
        placeholder="Select check-out"
      />,
    );

    await user.click(screen.getByRole("button", { name: /select check-out/i }));
    expect(screen.getByRole("dialog")).toBeInTheDocument();

    // Check that the month selector displays April and year selector displays 2027
    const monthSelect = screen.getByRole("combobox", {
      name: /select month/i,
    }) as HTMLSelectElement;
    const yearSelect = screen.getByRole("combobox", {
      name: /select year/i,
    }) as HTMLSelectElement;

    expect(monthSelect.value).toBe("3"); // 0-indexed: 3 = April
    expect(yearSelect.value).toBe("2027");
  });

  it("navigates months with next and previous buttons", async () => {
    const user = userEvent.setup();
    render(<DatePicker id="test-date" value="2027-01-15" />);

    await user.click(screen.getByRole("button", { name: /jan 15, 2027/i }));

    const monthSelect = screen.getByRole("combobox", {
      name: /select month/i,
    }) as HTMLSelectElement;
    expect(monthSelect.value).toBe("0"); // January

    const nextBtn = screen.getByRole("button", { name: /next month/i });
    await user.click(nextBtn);
    expect(monthSelect.value).toBe("1"); // February

    const prevBtn = screen.getByRole("button", { name: /previous month/i });
    await user.click(prevBtn);
    expect(monthSelect.value).toBe("0"); // January
  });

  it("disables dates prior to effectiveMinDate", async () => {
    const user = userEvent.setup();
    render(
      <DatePicker
        id="end-date"
        value="2027-01-15"
        startDate="2027-01-15"
        minDate="2027-01-16"
      />,
    );

    await user.click(screen.getByRole("button", { name: /jan 15, 2027/i }));

    // In January 2027: days 1..15 should be disabled because minDate is 2027-01-16
    const day10Btn = screen.getByRole("button", { name: "10" });
    expect(day10Btn).toBeDisabled();

    // Day 16 should be enabled
    const day16Btn = screen.getByRole("button", { name: "16" });
    expect(day16Btn).not.toBeDisabled();
  });

  it("selects a date when clicked and calls onChange", async () => {
    const user = userEvent.setup();
    const handleChange = vi.fn();
    render(
      <DatePicker id="test-date" value="2027-01-15" onChange={handleChange} />,
    );

    await user.click(screen.getByRole("button", { name: /jan 15, 2027/i }));

    const day20Btn = screen.getByRole("button", { name: "20" });
    await user.click(day20Btn);

    expect(handleChange).toHaveBeenCalledWith("2027-01-20");
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("renders duration presets and selects date when startDate is provided", async () => {
    const user = userEvent.setup();
    const handleChange = vi.fn();
    render(
      <DatePicker
        id="end-date"
        startDate="2027-01-15"
        placeholder="Select check-out"
        onChange={handleChange}
      />,
    );

    await user.click(screen.getByRole("button", { name: /select check-out/i }));

    // Check duration presets are rendered
    expect(screen.getByRole("button", { name: "1 night" })).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "2 nights" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "3 nights" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "7 nights" }),
    ).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "3 nights" }));
    expect(handleChange).toHaveBeenCalledWith("2027-01-18");
  });

  it("clears the date when the clear button is clicked", () => {
    const handleChange = vi.fn();
    render(
      <DatePicker id="test-date" value="2027-01-15" onChange={handleChange} />,
    );

    const clearBtn = screen.getByRole("button", { name: /clear date/i });
    fireEvent.click(clearBtn);

    expect(handleChange).toHaveBeenCalledWith("");
  });
});
