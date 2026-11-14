import {
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { DestinationDetails } from "./DestinationDetails";
import { destinationDetails as snapshot } from "@/test/destination-details";

// Layout and dragging are exercised with the real Embla engine in browser snapshots.
vi.mock("embla-carousel-react", () => ({
  default: () => [() => {}, undefined],
}));

describe("Destination enrichment", () => {
  it("omits enrichment when no snapshot exists", () => {
    const { container } = render(
      <DestinationDetails name="Synthetic park" details={null} />,
    );
    expect(container).toBeEmptyDOMElement();
  });

  it("preserves the overview when enrichment is absent", () => {
    render(
      <DestinationDetails name="Synthetic park" details={null}>
        <p>Destination overview and map</p>
      </DestinationDetails>,
    );
    expect(screen.getByText("Destination overview and map")).toBeVisible();
    expect(screen.queryByRole("heading", { name: "Photos" })).toBeNull();
  });

  it("shows populated practical information and truthful UTC provenance", () => {
    render(<DestinationDetails name="Synthetic park" details={snapshot()} />);
    expect(
      screen.getByRole("heading", { name: "Know before you go" }),
    ).toBeVisible();
    expect(screen.getByRole("heading", { name: "Directions" })).toBeVisible();
    expect(screen.getByText("Follow the signed road.")).toBeVisible();
    expect(screen.getByText("Boat launch (nearby)")).toBeVisible();
    expect(screen.getByText("8 a.m. until sunset")).toBeVisible();
    expect(screen.getByText("35 feet")).toBeVisible();
    expect(screen.getByRole("link", { name: "Park map" })).toHaveAttribute(
      "rel",
      "noopener noreferrer",
    );
    expect(screen.getByText("Updated Nov 15, 2026 (UTC)")).toBeVisible();
    expect(screen.queryByRole("heading", { name: "Accessibility" })).toBeNull();
  });

  it("opens photos, wraps by keyboard, and restores focus to the selected photo", async () => {
    const user = userEvent.setup();
    render(<DestinationDetails name="Synthetic park" details={snapshot()} />);
    const trigger = screen.getByRole("button", {
      name: "View Synthetic park photo 1",
    });
    const carousel = screen.getByRole("region", {
      name: "Synthetic park photos",
    });
    expect(within(carousel).getByText("A synthetic lake view")).toBeVisible();
    expect(within(carousel).queryByText(/^Photo \d+ of \d+$/)).toBeNull();
    expect(within(carousel).queryByText(/Credit:/)).toBeNull();
    expect(
      within(carousel).queryByRole("link", { name: "Photo source" }),
    ).toBeNull();
    await user.click(trigger);
    const dialog = screen.getByRole("dialog", {
      name: "Synthetic park photos",
    });
    expect(within(dialog).getByText("Photo 1 of 2")).toBeVisible();
    expect(within(dialog).getByText("A synthetic lake view")).toBeVisible();
    expect(within(dialog).queryByText(/Credit:/)).toBeNull();
    expect(
      within(dialog).queryByRole("link", { name: "Photo source" }),
    ).toBeNull();
    within(dialog).getByRole("button", { name: "Close" }).focus();
    await user.tab();
    expect(
      within(dialog).getByRole("button", { name: "Previous photo" }),
    ).toHaveFocus();
    await user.keyboard("{ArrowLeft}");
    expect(within(dialog).getByText("Photo 2 of 2")).toBeVisible();
    await user.keyboard("{ArrowRight}");
    expect(within(dialog).getByText("Photo 1 of 2")).toBeVisible();
    await user.click(
      within(dialog).getByRole("button", { name: "Next photo" }),
    );
    expect(within(dialog).getByText("Photo 2 of 2")).toBeVisible();
    await user.keyboard("{Escape}");
    expect(screen.queryByRole("dialog")).toBeNull();
    expect(
      screen.getByRole("button", { name: "View Synthetic park photo 2" }),
    ).toHaveFocus();
  });

  it("hides navigation for a single photo and never invents captions or credits", async () => {
    const user = userEvent.setup();
    const data = snapshot();
    data.photos = [data.photos[1]];
    render(<DestinationDetails name="Synthetic campground" details={data} />);
    expect(screen.queryByRole("button", { name: "Next photo" })).toBeNull();
    await user.click(
      screen.getByRole("button", { name: "View Synthetic campground photo 1" }),
    );
    const dialog = screen.getByRole("dialog");
    expect(within(dialog).getByRole("img")).toHaveAttribute(
      "alt",
      "Synthetic campground photo 1",
    );
    expect(
      within(dialog).queryByRole("button", { name: "Next photo" }),
    ).toBeNull();
    expect(within(dialog).queryByText(/Credit:/)).toBeNull();
  });

  it("cycles a single visible carousel photo and opens the selected photo", async () => {
    const user = userEvent.setup();
    render(<DestinationDetails name="Synthetic park" details={snapshot()} />);
    const carousel = screen.getByRole("region", {
      name: "Synthetic park photos",
    });
    expect(within(carousel).getAllByRole("img")).toHaveLength(1);
    await user.click(
      within(carousel).getByRole("button", { name: "Next photo" }),
    );
    const trigger = screen.getByRole("button", {
      name: "View Synthetic park photo 2",
    });
    await user.click(trigger);
    expect(
      within(screen.getByRole("dialog")).getByText("Photo 2 of 2"),
    ).toBeVisible();
    await user.keyboard("{Escape}");
    expect(trigger).toHaveFocus();
    await user.keyboard("{ArrowRight}");
    expect(
      within(carousel).getByRole("group", {
        name: "Photo 1 of 2",
      }),
    ).toBeVisible();
    await user.keyboard("{ArrowLeft}");
    expect(
      within(carousel).getByRole("group", {
        name: "Photo 2 of 2",
      }),
    ).toBeVisible();
  });

  it("removes failed images and keeps useful details after all images fail", async () => {
    const user = userEvent.setup();
    render(<DestinationDetails name="Synthetic park" details={snapshot()} />);
    await user.click(
      screen.getByRole("button", { name: "View Synthetic park photo 1" }),
    );
    fireEvent.error(within(screen.getByRole("dialog")).getByRole("img"));
    expect(
      within(screen.getByRole("dialog")).getByText("Photo 1 of 1"),
    ).toBeVisible();
    fireEvent.error(within(screen.getByRole("dialog")).getByRole("img"));
    expect(screen.queryByRole("dialog")).toBeNull();
    expect(screen.queryByRole("heading", { name: "Photos" })).toBeNull();
    expect(screen.queryByRole("button", { name: /View Synthetic/ })).toBeNull();
    expect(screen.getByText("Follow the signed road.")).toBeVisible();
    expect(screen.getByRole("link", { name: "Source" })).toBeVisible();
    await waitFor(() =>
      expect(
        screen.getByRole("link", { name: "Source" }).closest("p"),
      ).toHaveFocus(),
    );
  });

  it("skips failed carousel photos without opening the full-screen viewer", () => {
    render(<DestinationDetails name="Synthetic park" details={snapshot()} />);
    const carousel = screen.getByRole("region", {
      name: "Synthetic park photos",
    });
    fireEvent.error(within(carousel).getByRole("img"));
    expect(
      within(carousel).getByRole("group", {
        name: "Photo 1 of 1",
      }),
    ).toBeVisible();
    expect(
      within(carousel).queryByRole("button", { name: "Next photo" }),
    ).toBeNull();
    fireEvent.error(within(carousel).getByRole("img"));
    expect(
      screen.queryByRole("region", { name: "Synthetic park photos" }),
    ).toBeNull();
    expect(
      screen.getByRole("heading", { name: "Know before you go" }),
    ).toBeVisible();
  });

  it("resets gallery state when navigating to another destination", async () => {
    const user = userEvent.setup();
    const data = snapshot();
    const { rerender } = render(
      <DestinationDetails name="First park" details={data} />,
    );
    fireEvent.error(screen.getAllByRole("img")[0]);
    await user.click(
      screen.getByRole("button", { name: "View First park photo 1" }),
    );
    rerender(
      <DestinationDetails
        name="Second park"
        details={{
          ...data,
          source_url: "https://provider.example.test/second",
        }}
      />,
    );
    expect(screen.queryByRole("dialog")).toBeNull();
    expect(screen.getAllByRole("img")).toHaveLength(1);
    expect(
      screen.getByRole("button", { name: "View Second park photo 1" }),
    ).toBeVisible();
  });

  it("rejects unsafe image/link protocols and sanitizes narrative markup", () => {
    const data = snapshot();
    data.photos = [{ ...data.photos[0], url: "data:image/svg+xml,unsafe" }];
    data.links = [{ label: "Unsafe link", url: "javascript:alert(1)" }];
    data.source_url = "https://user:password@provider.example.test/park";
    data.directions =
      '<p>Safe route<script>alert(1)</script><img src=x onerror="alert(1)"><a href="javascript:alert(1)">Unsafe narrative link</a><a target="_blank" href="https://provider.example.test/directions">Route map</a></p>';
    const { container } = render(
      <DestinationDetails name="Synthetic park" details={data} />,
    );
    expect(screen.queryByRole("img")).toBeNull();
    expect(screen.queryByRole("link", { name: "Unsafe link" })).toBeNull();
    expect(
      screen.queryByRole("link", { name: "Unsafe narrative link" }),
    ).toBeNull();
    expect(screen.queryByRole("link", { name: "Source" })).toBeNull();
    expect(container.querySelector("script")).toBeNull();
    expect(screen.getByRole("link", { name: "Route map" })).toHaveAttribute(
      "rel",
      "noopener noreferrer",
    );
  });
});
