import { render, screen, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import { Providers } from "./Providers";

vi.mock("@/components/SearchBar.tsx", () => ({ SearchBar: () => null }));

describe("Providers", () => {
  it("links both ReserveAmerica cards to the public website", () => {
    render(
      <MemoryRouter>
        <Providers />
      </MemoryRouter>,
    );

    const cards = screen.getAllByText("ReserveAmerica");
    expect(cards).toHaveLength(2);
    for (const title of cards) {
      expect(within(title).getByRole("link")).toHaveAttribute(
        "href",
        "https://www.reserveamerica.com",
      );
    }
    expect(screen.queryByText("Yellowstone Lodges")).not.toBeInTheDocument();
  });
});
