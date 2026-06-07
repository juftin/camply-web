import { useState, type FormEvent } from "react";
import { TentTree, Mail, CheckCircle, ArrowLeft, Loader2 } from "lucide-react";
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
import { submitAccessRequest } from "@/lib/api";

export function EarlyAccess() {
  const { user } = useAuth();
  const email = user?.email ?? "";

  const [name, setName] = useState("");
  const [submitted, setSubmitted] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

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
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to submit. Please try again."
      );
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen bg-background flex flex-col items-center justify-center px-4">
      <div className="w-full max-w-md text-center">
        <div className="mb-6">
          <div className="inline-flex items-center space-x-2">
            <TentTree className="h-8 w-8 text-primary" />
            <span className="text-2xl font-bold">camply</span>
          </div>
        </div>

        <Card className="text-left">
          <CardHeader className="text-center">
            <div className="mx-auto mb-2">
              {submitted ? (
                <CheckCircle className="h-12 w-12 text-green-500" />
              ) : (
                <Mail className="h-12 w-12 text-primary" />
              )}
            </div>
            <CardTitle className="text-xl">
              {submitted ? "You're on the List!" : "Early Access Required"}
            </CardTitle>
            <CardDescription className="text-sm mt-2">
              {submitted
                ? `Thanks, ${name || email}! We'll notify you when early access becomes available.`
                : "camply is currently in private beta. Request early access to start monitoring campsites."}
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {submitted ? (
              <div className="rounded-md bg-green-50 dark:bg-green-950 p-4 border border-green-200 dark:border-green-800">
                <p className="text-sm text-green-800 dark:text-green-200">
                  We're working hard to get camply ready for you. Check back soon!
                </p>
              </div>
            ) : (
              <form onSubmit={handleSubmit} className="space-y-3">
                <div className="space-y-1">
                  <Label htmlFor="ea-email">Email</Label>
                  <Input
                    id="ea-email"
                    type="email"
                    value={email}
                    disabled
                    className="text-muted-foreground"
                  />
                </div>
                <div className="space-y-1">
                  <Label htmlFor="ea-name">Name (optional)</Label>
                  <Input
                    id="ea-name"
                    placeholder="Your name"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                  />
                </div>
                {error && (
                  <p className="text-sm text-destructive">{error}</p>
                )}
                <Button type="submit" className="w-full" disabled={submitting}>
                  {submitting ? (
                    <Loader2 className="h-4 w-4 animate-spin mr-2" />
                  ) : null}
                  Request Access
                </Button>
              </form>
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
