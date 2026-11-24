import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi, beforeEach } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ChangePasswordRequired } from "./ChangePasswordRequired";
import * as api from "@/lib/api";

const mockSignOut = vi.fn();

vi.mock("@/hooks/useAuth", () => ({
  useAuth: () => ({
    user: {
      id: "user-1",
      email: "tempuser@example.com",
      is_invited: true,
      is_admin: false,
      scanning_enabled: true,
      pushover_token: null,
      must_change_password: true,
    },
    signOut: mockSignOut,
  }),
}));

vi.mock("@/lib/api", async (original) => ({
  ...(await original<typeof import("@/lib/api")>()),
  changePassword: vi.fn(),
}));

describe("ChangePasswordRequired", () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    vi.clearAllMocks();
    queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
  });

  function renderComponent() {
    return render(
      <QueryClientProvider client={queryClient}>
        <ChangePasswordRequired />
      </QueryClientProvider>,
    );
  }

  it("renders the required fields and user email", () => {
    renderComponent();
    expect(screen.getByText("Password Change Required")).toBeInTheDocument();
    expect(screen.getByText(/tempuser@example.com/)).toBeInTheDocument();
    expect(
      screen.getByLabelText(/Current \/ Temporary Password/i),
    ).toBeInTheDocument();
    expect(screen.getByLabelText(/^New Password/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Confirm New Password/i)).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Update Password" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Sign Out" }),
    ).toBeInTheDocument();
  });

  it("validates that new passwords match", async () => {
    const user = userEvent.setup();
    renderComponent();

    await user.type(
      screen.getByLabelText(/Current \/ Temporary Password/i),
      "temporary-pass",
    );
    await user.type(
      screen.getByLabelText(/^New Password/i),
      "new-secure-pass-1",
    );
    await user.type(
      screen.getByLabelText(/Confirm New Password/i),
      "different-pass-2",
    );
    await user.click(screen.getByRole("button", { name: "Update Password" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "New passwords do not match.",
    );
    expect(api.changePassword).not.toHaveBeenCalled();
  });

  it("validates minimum password length of 8 characters", async () => {
    const user = userEvent.setup();
    renderComponent();

    await user.type(
      screen.getByLabelText(/Current \/ Temporary Password/i),
      "temp-pass",
    );
    await user.type(screen.getByLabelText(/^New Password/i), "short");
    await user.type(screen.getByLabelText(/Confirm New Password/i), "short");
    await user.click(screen.getByRole("button", { name: "Update Password" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "New password must be at least 8 characters long.",
    );
    expect(api.changePassword).not.toHaveBeenCalled();
  });

  it("submits the password change request successfully", async () => {
    const user = userEvent.setup();
    const updatedProfile = {
      id: "user-1",
      email: "tempuser@example.com",
      is_invited: true,
      is_admin: false,
      scanning_enabled: true,
      pushover_token: null,
      must_change_password: false,
    };
    vi.mocked(api.changePassword).mockResolvedValue(updatedProfile);

    renderComponent();

    await user.type(
      screen.getByLabelText(/Current \/ Temporary Password/i),
      "old-pass-123",
    );
    await user.type(
      screen.getByLabelText(/^New Password/i),
      "brand-new-pass-456",
    );
    await user.type(
      screen.getByLabelText(/Confirm New Password/i),
      "brand-new-pass-456",
    );
    await user.click(screen.getByRole("button", { name: "Update Password" }));

    await waitFor(() => {
      expect(api.changePassword).toHaveBeenCalledWith({
        current_password: "old-pass-123",
        new_password: "brand-new-pass-456",
      });
    });

    expect(queryClient.getQueryData(["me"])).toEqual(updatedProfile);
  });

  it("displays server error message on failure", async () => {
    const user = userEvent.setup();
    vi.mocked(api.changePassword).mockRejectedValue(
      new Error("Current password is incorrect."),
    );

    renderComponent();

    await user.type(
      screen.getByLabelText(/Current \/ Temporary Password/i),
      "wrong-password",
    );
    await user.type(
      screen.getByLabelText(/^New Password/i),
      "brand-new-pass-456",
    );
    await user.type(
      screen.getByLabelText(/Confirm New Password/i),
      "brand-new-pass-456",
    );
    await user.click(screen.getByRole("button", { name: "Update Password" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Current password is incorrect.",
    );
  });

  it("triggers signOut when clicking Sign Out", async () => {
    const user = userEvent.setup();
    renderComponent();

    await user.click(screen.getByRole("button", { name: "Sign Out" }));
    expect(mockSignOut).toHaveBeenCalled();
  });
});
