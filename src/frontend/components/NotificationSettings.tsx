import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

import { updateMe } from "@/lib/api";
import type { MeResponse } from "@/lib/structs";

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
  const subscriptionUrl = `${(user.ntfy_subscription_url || "https://ntfy.sh").replace(/\/+$/, "")}/${user.ntfy_topic ?? ""}`;
  const [token, setToken] = useState(user.ntfy_access_token ?? "");
  const mutation = useMutation({
    mutationFn: () =>
      updateMe({
        notification_provider: provider,
        ...(provider === "ntfy"
          ? {
              ntfy_server_url:
                serverChoice === "default"
                  ? null
                  : serverChoice === "ntfy.sh"
                    ? publicServer
                    : server.trim(),
              ntfy_access_token: token.trim() || null,
            }
          : {}),
      }),
    onSuccess: refresh,
  });
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
      {provider === "ntfy" && (
        <>
          <Label htmlFor="ntfy-server-choice">ntfy server</Label>
          <select
            id="ntfy-server-choice"
            className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
            value={serverChoice}
            onChange={(event) =>
              setServerChoice(
                event.target.value as "default" | "ntfy.sh" | "custom",
              )
            }
          >
            {user.ntfy_default_subscription_url && (
              <option value="default">
                Configured server ({user.ntfy_default_subscription_url})
              </option>
            )}
            <option value="ntfy.sh">ntfy.sh</option>
            <option value="custom">Enter your own server</option>
          </select>
          {serverChoice === "custom" && (
            <>
              <Label htmlFor="ntfy-server">Your ntfy server URL</Label>
              <Input
                id="ntfy-server"
                type="url"
                value={server}
                onChange={(event) => setServer(event.target.value)}
                placeholder="https://ntfy.example.com"
              />
            </>
          )}
          <Label htmlFor="ntfy-topic">Your ntfy topic</Label>
          <Input id="ntfy-topic" value={user.ntfy_topic ?? ""} readOnly />
          <Label htmlFor="ntfy-subscription-url">
            Your saved subscription URL
          </Label>
          <Input id="ntfy-subscription-url" value={subscriptionUrl} readOnly />
          <p className="text-xs text-muted-foreground">
            Subscribe using this URL, or use its server and topic in the ntfy
            app. Save changes to update the URL shown here. Keep the topic
            private: public servers allow anyone who knows it to read or publish
            messages.
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
          </p>
        </>
      )}
      <Button
        size="sm"
        disabled={
          mutation.isPending ||
          (provider === "ntfy" && serverChoice === "custom" && !server.trim())
        }
        onClick={() => mutation.mutate()}
      >
        Save notification settings
      </Button>
      {mutation.isSuccess && (
        <p role="status">Notification settings updated.</p>
      )}
      {mutation.isError && (
        <p role="alert">
          Could not save notification settings. Check the server URL and try
          again.
        </p>
      )}
    </div>
  );
};
