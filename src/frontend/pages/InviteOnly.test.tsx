import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { InviteOnly } from "./InviteOnly";
import type { AuthState } from "@/hooks/useAuth";
import * as api from "@/lib/api";

let mockAuthState: Partial<AuthState>;

vi.mock("@/hooks/useAuth", () => ({
  useAuth: () => mockAuthState,
}));

vi.mock("@/lib/api", async (original) => ({
  ...(await original<typeof import("@/lib/api")>()),
  submitAccessRequest: vi.fn(),
}));

describe("InviteOnly", () => {
  const refreshMock = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    refreshMock.mockResolvedValue(undefined);
  });

  function setup() {
    render(
      <MemoryRouter>
        <InviteOnly />
      </MemoryRouter>,
    );
    return userEvent.setup();
  }

  it("shows Pending Review status card and calls refresh() on Refresh Status", async () => {
    mockAuthState = {
      user: {
        id: "u-1",
        email: "camper@example.test",
        is_invited: false,
        is_admin: false,
        scanning_enabled: true,
        pushover_token: null,
        invitation_status: "pending",
      },
      refresh: refreshMock,
    };

    const user = setup();
    expect(
      screen.getByRole("heading", { name: "Pending Review" }),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/email notifications are not sent/i),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Request Access" }),
    ).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Refresh Status" }));
    expect(refreshMock).toHaveBeenCalledTimes(1);
  });

  it("shows Invitation Approved status card with dashboard link when invited", () => {
    mockAuthState = {
      user: {
        id: "u-1",
        email: "camper@example.test",
        is_invited: true,
        is_admin: false,
        scanning_enabled: true,
        pushover_token: null,
        invitation_status: "approved",
      },
      refresh: refreshMock,
    };

    setup();
    expect(
      screen.getByRole("heading", { name: "Invitation Approved" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: "Continue to Dashboard" }),
    ).toHaveAttribute("href", "/dashboard");
    expect(
      screen.queryByRole("button", { name: "Refresh Status" }),
    ).not.toBeInTheDocument();
  });

  it("shows Refresh Status alongside Continue to Dashboard when approved but not yet marked invited", async () => {
    mockAuthState = {
      user: {
        id: "u-1",
        email: "camper@example.test",
        is_invited: false,
        is_admin: false,
        scanning_enabled: true,
        pushover_token: null,
        invitation_status: "approved",
      },
      refresh: refreshMock,
    };

    const user = setup();
    expect(
      screen.getByRole("heading", { name: "Invitation Approved" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: "Continue to Dashboard" }),
    ).toHaveAttribute("href", "/dashboard");
    await user.click(screen.getByRole("button", { name: "Refresh Status" }));
    expect(refreshMock).toHaveBeenCalledTimes(1);
  });

  it("shows Request Declined status card without resubmit form when rejected", async () => {
    mockAuthState = {
      user: {
        id: "u-1",
        email: "camper@example.test",
        is_invited: false,
        is_admin: false,
        scanning_enabled: true,
        pushover_token: null,
        invitation_status: "rejected",
      },
      refresh: refreshMock,
    };

    const user = setup();
    expect(
      screen.getByRole("heading", { name: "Request Declined" }),
    ).toBeInTheDocument();
    expect(screen.queryByLabelText("Email")).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Request Access" }),
    ).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Refresh Status" }));
    expect(refreshMock).toHaveBeenCalledTimes(1);
  });

  it("pre-fills signed-in user email, submits request, calls refresh(), and shows Pending Review", async () => {
    mockAuthState = {
      user: {
        id: "u-1",
        email: "camper@example.test",
        is_invited: false,
        is_admin: false,
        scanning_enabled: true,
        pushover_token: null,
        invitation_status: null,
      },
      refresh: refreshMock,
    };
    vi.mocked(api.submitAccessRequest).mockResolvedValue({
      message: "Thanks!",
    });

    const user = setup();
    const emailInput = screen.getByLabelText("Email");
    expect(emailInput).toHaveValue("camper@example.test");

    await user.type(screen.getByLabelText("Name (optional)"), "Sam");
    await user.click(screen.getByRole("button", { name: "Request Access" }));

    await waitFor(() => {
      expect(api.submitAccessRequest).toHaveBeenCalledWith({
        email: "camper@example.test",
        name: "Sam",
      });
    });
    expect(refreshMock).toHaveBeenCalledTimes(1);
    expect(
      await screen.findByRole("heading", { name: "Pending Review" }),
    ).toBeInTheDocument();
  });

  it("allows signed-out visitors to submit an access request without calling refresh()", async () => {
    mockAuthState = {
      user: null,
      refresh: refreshMock,
    };
    vi.mocked(api.submitAccessRequest).mockResolvedValue({
      message: "Thanks!",
    });

    const user = setup();
    const emailInput = screen.getByLabelText("Email");
    expect(emailInput).toHaveValue("");

    await user.type(emailInput, "visitor@example.test");
    await user.click(screen.getByRole("button", { name: "Request Access" }));

    await waitFor(() => {
      expect(api.submitAccessRequest).toHaveBeenCalledWith({
        email: "visitor@example.test",
        name: null,
      });
    });
    expect(refreshMock).not.toHaveBeenCalled();
    expect(
      await screen.findByRole("heading", { name: "Pending Review" }),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Refresh Status" }),
    ).not.toBeInTheDocument();
  });

  it("displays an error when submitting the access request fails", async () => {
    mockAuthState = {
      user: null,
      refresh: refreshMock,
    };
    vi.mocked(api.submitAccessRequest).mockRejectedValue(
      new Error("Request service unavailable"),
    );

    const user = setup();
    await user.type(screen.getByLabelText("Email"), "visitor@example.test");
    await user.click(screen.getByRole("button", { name: "Request Access" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Request service unavailable",
    );
  });
});
