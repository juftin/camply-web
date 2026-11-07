import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { beforeEach, expect, it, vi } from "vitest";
import { MobileNotifications } from "./MobileNotifications";

const mocks = vi.hoisted(() => ({
  native: vi.fn(),
  enable: vi.fn(),
  auth: vi.fn(),
  scans: vi.fn(),
}));
vi.mock("@/hooks/useAuth", () => ({ useAuth: mocks.auth }));
vi.mock("@/lib/api", () => ({ listScans: mocks.scans, getScan: vi.fn() }));
vi.mock("@/lib/mobile-notifications", async (original) => ({
  ...(await original<typeof import("@/lib/mobile-notifications")>()),
  nativeNotificationsAvailable: mocks.native,
  enableNativeNotifications: mocks.enable,
}));
const mount = () =>
  render(
    <QueryClientProvider
      client={
        new QueryClient({ defaultOptions: { queries: { retry: false } } })
      }
    >
      <MobileNotifications />
    </QueryClientProvider>,
  );
beforeEach(() => {
  vi.resetAllMocks();
  localStorage.clear();
  mocks.native.mockReturnValue(true);
  mocks.auth.mockReturnValue({
    user: { id: "user1" },
    isReady: true,
    inviteOnly: false,
  });
  mocks.scans.mockResolvedValue({ scans: [], total: 0 });
});

it("leaves ordinary web pages untouched, even outside an auth provider", () => {
  mocks.native.mockReturnValue(false);
  expect(mount().container).toBeEmptyDOMElement();
  expect(mocks.auth).not.toHaveBeenCalled();
});
it("does not poll until the user grants permission, and can disable", async () => {
  mocks.enable.mockResolvedValue(true);
  mount();
  expect(mocks.scans).not.toHaveBeenCalled();
  fireEvent.click(
    screen.getByRole("button", { name: "Enable mobile notifications" }),
  );
  await waitFor(() => expect(mocks.scans).toHaveBeenCalled());
  expect(localStorage.getItem("camply-mobile-notifications:user1")).toBe(
    "true",
  );
  fireEvent.click(
    screen.getByRole("button", { name: "Disable mobile notifications" }),
  );
  expect(localStorage.getItem("camply-mobile-notifications:user1")).toBeNull();
});
it("shows denied permission without polling", async () => {
  mocks.enable.mockResolvedValue(false);
  mount();
  fireEvent.click(screen.getByRole("button"));
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "Notifications are denied",
  );
  expect(mocks.scans).not.toHaveBeenCalled();
});
it("shows permission errors without enabling alerts", async () => {
  mocks.enable.mockRejectedValue(new Error("unavailable"));
  mount();
  fireEvent.click(screen.getByRole("button"));
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "Could not request",
  );
  expect(mocks.scans).not.toHaveBeenCalled();
});
it("does not expose notification controls before login or invitation approval", () => {
  mocks.auth.mockReturnValue({ user: null, isReady: true });
  expect(mount().container).toBeEmptyDOMElement();
  mocks.auth.mockReturnValue({
    user: { id: "user1" },
    isReady: true,
    inviteOnly: true,
    isInvited: false,
  });
  expect(mount().container).toBeEmptyDOMElement();
});
