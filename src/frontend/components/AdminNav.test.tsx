import { act, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { expect, it, vi } from "vitest";
import { AdminNav } from "./AdminNav";

it("reveals the entire active tab after the web font loads", async () => {
  let resolveFont: () => void = () => {};
  const fontReady = new Promise<void>((resolve) => {
    resolveFont = resolve;
  });
  const fonts = Object.getOwnPropertyDescriptor(document, "fonts");
  Object.defineProperty(document, "fonts", {
    configurable: true,
    value: { ready: fontReady },
  });
  let activeTabRight = 410;
  const bounds = vi
    .spyOn(HTMLElement.prototype, "getBoundingClientRect")
    .mockImplementation(function (this: HTMLElement) {
      return this.getAttribute("aria-current") === "page"
        ? new DOMRect(300, 0, activeTabRight - 300, 44)
        : new DOMRect(0, 0, 390, 44);
    });

  try {
    render(
      <MemoryRouter initialEntries={["/admin/audit"]}>
        <AdminNav />
      </MemoryRouter>,
    );
    const scroller = screen.getByRole("link", {
      current: "page",
    }).parentElement;

    activeTabRight = 412;
    await act(async () => resolveFont());

    expect(scroller?.scrollLeft).toBe(22);
  } finally {
    bounds.mockRestore();
    if (fonts) Object.defineProperty(document, "fonts", fonts);
    else Reflect.deleteProperty(document, "fonts");
  }
});
