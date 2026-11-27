import { useId, useState, type FormEvent } from "react";
import { Settings } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  defaultMobileServerUrl,
  saveMobileServer,
  type MobileServer,
} from "@/lib/mobile-server";

export function MobileServerSettings({
  server,
  compact = false,
}: {
  server: MobileServer;
  compact?: boolean;
}) {
  const id = useId();
  const [open, setOpen] = useState(false);
  const [url, setUrl] = useState(server.url);
  const [auth0ClientId, setAuth0ClientId] = useState(server.auth0ClientId);
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);

  async function connect(event: FormEvent) {
    event.preventDefault();
    setError("");
    setSaving(true);
    try {
      const selected = await saveMobileServer(url, auth0ClientId);
      if (
        server.url === selected.url &&
        server.auth0ClientId === selected.auth0ClientId
      ) {
        setOpen(false);
        return;
      }
      // OAuth transactions, API credentials, and query caches belong to the previous server.
      sessionStorage.clear();
      location.replace(import.meta.env.BASE_URL);
    } catch (cause) {
      setError(
        cause instanceof Error
          ? cause.message
          : "Could not save server settings.",
      );
    } finally {
      setSaving(false);
    }
  }

  return (
    <Dialog
      open={open}
      onOpenChange={(next) => {
        setOpen(next);
        if (!next) return;
        setUrl(server.url);
        setAuth0ClientId(server.auth0ClientId);
        setError("");
      }}
    >
      <DialogTrigger asChild>
        <Button
          variant="outline"
          size={compact ? "icon" : "default"}
          aria-label={compact ? "Server settings" : undefined}
          title={compact ? "Server settings" : undefined}
          className="min-h-11"
        >
          {compact ? <Settings className="h-4 w-4" /> : "Server settings"}
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Server settings</DialogTitle>
          <DialogDescription>
            Switching servers starts a new app session.
          </DialogDescription>
        </DialogHeader>
        <form className="space-y-4" onSubmit={connect}>
          <div className="space-y-2">
            <Label htmlFor={`${id}-url`}>Server URL</Label>
            <Input
              id={`${id}-url`}
              inputMode="url"
              autoCapitalize="none"
              spellCheck={false}
              disabled={saving}
              value={url}
              onChange={(event) => {
                setUrl(event.target.value);
                setAuth0ClientId("");
              }}
            />
          </div>
          <details className="text-sm">
            <summary className="cursor-pointer">Auth0 options</summary>
            <div className="mt-2 space-y-2">
              <Label htmlFor={`${id}-auth0`}>Native Auth0 client ID</Label>
              <Input
                id={`${id}-auth0`}
                disabled={saving}
                value={auth0ClientId}
                onChange={(event) => setAuth0ClientId(event.target.value)}
              />
            </div>
          </details>
          {error && (
            <p role="alert" className="text-sm text-destructive">
              {error}
            </p>
          )}
          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              disabled={saving}
              onClick={() => {
                setUrl(defaultMobileServerUrl);
                setAuth0ClientId("");
                setError("");
              }}
            >
              Use camply.rocks
            </Button>
            <Button type="submit" disabled={saving}>
              Connect
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
