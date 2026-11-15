import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { Laptop, Loader2 } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/hooks/useAuth";
import {
  getApiErrorMessage,
  listMySessions,
  revokeMySession,
  shouldRetryProtectedQuery,
} from "@/lib/api";
import type { UserSessionItem } from "@/lib/structs";
import { formatSessionDevice, parseDateTime } from "@/lib/utils";

function formatSessionTimestamp(value: string): string {
  const date = parseDateTime(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString();
}

export function ActiveSessions() {
  const { user, authMode, autoLogin } = useAuth();
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const [pendingSessionId, setPendingSessionId] = useState<string | null>(null);
  const [currentSessionRevoked, setCurrentSessionRevoked] = useState(false);
  const [feedback, setFeedback] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  const enabled =
    authMode === "session" &&
    !autoLogin &&
    Boolean(user) &&
    !user?.must_change_password &&
    !currentSessionRevoked;

  const { data, isLoading, error } = useQuery({
    queryKey: ["me", "sessions"],
    queryFn: listMySessions,
    enabled,
    retry: shouldRetryProtectedQuery,
  });

  const revokeMutation = useMutation({
    mutationFn: (session: UserSessionItem) => revokeMySession(session.id),
    onMutate: (session) => {
      setFeedback(null);
      setActionError(null);
      setPendingSessionId(session.id);
    },
    onSuccess: async (_data, session) => {
      if (session.is_current) {
        setCurrentSessionRevoked(true);
        await queryClient.cancelQueries();
        queryClient.removeQueries({
          predicate: (query) =>
            !(query.queryKey.length === 1 && query.queryKey[0] === "me"),
        });
        queryClient.setQueryData(["me"], null);
        navigate("/auth", { replace: true });
        return;
      }

      await queryClient.invalidateQueries({ queryKey: ["me", "sessions"] });
      setFeedback("Session revoked.");
    },
    onError: (err) => {
      setActionError(getApiErrorMessage(err));
    },
    onSettled: () => {
      setPendingSessionId(null);
    },
  });

  if (!enabled) return null;

  const sessions = data?.items ?? [];

  return (
    <section
      aria-labelledby="active-sessions-heading"
      className="pt-4 border-t space-y-3"
    >
      <div className="space-y-1">
        <h3
          id="active-sessions-heading"
          className="text-sm font-medium flex items-center gap-2"
        >
          <Laptop className="h-4 w-4 text-muted-foreground" />
          Active Sessions
        </h3>
        <p className="text-xs text-muted-foreground">
          Manage browsers and devices currently signed in to your account.
        </p>
      </div>

      {isLoading && (
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <Loader2 className="h-4 w-4 animate-spin" />
          <span>Loading active sessions…</span>
        </div>
      )}

      {error ? (
        <p role="alert" className="text-sm text-destructive">
          {getApiErrorMessage(error)}
        </p>
      ) : null}

      {!isLoading && !error && sessions.length === 0 && (
        <p className="text-sm text-muted-foreground">
          No active sessions found.
        </p>
      )}

      {!isLoading && !error && sessions.length > 0 && (
        <ul className="space-y-2">
          {sessions.map((session) => {
            const isPending = pendingSessionId === session.id;
            return (
              <li
                key={session.id}
                className="flex flex-col gap-2 rounded-md border p-3 sm:flex-row sm:items-center sm:justify-between"
              >
                <div className="min-w-0 space-y-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <span
                      className="text-sm font-medium truncate"
                      title={session.user_agent ?? undefined}
                    >
                      {formatSessionDevice(session.user_agent)}
                    </span>
                    {session.is_current && (
                      <Badge variant="secondary">Current</Badge>
                    )}
                  </div>
                  <div className="flex flex-wrap items-center gap-x-2 gap-y-0.5 text-xs text-muted-foreground">
                    {session.ip_address && <span>IP {session.ip_address}</span>}
                    <span>
                      Signed in {formatSessionTimestamp(session.created_at)}
                    </span>
                    <span>
                      Expires {formatSessionTimestamp(session.expires_at)}
                    </span>
                  </div>
                </div>
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  className="shrink-0 self-start sm:self-center"
                  disabled={isPending}
                  onClick={() => revokeMutation.mutate(session)}
                >
                  {isPending ? "Revoking…" : "Revoke"}
                </Button>
              </li>
            );
          })}
        </ul>
      )}

      {feedback && (
        <p role="status" className="text-sm text-muted-foreground">
          {feedback}
        </p>
      )}

      {actionError && (
        <p role="alert" className="text-sm text-destructive">
          {actionError}
        </p>
      )}
    </section>
  );
}
