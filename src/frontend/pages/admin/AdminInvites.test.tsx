import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, useLocation } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { AxiosError } from "axios";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { AdminInvites } from "./AdminInvites";
import * as api from "@/lib/api";
import type { AdminAccessRequestItem } from "@/lib/structs";

vi.mock("@/lib/api", async (original) => ({
  ...(await original<typeof import("@/lib/api")>()),
  listAdminAccessRequests: vi.fn(),
  updateAdminAccessRequest: vi.fn(),
}));

const pendingRequest: AdminAccessRequestItem = {
  id: "req-1",
  email: "pending@example.test",
  name: "Pat Camper",
  status: "pending",
  created_at: "2026-10-10T12:00:00Z",
  updated_at: "2026-10-10T12:00:00Z",
  reviewed_at: null,
  reviewed_by_id: null,
  user_id: null,
};

const approvedRequest: AdminAccessRequestItem = {
  id: "req-2",
  email: "approved@example.test",
  name: null,
  status: "approved",
  created_at: "2026-10-08T09:00:00Z",
  updated_at: "2026-10-09T10:00:00Z",
  reviewed_at: "2026-10-09T10:00:00Z",
  reviewed_by_id: "admin-1",
  user_id: "user-2",
};

const rejectedRequest: AdminAccessRequestItem = {
  id: "req-3",
  email: "rejected@example.test",
  name: "Riley",
  status: "rejected",
  created_at: "2026-10-07T08:00:00Z",
  updated_at: "2026-10-07T11:00:00Z",
  reviewed_at: "2026-10-07T11:00:00Z",
  reviewed_by_id: "admin-1",
  user_id: null,
};

function LocationProbe() {
  return <output data-testid="location">{useLocation().search}</output>;
}

describe("AdminInvites", () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    vi.clearAllMocks();
    queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    vi.mocked(api.listAdminAccessRequests).mockResolvedValue({
      access_requests: [pendingRequest, approvedRequest, rejectedRequest],
      total: 3,
    });
  });

  function setup(path = "/admin/invitations") {
    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={[path]}>
          <AdminInvites />
          <LocationProbe />
        </MemoryRouter>
      </QueryClientProvider>,
    );
    return userEvent.setup();
  }

  it("renders access request rows with status badges and linked user links", async () => {
    setup();

    expect(await screen.findByText("pending@example.test")).toBeInTheDocument();
    expect(screen.getByText("Pat Camper")).toBeInTheDocument();
    expect(screen.getByText("approved@example.test")).toBeInTheDocument();
    expect(screen.getByText("rejected@example.test")).toBeInTheDocument();
    expect(screen.getByText("pending")).toBeInTheDocument();
    expect(screen.getByText("approved")).toBeInTheDocument();
    expect(screen.getByText("rejected")).toBeInTheDocument();

    const userLink = screen.getByRole("link", { name: /View User/i });
    expect(userLink).toHaveAttribute("href", "/admin/users/user-2");
    expect(
      screen.getByRole("link", { name: "Invitations" }),
    ).toBeInTheDocument();
  });

  it("filters by status and searches by email or name", async () => {
    const user = setup();
    await screen.findByText("pending@example.test");

    await user.click(screen.getByRole("button", { name: "Pending" }));
    await waitFor(() => {
      expect(api.listAdminAccessRequests).toHaveBeenCalledWith(
        expect.objectContaining({ status: "pending", offset: 0 }),
      );
    });
    expect(screen.getByTestId("location")).toHaveTextContent("status=pending");

    await user.type(
      screen.getByPlaceholderText(/Search by email or name/i),
      "pat",
    );
    await waitFor(() => {
      expect(api.listAdminAccessRequests).toHaveBeenCalledWith(
        expect.objectContaining({
          status: "pending",
          search: "pat",
          offset: 0,
        }),
      );
    });
  });

  it("approves, rejects, and revokes requests and invalidates admin caches", async () => {
    const invalidateSpy = vi.spyOn(queryClient, "invalidateQueries");
    vi.mocked(api.updateAdminAccessRequest).mockResolvedValue({
      ...pendingRequest,
      status: "approved",
    });

    const user = setup();
    await screen.findByText("pending@example.test");

    const approveButtons = screen.getAllByRole("button", { name: "Approve" });
    await user.click(approveButtons[0]);

    await waitFor(() => {
      expect(api.updateAdminAccessRequest).toHaveBeenCalledWith("req-1", {
        status: "approved",
      });
    });
    expect(
      await screen.findByText(
        "Approved invitation request for pending@example.test.",
      ),
    ).toBeInTheDocument();
    expect(invalidateSpy).toHaveBeenCalledWith({
      queryKey: ["admin", "access-requests"],
    });
    expect(invalidateSpy).toHaveBeenCalledWith({
      queryKey: ["admin", "users"],
    });
    expect(invalidateSpy).toHaveBeenCalledWith({
      queryKey: ["admin", "overview"],
    });

    await user.click(screen.getByRole("button", { name: "Reject" }));
    await waitFor(() => {
      expect(api.updateAdminAccessRequest).toHaveBeenCalledWith("req-1", {
        status: "rejected",
      });
    });

    await user.click(screen.getByRole("button", { name: "Revoke" }));
    await waitFor(() => {
      expect(api.updateAdminAccessRequest).toHaveBeenCalledWith("req-2", {
        status: "rejected",
      });
    });
    expect(
      await screen.findByText("Revoked invitation for approved@example.test."),
    ).toBeInTheDocument();

    // Re-approve previously rejected request
    await user.click(approveButtons[1]);
    await waitFor(() => {
      expect(api.updateAdminAccessRequest).toHaveBeenCalledWith("req-3", {
        status: "approved",
      });
    });
  });

  it("displays API error details when a mutation fails", async () => {
    vi.mocked(api.updateAdminAccessRequest).mockRejectedValue(
      new AxiosError("Bad Request", "ERR_BAD_REQUEST", undefined, undefined, {
        status: 400,
        data: {
          detail:
            "You cannot revoke the invitation of your own or the bootstrap administrator account.",
        },
        statusText: "Bad Request",
        headers: {},
        config: {} as never,
      }),
    );

    const user = setup();
    await screen.findByText("approved@example.test");

    await user.click(screen.getByRole("button", { name: "Revoke" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "You cannot revoke the invitation of your own or the bootstrap administrator account.",
    );
  });

  it("shows load errors with retry and supports pagination", async () => {
    vi.mocked(api.listAdminAccessRequests).mockRejectedValueOnce(
      new Error("Server error"),
    );

    const user = setup();
    expect(
      await screen.findByText("Failed to load invitation requests"),
    ).toBeInTheDocument();

    vi.mocked(api.listAdminAccessRequests).mockResolvedValue({
      access_requests: [pendingRequest],
      total: 60,
    });
    await user.click(screen.getByRole("button", { name: "Retry" }));
    expect(await screen.findByText("pending@example.test")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Next" }));
    await waitFor(() => {
      expect(api.listAdminAccessRequests).toHaveBeenCalledWith(
        expect.objectContaining({ offset: 50 }),
      );
    });
  });
});
