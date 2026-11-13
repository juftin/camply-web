import {
  act,
  render,
  screen,
  fireEvent,
  waitFor,
} from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, it, expect, vi } from "vitest";
import { NotificationSettings } from "./NotificationSettings";
import { sendTestNotification, updateMe } from "@/lib/api";
import type { MeResponse } from "@/lib/structs";

vi.mock("@/lib/api", () => ({
  updateMe: vi.fn().mockResolvedValue({}),
  sendTestNotification: vi
    .fn()
    .mockResolvedValue({ status: "sent", provider: "ntfy" }),
}));

const renderReviewSettings = (overrides: Partial<MeResponse> = {}) => {
  render(
    <QueryClientProvider client={new QueryClient()}>
      <NotificationSettings
        refresh={vi.fn().mockResolvedValue(undefined)}
        user={{
          id: "1234567a-abcd-1234-1234-123456789abc",
          email: "review@example.test",
          is_invited: true,
          is_admin: false,
          scanning_enabled: true,
          pushover_token: null,
          notification_provider: "ntfy",
          ntfy_topic: "camply-1234567",
          ntfy_server_url: "https://old.example.test",
          ntfy_access_token: "synthetic-old-token",
          ...overrides,
        }}
      />
    </QueryClientProvider>,
  );
};

it.each(["ntfy.sh", "default", "custom"])(
  "clears the saved token when changing to %s and never tests with the old token",
  async (choice) => {
    vi.mocked(sendTestNotification).mockClear();
    renderReviewSettings({
      ntfy_default_subscription_url: "https://app.example.test",
    });
    fireEvent.change(screen.getByLabelText("ntfy server"), {
      target: { value: choice },
    });
    if (choice === "custom") {
      fireEvent.change(screen.getByLabelText("Your ntfy server URL"), {
        target: { value: "https://new.example.test" },
      });
    }
    expect(screen.getByLabelText("Access token (optional)")).toHaveValue("");
    fireEvent.click(
      screen.getByRole("button", { name: "Send test notification" }),
    );
    await waitFor(() =>
      expect(sendTestNotification).toHaveBeenCalledWith(
        expect.objectContaining({ ntfy_access_token: null }),
      ),
    );
  },
);

it("keeps a new server's token when editing only its topic", async () => {
  vi.mocked(updateMe).mockClear();
  renderReviewSettings();
  fireEvent.change(screen.getByLabelText("Your ntfy topic"), {
    target: { value: "edited-topic" },
  });
  fireEvent.click(
    screen.getByRole("button", { name: "Save notification settings" }),
  );
  await waitFor(() =>
    expect(updateMe).toHaveBeenCalledWith(
      expect.objectContaining({ ntfy_access_token: "synthetic-old-token" }),
    ),
  );
});

it("retains a private application's default when subscriptions use ntfy.sh", async () => {
  vi.mocked(updateMe).mockClear();
  renderReviewSettings({
    ntfy_server_url: null,
    ntfy_default_subscription_url: "https://ntfy.sh",
  });
  expect(screen.getByLabelText("ntfy server")).toHaveValue("default");
  fireEvent.click(
    screen.getByRole("button", { name: "Save notification settings" }),
  );
  await waitFor(() =>
    expect(updateMe).toHaveBeenCalledWith(
      expect.objectContaining({ ntfy_server_url: null }),
    ),
  );
});

it.each(["Your ntfy topic", "Notification provider"])(
  "hides saved feedback after editing %s",
  async (field) => {
    renderReviewSettings();
    fireEvent.click(
      screen.getByRole("button", { name: "Save notification settings" }),
    );
    await screen.findByText("Notification settings updated.");
    fireEvent.change(screen.getByLabelText(field), {
      target: {
        value: field === "Your ntfy topic" ? "unsaved-topic" : "pushover",
      },
    });
    expect(
      screen.queryByText("Notification settings updated."),
    ).not.toBeInTheDocument();
  },
);

it("does not confirm edits made while a save is pending", async () => {
  let finish!: (value: MeResponse) => void;
  vi.mocked(updateMe).mockReturnValueOnce(
    new Promise((resolve) => {
      finish = resolve;
    }),
  );
  renderReviewSettings();
  fireEvent.click(
    screen.getByRole("button", { name: "Save notification settings" }),
  );
  await waitFor(() =>
    expect(
      screen.getByRole("button", { name: "Save notification settings" }),
    ).toBeDisabled(),
  );
  fireEvent.change(screen.getByLabelText("Your ntfy topic"), {
    target: { value: "unsaved-during-request" },
  });
  await act(async () =>
    finish({
      id: "user",
      email: "review@example.test",
      is_invited: true,
      is_admin: false,
      scanning_enabled: true,
      pushover_token: null,
    }),
  );
  expect(
    screen.queryByText("Notification settings updated."),
  ).not.toBeInTheDocument();
});

it("explains subscribing in the ntfy app before testing", () => {
  renderReviewSettings();
  expect(
    screen.getByText(
      /In the ntfy app, subscribe using this server and topic, then send a test/,
    ),
  ).toBeInTheDocument();
});

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
    expect(screen.queryByLabelText("Subscription URL")).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Copy subscription URL" }),
    ).not.toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Copy ntfy server URL" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Copy ntfy topic" }),
    ).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("ntfy server"), {
      target: { value: "custom" },
    });
    fireEvent.change(screen.getByLabelText("Your ntfy server URL"), {
      target: { value: "https://custom.example.test/push" },
    });
    fireEvent.change(screen.getByLabelText("ntfy server"), {
      target: { value: "ntfy.sh" },
    });
    fireEvent.change(screen.getByLabelText("ntfy server"), {
      target: { value: "default" },
    });
    fireEvent.change(screen.getByLabelText("ntfy server"), {
      target: { value: "custom" },
    });
    fireEvent.change(screen.getByLabelText("Your ntfy server URL"), {
      target: { value: " https://custom.example.test/push/// " },
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
        ntfy_topic: "camply-random",
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

it("previews the public application server and retains defaults when saving", async () => {
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
  expect(
    screen.queryByLabelText("Your ntfy server URL"),
  ).not.toBeInTheDocument();
  expect(screen.getByLabelText("ntfy server")).toHaveValue("default");
  fireEvent.click(screen.getByText("Save notification settings"));
  await waitFor(() =>
    expect(updateMe).toHaveBeenLastCalledWith({
      notification_provider: "ntfy",
      ntfy_topic: "camply-fallback",
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
        ntfy_topic: "camply-choices",
        ntfy_server_url: "https://ntfy.sh",
        ntfy_access_token: null,
      }),
    );
    fireEvent.change(select, { target: { value: "custom" } });
    expect(screen.getByLabelText("Your ntfy server URL")).toBeInTheDocument();
    expect(screen.getByText("Save notification settings")).toBeDisabled();
  },
);

describe("notification field copying", () => {
  const renderCopySettings = () =>
    render(
      <QueryClientProvider client={new QueryClient()}>
        <NotificationSettings
          refresh={vi.fn()}
          user={{
            id: "1234567a-abcd-1234-1234-123456789abc",
            email: "test@example.test",
            is_invited: true,
            is_admin: false,
            scanning_enabled: true,
            pushover_token: null,
            notification_provider: "ntfy",
            ntfy_topic: "camply-1234567",
            ntfy_server_url: null,
            ntfy_default_subscription_url: "https://push.example.test/prefix",
            ntfy_subscription_url: "https://push.example.test/prefix",
          }}
        />
      </QueryClientProvider>,
    );

  afterEach(() => vi.restoreAllMocks());

  it("copies the resolved public server and current topic without saving", async () => {
    const user = userEvent.setup();
    const copy = vi.spyOn(navigator.clipboard, "writeText").mockResolvedValue();
    vi.mocked(updateMe).mockClear();
    renderCopySettings();
    await user.click(
      screen.getByRole("button", { name: "Copy ntfy server URL" }),
    );
    expect(copy).toHaveBeenLastCalledWith("https://push.example.test/prefix");
    expect(
      screen.getByRole("button", { name: "Copy ntfy server URL" }),
    ).toHaveTextContent("Copied");
    await user.click(screen.getByRole("button", { name: "Copy ntfy topic" }));
    expect(copy).toHaveBeenLastCalledWith("camply-1234567");

    fireEvent.change(screen.getByLabelText("ntfy server"), {
      target: { value: "ntfy.sh" },
    });
    await user.click(
      screen.getByRole("button", { name: "Copy ntfy server URL" }),
    );
    expect(copy).toHaveBeenLastCalledWith("https://ntfy.sh");
    fireEvent.change(screen.getByLabelText("ntfy server"), {
      target: { value: "custom" },
    });
    expect(
      screen.getByRole("button", { name: "Copy ntfy server URL" }),
    ).toBeDisabled();
    fireEvent.change(screen.getByLabelText("Your ntfy server URL"), {
      target: { value: " https://custom.example.test/alerts/// " },
    });
    fireEvent.change(screen.getByLabelText("Your ntfy topic"), {
      target: { value: "edited-topic" },
    });
    expect(
      screen.getByRole("button", { name: "Copy ntfy topic" }),
    ).toHaveTextContent("Copy");
    await user.click(
      screen.getByRole("button", { name: "Copy ntfy server URL" }),
    );
    expect(copy).toHaveBeenLastCalledWith("https://custom.example.test/alerts");
    await user.click(screen.getByRole("button", { name: "Copy ntfy topic" }));
    expect(copy).toHaveBeenLastCalledWith("edited-topic");
    fireEvent.change(screen.getByLabelText("Your ntfy topic"), {
      target: { value: "" },
    });
    expect(
      screen.getByRole("button", { name: "Copy ntfy topic" }),
    ).toBeDisabled();
    expect(updateMe).not.toHaveBeenCalled();
  });

  it("reports clipboard failures and lets the user retry", async () => {
    const user = userEvent.setup();
    const copy = vi
      .spyOn(navigator.clipboard, "writeText")
      .mockRejectedValueOnce(new Error("Clipboard denied"))
      .mockResolvedValue();
    renderCopySettings();
    await user.click(screen.getByRole("button", { name: "Copy ntfy topic" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Copy failed");
    expect(
      screen.getByRole("button", { name: "Copy ntfy topic" }),
    ).toHaveTextContent("Copy");
    await user.click(screen.getByRole("button", { name: "Copy ntfy topic" }));
    expect(copy).toHaveBeenLastCalledWith("camply-1234567");
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Copy ntfy topic" }),
    ).toHaveTextContent("Copied");
  });
});

it("tests unsaved ntfy settings once, shows pending/success feedback and does not save", async () => {
  const user = userEvent.setup();
  let finish!: (value: { status: "sent"; provider: "ntfy" }) => void;
  vi.mocked(sendTestNotification)
    .mockClear()
    .mockReturnValueOnce(
      new Promise((resolve) => {
        finish = resolve;
      }),
    );
  vi.mocked(updateMe).mockClear();
  render(
    <QueryClientProvider client={new QueryClient()}>
      <NotificationSettings
        refresh={vi.fn()}
        user={{
          id: "1234567a-abcd-1234-1234-123456789abc",
          email: "test@example.test",
          is_invited: true,
          is_admin: false,
          scanning_enabled: true,
          pushover_token: null,
          notification_provider: "ntfy",
          ntfy_topic: "saved-topic",
        }}
      />
    </QueryClientProvider>,
  );
  fireEvent.change(screen.getByLabelText("Your ntfy topic"), {
    target: { value: "draft-topic" },
  });
  fireEvent.change(screen.getByLabelText("ntfy server"), {
    target: { value: "custom" },
  });
  expect(
    screen.getByRole("button", { name: "Send test notification" }),
  ).toBeDisabled();
  fireEvent.change(screen.getByLabelText("Your ntfy server URL"), {
    target: { value: "https://custom.example.test/push" },
  });
  fireEvent.change(screen.getByLabelText("Access token (optional)"), {
    target: { value: "draft-token" },
  });
  await user.click(
    screen.getByRole("button", { name: "Send test notification" }),
  );
  expect(sendTestNotification).toHaveBeenCalledExactlyOnceWith({
    notification_provider: "ntfy",
    ntfy_topic: "draft-topic",
    ntfy_server_url: "https://custom.example.test/push",
    ntfy_access_token: "draft-token",
  });
  expect(screen.getByRole("button", { name: "Sending test…" })).toBeDisabled();
  expect(
    screen.getByRole("button", { name: "Save notification settings" }),
  ).toBeDisabled();
  await act(async () => finish({ status: "sent", provider: "ntfy" }));
  expect(await screen.findByRole("status")).toHaveTextContent(
    "Test notification sent",
  );
  expect(updateMe).not.toHaveBeenCalled();
  fireEvent.change(screen.getByLabelText("Your ntfy topic"), {
    target: { value: "another-topic" },
  });
  expect(
    screen.queryByText("Test notification sent. Check your device."),
  ).not.toBeInTheDocument();
});

it("requires a Pushover key for testing and shows a failed test without saving", async () => {
  const user = userEvent.setup();
  vi.mocked(sendTestNotification)
    .mockClear()
    .mockRejectedValueOnce(
      new Error("Pushover is not configured on this server."),
    );
  vi.mocked(updateMe).mockClear();
  render(
    <QueryClientProvider client={new QueryClient()}>
      <NotificationSettings
        refresh={vi.fn()}
        user={{
          id: "user",
          email: "test@example.test",
          is_invited: true,
          is_admin: false,
          scanning_enabled: true,
          pushover_token: null,
          notification_provider: "pushover",
        }}
      />
    </QueryClientProvider>,
  );
  expect(
    screen.getByRole("button", { name: "Send test notification" }),
  ).toBeDisabled();
  fireEvent.change(screen.getByLabelText("Pushover User Key"), {
    target: { value: "draft-key" },
  });
  await user.click(
    screen.getByRole("button", { name: "Send test notification" }),
  );
  expect(sendTestNotification).toHaveBeenCalledExactlyOnceWith({
    notification_provider: "pushover",
    pushover_token: "draft-key",
  });
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "Pushover is not configured",
  );
  expect(updateMe).not.toHaveBeenCalled();
  expect(
    screen.getByRole("button", { name: "Send test notification" }),
  ).toBeEnabled();
});
