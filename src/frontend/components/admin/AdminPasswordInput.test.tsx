import { useState } from "react";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { AdminPasswordInput } from "./AdminPasswordInput";

function PasswordForm({ disabled = false }: { disabled?: boolean }) {
  const [password, setPassword] = useState("");
  return (
    <form onSubmit={(event) => event.preventDefault()}>
      <AdminPasswordInput
        id="password"
        label="Initial Password"
        value={password}
        onChange={setPassword}
        disabled={disabled}
      />
    </form>
  );
}

describe("AdminPasswordInput", () => {
  afterEach(() => vi.restoreAllMocks());

  it("generates a password using Web Crypto, reveals it, and copies exactly that value", async () => {
    const user = userEvent.setup();
    const random = vi.spyOn(crypto, "getRandomValues");
    const copy = vi.spyOn(navigator.clipboard, "writeText").mockResolvedValue();
    render(<PasswordForm />);
    expect(screen.getByLabelText("Initial Password")).toHaveAttribute(
      "type",
      "password",
    );
    expect(
      screen.queryByRole("button", { name: "Copy password" }),
    ).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Generate Password" }));
    const input = screen.getByLabelText("Initial Password") as HTMLInputElement;
    expect(random).toHaveBeenCalled();
    expect(input.value).toMatch(/^[A-Za-z0-9_-]{24}$/);
    expect(input).toHaveAttribute("type", "text");
    expect(screen.getByText(/will not be shown again/)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Copy password" }));
    expect(copy).toHaveBeenCalledWith(input.value);
    expect(
      await screen.findByRole("button", { name: "Copied" }),
    ).toBeInTheDocument();
  });

  it("replaces a generated password and resets copy feedback", async () => {
    const user = userEvent.setup();
    vi.spyOn(navigator.clipboard, "writeText").mockResolvedValue();
    render(<PasswordForm />);
    await user.click(screen.getByRole("button", { name: "Generate Password" }));
    const input = screen.getByLabelText("Initial Password") as HTMLInputElement;
    const previous = input.value;
    await user.click(screen.getByRole("button", { name: "Copy password" }));
    await user.click(screen.getByRole("button", { name: "Generate Password" }));
    expect(input.value).not.toBe(previous);
    expect(
      screen.getByRole("button", { name: "Copy password" }),
    ).toBeInTheDocument();
  });

  it("masks manually entered passwords and clears generated-password feedback", async () => {
    const user = userEvent.setup();
    render(<PasswordForm />);
    await user.click(screen.getByRole("button", { name: "Generate Password" }));
    const input = screen.getByLabelText("Initial Password");
    await user.clear(input);
    await user.type(input, "manually-entered-password");
    expect(input).toHaveValue("manually-entered-password");
    expect(input).toHaveAttribute("type", "password");
    expect(
      screen.queryByRole("button", { name: "Copy password" }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByText(/will not be shown again/),
    ).not.toBeInTheDocument();
  });

  it("keeps the password visible for manual copying when clipboard access fails", async () => {
    const user = userEvent.setup();
    vi.spyOn(navigator.clipboard, "writeText").mockRejectedValue(
      new Error("Clipboard denied"),
    );
    render(<PasswordForm />);
    await user.click(screen.getByRole("button", { name: "Generate Password" }));
    const input = screen.getByLabelText("Initial Password") as HTMLInputElement;
    const password = input.value;
    await user.click(screen.getByRole("button", { name: "Copy password" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(
      /copy it manually/i,
    );
    expect(input).toHaveValue(password);
    expect(input).toHaveAttribute("type", "text");
  });

  it("does not generate a password if cryptographic randomness is unavailable", async () => {
    const user = userEvent.setup();
    vi.spyOn(crypto, "getRandomValues").mockImplementation(() => {
      throw new Error("Unavailable");
    });
    render(<PasswordForm />);
    await user.click(screen.getByRole("button", { name: "Generate Password" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(
      /generate a secure password/i,
    );
    expect(screen.getByLabelText("Initial Password")).toHaveValue("");
  });

  it("disables generation and copy while a request is pending", async () => {
    const user = userEvent.setup();
    const { rerender } = render(<PasswordForm />);
    await user.click(screen.getByRole("button", { name: "Generate Password" }));
    rerender(<PasswordForm disabled />);
    await waitFor(() => {
      expect(screen.getByLabelText("Initial Password")).toBeDisabled();
      expect(
        screen.getByRole("button", { name: "Generate Password" }),
      ).toBeDisabled();
      expect(
        screen.getByRole("button", { name: "Copy password" }),
      ).toBeDisabled();
    });
  });
});
