import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, it } from "vitest";
import { Sheet, SheetContent, SheetTitle, SheetTrigger } from "./sheet";

it("traps focus and restores it to the trigger when dismissed", async () => {
  const user = userEvent.setup();
  render(
    <Sheet>
      <SheetTrigger>Open menu</SheetTrigger>
      <SheetContent aria-describedby={undefined}>
        <SheetTitle>Navigation</SheetTitle>
        <a href="/search">Explore</a>
      </SheetContent>
    </Sheet>,
  );

  const trigger = screen.getByRole("button", { name: "Open menu" });
  await user.click(trigger);
  expect(trigger).toHaveAttribute("aria-expanded", "true");
  expect(screen.getByRole("dialog", { name: "Navigation" })).toContainElement(
    document.activeElement as HTMLElement,
  );
  await user.tab();
  expect(screen.getByRole("link", { name: "Explore" })).toHaveFocus();
  await user.tab();
  expect(screen.getByRole("button", { name: "Close" })).toHaveFocus();
  await user.keyboard("{Escape}");
  expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  expect(trigger).toHaveFocus();
});
