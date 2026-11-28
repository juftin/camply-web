import userEvent from "@testing-library/user-event";
import { render, screen, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import { Layout } from "./Layout";

vi.mock("@/hooks/useAuth", () => ({
  useAuth: () => ({ user: null, signupEnabled: true, autoLogin: false }),
}));
vi.mock("@/components/theme-toggle", () => ({ ThemeToggle: () => null }));
vi.stubGlobal("scrollTo", vi.fn());
const matchMedia = vi.fn((query: string) => ({
  matches: false,
  media: query,
  addEventListener: vi.fn(),
  removeEventListener: vi.fn(),
}));
vi.stubGlobal("matchMedia", matchMedia);
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

  it("links to FAQ from the desktop navigation", () => {
    render(
      <MemoryRouter>
        <Layout>Content</Layout>
      </MemoryRouter>,
    );
    const nav = within(screen.getByRole("navigation"));
    expect(nav.getByRole("link", { name: "FAQ" })).toHaveAttribute(
      "href",
      "/faq",
    );
    const footer = within(screen.getByRole("contentinfo"));
    expect(footer.queryByRole("link", { name: "FAQ" })).not.toBeInTheDocument();
  });
});

it("opens the mobile navigation and closes it after following a link", async () => {
  const user = userEvent.setup();
  render(
    <MemoryRouter>
      <Layout>Content</Layout>
    </MemoryRouter>,
  );

  const trigger = screen.getByRole("button", { name: "Toggle mobile menu" });
  await user.click(trigger);
  const drawer = screen.getByRole("dialog", { name: "Navigation" });
  const faq = within(drawer).getByRole("link", { name: "FAQ" });
  expect(faq).toHaveAttribute("href", "/faq");
  await user.click(faq);
  expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  expect(trigger).toHaveAttribute("aria-expanded", "false");
});

it("navigates without smooth scrolling when reduced motion is preferred", async () => {
  const user = userEvent.setup();
  matchMedia.mockImplementation((query) => ({
    matches: query === "(prefers-reduced-motion: reduce)",
    media: query,
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
  }));
  try {
    render(
      <MemoryRouter>
        <Layout>Content</Layout>
      </MemoryRouter>,
    );
    await user.click(screen.getByRole("link", { name: "FAQ" }));
    expect(window.scrollTo).toHaveBeenLastCalledWith({
      top: 0,
      behavior: "instant",
    });
  } finally {
    matchMedia.mockImplementation((query) => ({
      matches: false,
      media: query,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
    }));
  }
});
