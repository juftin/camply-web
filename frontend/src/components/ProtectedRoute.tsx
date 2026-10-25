import type { ReactNode } from "react";
import { Navigate, useLocation } from "react-router-dom";
import { useAuth } from "@/hooks/useAuth";
import { InviteOnly } from "@/pages/InviteOnly";
import { ChangePasswordRequired } from "@/components/ChangePasswordRequired";

export function ProtectedRoute({
  children,
  requireInvite = false,
}: {
  children: ReactNode;
  requireInvite?: boolean;
}) {
  const { user, isReady, isLoading, error, inviteOnly, isInvited } = useAuth();
  const location = useLocation();
  if (isLoading || !isReady) {
    return (
      <div role="status" className="p-8 text-center">
        Loading your account…
      </div>
    );
  }
  if (error) {
    return (
      <div role="alert" className="p-8 text-center">
        {error}
      </div>
    );
  }
  if (!user)
    return (
      <Navigate
        to={`/auth?returnTo=${encodeURIComponent(location.pathname + location.search + location.hash)}`}
        replace
      />
    );
  if (user.must_change_password) return <ChangePasswordRequired />;
  if (requireInvite && inviteOnly && !isInvited) return <InviteOnly />;
  return <>{children}</>;
}
