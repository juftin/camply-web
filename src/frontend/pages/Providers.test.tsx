import { render, screen, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import { Providers } from "./Providers";

vi.mock("@/components/SearchBar.tsx", () => ({ SearchBar: () => null }));

describe("Providers", () => {
  it("lists all supported providers with canonical website links and excludes retired systems", () => {
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

    for (const retired of [
      "Yellowstone Lodges",
      "Alabama State Parks",
      "Maricopa County Parks",
    ]) {
      expect(screen.queryByText(retired)).not.toBeInTheDocument();
    }

    const sampleGoingToCamp: Array<[string, string]> = [
      ["Washington State Parks", "https://washington.goingtocamp.com"],
      ["Wisconsin State Parks", "https://wisconsin.goingtocamp.com"],
      ["Michigan State Parks", "https://midnrreservations.com"],
      ["Parks Canada", "https://reservation.pc.gc.ca"],
      ["BC Parks", "https://camping.bcparks.ca"],
      ["Ontario Parks", "https://reservations.ontarioparks.ca"],
      ["Newfoundland & Labrador Provincial Parks", "https://www.nlcamping.ca"],
      ["St. Clair Region", "https://stclair.goingtocamp.com"],
    ];
    for (const [name, url] of sampleGoingToCamp) {
      const title = screen
        .getAllByText(name)
        .find((el) => within(el).queryByRole("link") !== null);
      expect(title).toBeDefined();
      expect(within(title!).getByRole("link")).toHaveAttribute("href", url);
    }

    expect(screen.getByText("26 Booking Platforms")).toBeInTheDocument();
  });
});
