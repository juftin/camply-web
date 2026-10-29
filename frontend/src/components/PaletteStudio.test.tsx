import { describe, it, expect, beforeEach, vi } from "vitest";
import { render, screen, fireEvent, act } from "@testing-library/react";
import { ThemeProvider } from "@/components/theme-provider";
import { PaletteStudio } from "@/components/PaletteStudio";
import { FloatingPaletteWidget } from "@/components/FloatingPaletteWidget";

describe("PaletteStudio", () => {
  beforeEach(() => {
    localStorage.clear();
    document.documentElement.style.removeProperty("--primary");
    document.documentElement.style.removeProperty("--ring");
    vi.restoreAllMocks();
  });

  it("renders the palette studio with header and presets", () => {
    render(
      <ThemeProvider>
        <PaletteStudio />
      </ThemeProvider>,
    );

    expect(screen.getByText("Theme Palette Studio")).toBeInTheDocument();
    expect(screen.getByText("Steel / Slate Blue")).toBeInTheDocument();
    expect(screen.getByText("Alpine Lake Blue")).toBeInTheDocument();
    expect(screen.getByText("Nordic Dusk")).toBeInTheDocument();
    expect(screen.getByText("Legacy Neon Blue")).toBeInTheDocument();
  });

  it("allows selecting a curated preset and updates active color", () => {
    render(
      <ThemeProvider>
        <PaletteStudio />
      </ThemeProvider>,
    );

    const alpineButton = screen.getByRole("button", {
      name: /alpine lake blue/i,
    });
    fireEvent.click(alpineButton);

    // CSS property should be applied to documentElement
    const primary =
      document.documentElement.style.getPropertyValue("--primary");
    expect(primary).toContain("204");
  });

  it("updates hue when the slider changes", () => {
    render(
      <ThemeProvider>
        <PaletteStudio />
      </ThemeProvider>,
    );

    const hueSlider = screen.getByLabelText(/hue \(angle\)/i);
    fireEvent.change(hueSlider, { target: { value: "180" } });

    const primary =
      document.documentElement.style.getPropertyValue("--primary");
    expect(primary).toContain("180");
  });

  it("shows optical glare warning when saturation is high in dark mode", () => {
    // Switch to dark theme first
    localStorage.setItem("vite-ui-theme", "dark");

    render(
      <ThemeProvider>
        <PaletteStudio />
      </ThemeProvider>,
    );

    // Pick legacy neon
    const neonButton = screen.getByRole("button", {
      name: /legacy neon blue/i,
    });
    fireEvent.click(neonButton);

    expect(screen.getByText(/optical glare warning/i)).toBeInTheDocument();
  });

  it("resets to default palette", () => {
    render(
      <ThemeProvider>
        <PaletteStudio />
      </ThemeProvider>,
    );

    const alpineButton = screen.getByRole("button", {
      name: /alpine lake blue/i,
    });
    fireEvent.click(alpineButton);

    const resetButton = screen.getByRole("button", { name: /reset/i });
    fireEvent.click(resetButton);

    const primary =
      document.documentElement.style.getPropertyValue("--primary");
    expect(primary).toBe("");
  });

  it("copies CSS to clipboard", async () => {
    const writeTextMock = vi.fn().mockResolvedValue(undefined);
    Object.assign(navigator, {
      clipboard: {
        writeText: writeTextMock,
      },
    });

    render(
      <ThemeProvider>
        <PaletteStudio />
      </ThemeProvider>,
    );

    const copyButton = screen.getByRole("button", { name: /copy css/i });
    await act(async () => {
      fireEvent.click(copyButton);
    });

    expect(writeTextMock).toHaveBeenCalled();
  });
});

describe("FloatingPaletteWidget", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it("does not render when floating is disabled", () => {
    render(
      <ThemeProvider>
        <FloatingPaletteWidget />
      </ThemeProvider>,
    );

    expect(
      screen.queryByLabelText(/open theme palette studio/i),
    ).not.toBeInTheDocument();
  });

  it("renders and toggles open when floating is enabled in localStorage", () => {
    localStorage.setItem("camply-palette-floating-enabled", "true");

    render(
      <ThemeProvider>
        <FloatingPaletteWidget />
      </ThemeProvider>,
    );

    const openButton = screen.getByLabelText(/open theme palette studio/i);
    expect(openButton).toBeInTheDocument();

    fireEvent.click(openButton);
    expect(screen.getByText("Theme Palette Studio")).toBeInTheDocument();
  });
});
