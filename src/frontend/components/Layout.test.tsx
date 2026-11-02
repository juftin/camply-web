import { render, screen, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import { Layout } from "./Layout";

vi.mock("@/components/Header", () => ({ Header: () => <header /> }));
vi.mock("@/components/CamplyLogo", () => ({
  CamplyLogo: () => <span>camply</span>,
}));

describe("Layout", () => {
  it("links the footer to the bundled docs with full browser navigation", () => {
    render(
      <MemoryRouter>
        <Layout>Content</Layout>
      </MemoryRouter>,
    );
    const link = within(screen.getByRole("contentinfo")).getByRole("link", {
      name: "Docs",
    });
    expect(link).toHaveAttribute("href", `${import.meta.env.BASE_URL}docs/`);
    expect(link).not.toHaveAttribute("data-discover");
  });
});
