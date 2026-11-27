import { useAuth } from "@/hooks/useAuth";
import { MapPin, Tent } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Link } from "react-router-dom";
import { DismissibleBanner } from "@/components/DismissibleBanner";
import { SearchBar } from "@/components/SearchBar";
import { CamplyLogo } from "@/components/CamplyLogo";

export function Home() {
  const { accountPath, signupEnabled } = useAuth();
  const accountLabel =
    accountPath === "/dashboard"
      ? "Go to dashboard"
      : signupEnabled
        ? "Create an account"
        : "Sign in";

  return (
    <>
      <DismissibleBanner
        id="home-development"
        icon={Tent}
        className="bg-orange-100 border-b border-orange-200 py-3 px-4 text-orange-800"
        closeButtonClassName="hover:bg-orange-200 text-orange-800"
        storageType="session"
      >
        <p className="text-sm font-medium text-center">
          camply is still in development and isn’t ready to use. Follow our
          progress on{" "}
          <a
            href="https://github.com/juftin/camply-web"
            target="_blank"
            rel="noopener noreferrer"
            className="underline hover:no-underline font-semibold"
          >
            GitHub
          </a>
          .
        </p>
      </DismissibleBanner>

      <section className="px-4 py-12 sm:py-16">
        <div className="container mx-auto text-center">
          <CamplyLogo variant="icon" height={96} className="mx-auto mb-6" />
          <h1 className="text-4xl font-bold mb-4 sm:text-5xl">
            Campsite availability alerts
          </h1>
          <p className="text-lg text-muted-foreground mb-8 max-w-2xl mx-auto">
            camply alerts you when it finds an open campsite for your dates.
            Book directly on the provider’s website.
          </p>

          <SearchBar
            placeholder="Search campgrounds..."
            className="max-w-3xl mx-auto mb-4"
          />

          <div className="flex flex-wrap justify-center gap-4 text-sm text-muted-foreground">
            <Link
              to="/search?q=National+Park"
              className="flex min-h-11 items-center gap-1 hover:text-foreground sm:min-h-0 transition-colors"
            >
              <MapPin className="h-4 w-4" />
              National Parks
            </Link>
            <Link
              to="/search?q=State+Park"
              className="flex min-h-11 items-center gap-1 hover:text-foreground sm:min-h-0 transition-colors"
            >
              <MapPin className="h-4 w-4" />
              State Parks
            </Link>
            <Link
              to="/search"
              className="flex min-h-11 items-center gap-1 hover:text-foreground sm:min-h-0 transition-colors"
            >
              <MapPin className="h-4 w-4" />
              All Campgrounds
            </Link>
          </div>

          <div className="mt-6">
            <Button size="lg" asChild>
              <Link to={accountPath}>{accountLabel}</Link>
            </Button>
          </div>
        </div>
      </section>

      <section
        id="how-it-works"
        className="scroll-mt-20 bg-muted/50 px-4 py-12"
      >
        <div className="mx-auto max-w-4xl">
          <h2 className="text-2xl font-bold mb-6">How it works</h2>
          <ol className="grid list-decimal gap-6 pl-5 marker:font-semibold marker:text-primary md:grid-cols-3 md:gap-8">
            <li>
              <h3 className="font-semibold">Find a campground</h3>
              <p className="text-muted-foreground">
                Search by campground or park name.
              </p>
            </li>
            <li>
              <h3 className="font-semibold">Create a scan</h3>
              <p className="text-muted-foreground">
                Choose your dates and any campsite preferences.
              </p>
            </li>
            <li>
              <h3 className="font-semibold">Get alerts</h3>
              <p className="text-muted-foreground">
                Set up notifications in your profile or check your dashboard for
                openings.
              </p>
            </li>
          </ol>
        </div>
      </section>
    </>
  );
}
