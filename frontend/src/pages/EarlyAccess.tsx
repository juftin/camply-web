import { useState, useEffect } from "react";
import { TentTree, Mail, CheckCircle, ArrowLeft } from "lucide-react";
import { Link } from "react-router-dom";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { useAuth } from "@/hooks/useAuth";

export function EarlyAccess() {
  const { user } = useAuth();
  const email = user?.email ?? "";
  const [submitted, setSubmitted] = useState(false);

  // Auto-submit since we already have the email.
  useEffect(() => {
    if (!submitted) {
      const timer = setTimeout(() => setSubmitted(true), 600);
      return () => clearTimeout(timer);
    }
  }, [submitted]);

  return (
    <div className="min-h-screen bg-background flex flex-col items-center justify-center px-4">
      <div className="w-full max-w-md text-center">
        {/* Logo */}
        <div className="mb-6">
          <div className="inline-flex items-center space-x-2">
            <TentTree className="h-8 w-8 text-primary" />
            <span className="text-2xl font-bold">camply</span>
          </div>
        </div>

        <Card className="text-center">
          <CardHeader>
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
              {submitted ? (
                <>
                  Thanks, <strong>{email}</strong>! We'll notify you when
                  early access becomes available.
                </>
              ) : (
                <>
                  camply is currently in private beta. Request early access to
                  start monitoring campsites.
                </>
              )}
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {submitted && (
              <div className="rounded-md bg-green-50 dark:bg-green-950 p-4 border border-green-200 dark:border-green-800">
                <p className="text-sm text-green-800 dark:text-green-200">
                  We're working hard to get camply ready for you. Check back soon!
                </p>
              </div>
            )}
            <p className="text-xs text-muted-foreground">
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
