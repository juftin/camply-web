import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { CopyButton } from "@/components/CopyButton";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

import { sendTestNotification, updateMe } from "@/lib/api";
import type { MeResponse, MeUpdateRequest } from "@/lib/structs";

export const NotificationSettings = ({
  user,
  refresh,
}: {
  user: MeResponse;
  refresh: () => Promise<void>;
}) => {
  const [provider, setProvider] = useState<"pushover" | "ntfy">(
    user.notification_provider ?? "pushover",
  );
  const [pushoverKey, setPushoverKey] = useState(user.pushover_token ?? "");
  const [topic, setTopic] = useState(
    user.ntfy_topic || `camply-${user.id.slice(0, 7)}`,
  );
  const publicServer = "https://ntfy.sh";
  const savedServer = user.ntfy_server_url?.replace(/\/+$/, "");
  const [serverChoice, setServerChoice] = useState<
    "default" | "ntfy.sh" | "custom"
  >(
    savedServer
      ? savedServer === publicServer
        ? "ntfy.sh"
        : "custom"
      : user.ntfy_default_subscription_url
        ? "default"
        : "ntfy.sh",
  );
  const [server, setServer] = useState(
    savedServer && savedServer !== publicServer ? savedServer : "",
  );
  const subscriptionServer =
    serverChoice === "default"
      ? user.ntfy_default_subscription_url || publicServer
      : serverChoice === "ntfy.sh"
        ? publicServer
        : server.trim();
  const [token, setToken] = useState(user.ntfy_access_token ?? "");
  const settings: MeUpdateRequest = {
    notification_provider: provider,
    ...(provider === "ntfy"
      ? {
          ntfy_topic: topic.trim(),
          ntfy_server_url:
            serverChoice === "default"
              ? null
              : serverChoice === "ntfy.sh"
                ? publicServer
                : server.trim(),
          ntfy_access_token: token.trim() || null,
        }
      : { pushover_token: pushoverKey.trim() || null }),
  };
  const mutation = useMutation({
    mutationFn: (payload: MeUpdateRequest) => updateMe(payload),
    onSuccess: refresh,
  });
  const testMutation = useMutation({
    mutationFn: (payload: MeUpdateRequest) => sendTestNotification(payload),
  });
  const currentTest =
    JSON.stringify(testMutation.variables) === JSON.stringify(settings);
  const currentSave =
    JSON.stringify(mutation.variables) === JSON.stringify(settings);
  const invalidNtfy =
    provider === "ntfy" &&
    (!topic.trim() || (serverChoice === "custom" && !server.trim()));
  return (
    <div className="space-y-2">
      <Label htmlFor="notification-provider">Notification provider</Label>
      <select
        id="notification-provider"
        className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
        value={provider}
        onChange={(event) =>
          setProvider(event.target.value as "pushover" | "ntfy")
        }
      >
        <option value="pushover">Pushover</option>
        <option value="ntfy">ntfy</option>
      </select>
      <p className="text-xs text-muted-foreground">
        Alerts are sent through your selected provider.
      </p>
      {provider === "pushover" && (
        <>
          <Label htmlFor="pushover-key">Pushover User Key</Label>
          <Input
            id="pushover-key"
            type="password"
            value={pushoverKey}
            onChange={(event) => setPushoverKey(event.target.value)}
            placeholder="Enter your Pushover user key"
          />
          <p className="text-xs text-muted-foreground">
            Find your user key in the Pushover app or at{" "}
            <a
              href="https://pushover.net"
              target="_blank"
              rel="noopener noreferrer"
              className="text-primary hover:underline"
            >
              pushover.net
            </a>
            .
          </p>
        </>
      )}
      {provider === "ntfy" && (
        <>
          <Label htmlFor="ntfy-server-choice">ntfy server</Label>
          <div className="flex items-center gap-2">
            <select
              id="ntfy-server-choice"
              className="min-w-0 flex-1 rounded-md border border-input bg-background px-3 py-2 text-sm"
              value={serverChoice}
              onChange={(event) => {
                setToken("");
                setServerChoice(
                  event.target.value as "default" | "ntfy.sh" | "custom",
                );
              }}
            >
              {user.ntfy_default_subscription_url && (
                <option value="default">
                  Configured server ({user.ntfy_default_subscription_url})
                </option>
              )}
              <option value="ntfy.sh">ntfy.sh</option>
              <option value="custom">Enter your own server</option>
            </select>
            {serverChoice !== "custom" && (
              <CopyButton
                label="Copy ntfy server URL"
                value={subscriptionServer.replace(/\/+$/, "")}
              />
            )}
          </div>
          {serverChoice === "custom" && (
            <>
              <Label htmlFor="ntfy-server">Your ntfy server URL</Label>
              <div className="flex items-center gap-2">
                <Input
                  id="ntfy-server"
                  className="min-w-0 flex-1"
                  type="url"
                  value={server}
                  onChange={(event) => {
                    setToken("");
                    setServer(event.target.value);
                  }}
                  placeholder="https://ntfy.example.com"
                />
                <CopyButton
                  label="Copy ntfy server URL"
                  value={subscriptionServer.replace(/\/+$/, "")}
                />
              </div>
            </>
          )}
          <Label htmlFor="ntfy-topic">Your ntfy topic</Label>
          <div className="flex items-center gap-2">
            <Input
              id="ntfy-topic"
              className="min-w-0 flex-1"
              value={topic}
              onChange={(event) => setTopic(event.target.value)}
              maxLength={64}
            />
            <CopyButton label="Copy ntfy topic" value={topic.trim()} />
          </div>
          <p className="text-xs text-muted-foreground">
            Defaults to camply- followed by the first seven characters of your
            user ID, with a suffix if already taken. You can change it.
          </p>
          <p className="text-xs text-muted-foreground">
            In the ntfy app, subscribe using this server and topic, then send a
            test.
          </p>
          <Label htmlFor="ntfy-token">Access token (optional)</Label>
          <Input
            id="ntfy-token"
            type="password"
            autoComplete="off"
            value={token}
            onChange={(event) => setToken(event.target.value)}
          />
          <p className="text-xs text-muted-foreground">
            Use a token with publish permission for your selected server.
            Changing servers clears the token.
          </p>
        </>
      )}
      <Button
        size="sm"
        disabled={mutation.isPending || testMutation.isPending || invalidNtfy}
        onClick={() => mutation.mutate(settings)}
      >
        Save notification settings
      </Button>
      <Button
        type="button"
        variant="outline"
        size="sm"
        disabled={
          mutation.isPending ||
          testMutation.isPending ||
          invalidNtfy ||
          (provider === "pushover" && !pushoverKey.trim())
        }
        onClick={() => testMutation.mutate(settings)}
      >
        {testMutation.isPending ? "Sending test…" : "Send test notification"}
      </Button>
      <p className="text-xs text-muted-foreground">
        Send a test using the settings above without saving them.
      </p>
      {currentTest && testMutation.isSuccess && (
        <p role="status">Test notification sent. Check your device.</p>
      )}
      {currentTest && testMutation.isError && (
        <p role="alert">{testMutation.error.message}</p>
      )}
      {currentSave && mutation.isSuccess && (
        <p role="status">Notification settings updated.</p>
      )}
      {currentSave && mutation.isError && (
        <p role="alert">
          Could not save notification settings. Check your settings and choose
          an unused topic.
        </p>
      )}
    </div>
  );
};
