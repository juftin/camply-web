import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { describe, it, expect, vi } from "vitest";
import { NotificationSettings } from "./NotificationSettings";
import { updateMe } from "@/lib/api";

vi.mock("@/lib/api", () => ({ updateMe: vi.fn().mockResolvedValue({}) }));

describe("NotificationSettings", () => {
  it("shows the assigned topic and saves custom server settings", async () => {
    const refresh = vi.fn().mockResolvedValue(undefined);
    render(
      <QueryClientProvider client={new QueryClient()}>
        <NotificationSettings
          refresh={refresh}
          user={{
            id: "user",
            email: "test@example.test",
            is_invited: true,
            is_admin: false,
            scanning_enabled: true,
            pushover_token: null,
            ntfy_topic: "camply-random",
            ntfy_server_url: null,
            ntfy_subscription_url: "https://public.example.test/push",
            ntfy_default_subscription_url: "https://public.example.test/push",
            notification_provider: "pushover",
          }}
        />
      </QueryClientProvider>,
    );
    expect(screen.queryByLabelText("Your ntfy topic")).not.toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Notification provider"), {
      target: { value: "ntfy" },
    });
    expect(screen.getByLabelText("Your ntfy topic")).toHaveValue(
      "camply-random",
    );
    expect(screen.getByLabelText("Your saved subscription URL")).toHaveValue(
      "https://public.example.test/push/camply-random",
    );
    fireEvent.change(screen.getByLabelText("ntfy server"), {
      target: { value: "custom" },
    });
    fireEvent.change(screen.getByLabelText("Your ntfy server URL"), {
      target: { value: "https://custom.example.test/push" },
    });
    fireEvent.change(screen.getByLabelText("Access token (optional)"), {
      target: { value: "synthetic" },
    });
    fireEvent.click(screen.getByText("Save notification settings"));
    await waitFor(() =>
      expect(updateMe).toHaveBeenCalledWith({
        notification_provider: "ntfy",
        ntfy_server_url: "https://custom.example.test/push",
        ntfy_access_token: "synthetic",
      }),
    );
    await waitFor(() => expect(refresh).toHaveBeenCalled());
    expect(await screen.findByRole("status")).toHaveTextContent(
      "Notification settings updated.",
    );
  });
});

it("shows only the application subscription server and retains defaults when saving", async () => {
  render(
    <QueryClientProvider client={new QueryClient()}>
      <NotificationSettings
        refresh={vi.fn()}
        user={{
          id: "fallback",
          email: "fallback@example.test",
          is_invited: true,
          is_admin: false,
          scanning_enabled: true,
          pushover_token: null,
          notification_provider: "ntfy",
          ntfy_topic: "camply-fallback",
          ntfy_server_url: null,
          ntfy_subscription_url: "https://push.example.test/prefix",
          ntfy_default_subscription_url: "https://push.example.test/prefix",
        }}
      />
    </QueryClientProvider>,
  );
  expect(screen.getByLabelText("Your saved subscription URL")).toHaveValue(
    "https://push.example.test/prefix/camply-fallback",
  );
  expect(
    screen.queryByLabelText("Your ntfy server URL"),
  ).not.toBeInTheDocument();
  expect(screen.getByLabelText("ntfy server")).toHaveValue("default");
  fireEvent.click(screen.getByText("Save notification settings"));
  await waitFor(() =>
    expect(updateMe).toHaveBeenLastCalledWith({
      notification_provider: "ntfy",
      ntfy_server_url: null,
      ntfy_access_token: null,
    }),
  );
});

it.each([null, "https://application.example.test"])(
  "offers ntfy.sh and a user-provided URL with configured server %s",
  async (configured) => {
    render(
      <QueryClientProvider client={new QueryClient()}>
        <NotificationSettings
          refresh={vi.fn()}
          user={{
            id: "choices",
            email: "test@example.test",
            is_invited: true,
            is_admin: false,
            scanning_enabled: true,
            pushover_token: null,
            notification_provider: "ntfy",
            ntfy_default_subscription_url: configured,
            ntfy_subscription_url: configured || "https://ntfy.sh",
            ntfy_topic: "camply-choices",
          }}
        />
      </QueryClientProvider>,
    );
    const select = screen.getByLabelText("ntfy server");
    expect(
      screen.queryByRole("option", { name: /Configured server/ }) !== null,
    ).toBe(Boolean(configured));
    fireEvent.change(select, { target: { value: "ntfy.sh" } });
    expect(
      screen.queryByLabelText("Your ntfy server URL"),
    ).not.toBeInTheDocument();
    fireEvent.click(screen.getByText("Save notification settings"));
    await waitFor(() =>
      expect(updateMe).toHaveBeenLastCalledWith({
        notification_provider: "ntfy",
        ntfy_server_url: "https://ntfy.sh",
        ntfy_access_token: null,
      }),
    );
    fireEvent.change(select, { target: { value: "custom" } });
    expect(screen.getByLabelText("Your ntfy server URL")).toBeInTheDocument();
    expect(screen.getByText("Save notification settings")).toBeDisabled();
  },
);
