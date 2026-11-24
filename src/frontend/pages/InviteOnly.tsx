import { useState, type FormEvent } from "react";
import {
  Mail,
  CheckCircle,
  Clock,
  XCircle,
  ArrowLeft,
  Loader2,
  RefreshCw,
} from "lucide-react";
import { CamplyLogo } from "@/components/CamplyLogo";
import { Link } from "react-router-dom";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useAuth } from "@/hooks/useAuth";
import { getApiErrorMessage, submitAccessRequest } from "@/lib/api";

export function InviteOnly() {
  const { user, refresh } = useAuth();
  const [email, setEmail] = useState(
    user?.email.includes("@") ? user.email : "",
  );

  const [name, setName] = useState("");
  const [submitted, setSubmitted] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const isApproved = Boolean(user?.is_invited);
  const isPending =
    !isApproved && (user?.invitation_status === "pending" || submitted);
  const isRejected =
    !isApproved && !isPending && user?.invitation_status === "rejected";

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await submitAccessRequest({
        email,
        name: name.trim() || null,
      });
      setSubmitted(true);
      if (user) {
        await refresh();
      }
    } catch (err) {
      setError(getApiErrorMessage(err));
    } finally {
      setSubmitting(false);
    }
  };

  const handleRefresh = async () => {
    setError(null);
    setRefreshing(true);
    try {
      await refresh();
    } catch (err) {
      setError(getApiErrorMessage(err));
    } finally {
      setRefreshing(false);
    }
  };

  const renderHeaderIcon = () => {
    if (isApproved) {
      return (
        <CheckCircle className="h-12 w-12 text-emerald-600 dark:text-emerald-400" />
      );
    }
    if (isPending) {
      return <Clock className="h-12 w-12 text-amber-500" />;
    }
    if (isRejected) {
      return <XCircle className="h-12 w-12 text-destructive" />;
    }
    return <Mail className="h-12 w-12 text-primary" />;
  };

  const renderTitle = () => {
    if (isApproved) return "Invitation Approved";
    if (isPending) return "Pending Review";
    if (isRejected) return "Request Declined";
    return "Invitation Required";
  };

  const renderDescription = () => {
    if (isApproved) {
      return "Your invitation is active. Continue to your dashboard to manage campsite scans.";
    }
    if (isPending) {
      return submitted
        ? `Thanks, ${name.trim() || email}! Your invitation request has been received.`
        : "Your invitation request has been received and is awaiting review.";
    }
    if (isRejected) {
      return "Your invitation request was declined by an administrator.";
    }
    return "This camply instance is invite-only. Request an invitation to start monitoring campsites.";
  };

  return (
    <div className="min-h-screen bg-background flex flex-col items-center justify-center px-4">
      <div className="w-full max-w-md text-center">
        <div className="mb-6">
          <div className="inline-flex items-center space-x-2">
            <CamplyLogo variant="stacked" height={128} />
          </div>
        </div>

        <Card className="text-left">
          <CardHeader className="text-center">
            <div className="mx-auto mb-2">{renderHeaderIcon()}</div>
            <CardTitle className="text-xl">{renderTitle()}</CardTitle>
            <CardDescription className="text-sm mt-2">
              {renderDescription()}
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {isApproved ? (
              <div className="space-y-3">
                <div className="rounded-md bg-emerald-50 dark:bg-emerald-950/50 p-4 border border-emerald-200 dark:border-emerald-800">
                  <p className="text-sm text-emerald-800 dark:text-emerald-200">
                    You have access to campsite monitoring on this instance.
                  </p>
                </div>
                <Button className="w-full" asChild>
                  <Link to="/dashboard">Continue to Dashboard</Link>
                </Button>
              </div>
            ) : isPending ? (
              <div className="space-y-3">
                <div className="rounded-md bg-amber-50 dark:bg-amber-950/40 p-4 border border-amber-200 dark:border-amber-800">
                  <p className="text-sm text-amber-900 dark:text-amber-200">
                    An administrator reviews requests manually in the app —
                    email notifications are not sent. Check back here and
                    refresh your status to see when your access is approved.
                  </p>
                </div>
                {user && (
                  <Button
                    type="button"
                    variant="outline"
                    className="w-full"
                    disabled={refreshing}
                    onClick={handleRefresh}
                  >
                    {refreshing ? (
                      <Loader2 className="h-4 w-4 animate-spin mr-2" />
                    ) : (
                      <RefreshCw className="h-4 w-4 mr-2" />
                    )}
                    Refresh Status
                  </Button>
                )}
              </div>
            ) : isRejected ? (
              <div className="space-y-3">
                <div className="rounded-md bg-destructive/10 p-4 border border-destructive/30">
                  <p className="text-sm text-destructive">
                    Your request was not approved. If an administrator later
                    approves your access, refresh your status below.
                  </p>
                </div>
                <Button
                  type="button"
                  variant="outline"
                  className="w-full"
                  disabled={refreshing}
                  onClick={handleRefresh}
                >
                  {refreshing ? (
                    <Loader2 className="h-4 w-4 animate-spin mr-2" />
                  ) : (
                    <RefreshCw className="h-4 w-4 mr-2" />
                  )}
                  Refresh Status
                </Button>
              </div>
            ) : (
              <form onSubmit={handleSubmit} className="space-y-3">
                <div className="space-y-1">
                  <Label htmlFor="invite-email">Email</Label>
                  <Input
                    id="invite-email"
                    type="email"
                    value={email}
                    onChange={(event) => setEmail(event.target.value)}
                    required
                    className="text-muted-foreground"
                  />
                </div>
                <div className="space-y-1">
                  <Label htmlFor="invite-name">Name (optional)</Label>
                  <Input
                    id="invite-name"
                    placeholder="Your name"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                  />
                </div>
                <Button type="submit" className="w-full" disabled={submitting}>
                  {submitting ? (
                    <Loader2 className="h-4 w-4 animate-spin mr-2" />
                  ) : null}
                  Request Access
                </Button>
              </form>
            )}

            {error && (
              <p role="alert" className="text-sm text-destructive">
                {error}
              </p>
            )}

            <p className="text-xs text-muted-foreground text-center">
              In the meantime, feel free to{" "}
              <Link
                to="/"
                className="text-primary hover:text-primary/80 font-medium"
              >
                explore what campgrounds are available
              </Link>
              .
            </p>
            <Button variant="outline" className="w-full" asChild>
              <Link to="/">
                <ArrowLeft className="h-4 w-4 mr-2" />
                Back to Home
              </Link>
            </Button>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
