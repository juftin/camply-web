import * as React from "react";
import { Menu, LayoutDashboard, User, Shield } from "lucide-react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from "@/components/ui/sheet";
import { ThemeToggle } from "@/components/theme-toggle";
import { useAuth } from "@/hooks/useAuth";
import { communityPagesEnabled } from "@/lib/features";
import { CamplyLogo } from "@/components/CamplyLogo";

interface HeaderProps {
  showLogo?: boolean;
}

export function Header({ showLogo = true }: HeaderProps) {
  const location = useLocation();
  const navigate = useNavigate();
  const { user, signupEnabled, autoLogin } = useAuth();
  const [isMobileMenuOpen, setIsMobileMenuOpen] = React.useState(false);

  const isAuthenticated = user !== null;
  const isHowItWorks =
    location.pathname === "/" && location.hash === "#how-it-works";

  const handleAuthNavigation = (mode?: "signup") => {
    if (location.pathname === "/auth") {
      const searchParams = new URLSearchParams(location.search);
      if (mode === "signup") {
        searchParams.set("mode", "signup");
      } else {
        searchParams.delete("mode");
      }
      const queryString = searchParams.toString();
      navigate(`/auth${queryString ? `?${queryString}` : ""}`, {
        replace: true,
      });
    } else {
      navigate(mode === "signup" ? "/auth?mode=signup" : "/auth");
    }
  };

  React.useEffect(() => {
    const behavior = window.matchMedia?.("(prefers-reduced-motion: reduce)")
      ?.matches
      ? "instant"
      : "smooth";
    if (location.hash) {
      const element = document.getElementById(location.hash.substring(1));
      if (element) {
        setTimeout(() => {
          element.scrollIntoView({ behavior });
        }, 100);
      }
    } else {
      window.scrollTo({ top: 0, behavior });
    }
  }, [location]);

  React.useEffect(() => {
    setIsMobileMenuOpen(false);
  }, [location.pathname]);

  React.useEffect(() => {
    const desktop = window.matchMedia?.("(min-width: 768px)");
    const closeOnDesktop = (event: MediaQueryListEvent) => {
      if (event.matches) setIsMobileMenuOpen(false);
    };
    desktop?.addEventListener("change", closeOnDesktop);
    return () => desktop?.removeEventListener("change", closeOnDesktop);
  }, []);

  return (
    <Sheet open={isMobileMenuOpen} onOpenChange={setIsMobileMenuOpen}>
      <header className="sticky top-0 z-50 border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
        <div
          className={`container mx-auto px-4 py-4 flex items-center ${showLogo ? "justify-between" : "justify-center relative"}`}
        >
          <div className="flex shrink-0 items-center h-10">
            {showLogo && (
              <Link to="/" aria-label="camply home">
                <CamplyLogo className="md:max-lg:w-28" />
              </Link>
            )}
          </div>
          <nav className="hidden md:flex whitespace-nowrap gap-2 text-sm lg:gap-6 lg:text-base">
            <Link
              to="/search"
              className={`text-muted-foreground hover:text-foreground ${
                location.pathname === "/search" ? "text-foreground" : ""
              }`}
            >
              Explore
            </Link>
            <Link
              to="/providers"
              className={`text-muted-foreground hover:text-foreground ${
                location.pathname === "/providers" ? "text-foreground" : ""
              }`}
            >
              Providers
            </Link>
            <Link
              to="/#how-it-works"
              className={`text-muted-foreground hover:text-foreground ${
                isHowItWorks ? "text-foreground" : ""
              }`}
            >
              How It Works
            </Link>
            {communityPagesEnabled && (
              <>
                <Link
                  to="/ethos"
                  className={`text-muted-foreground hover:text-foreground ${
                    location.pathname === "/ethos" ? "text-foreground" : ""
                  }`}
                >
                  Ethos
                </Link>
                <Link
                  to="/contribute"
                  className={`text-muted-foreground hover:text-foreground ${
                    location.pathname === "/contribute" ? "text-foreground" : ""
                  }`}
                >
                  Contribute
                </Link>
              </>
            )}
          </nav>

          <SheetTrigger
            className={`md:hidden grid min-h-11 min-w-11 place-items-center ${!showLogo ? "absolute right-4" : ""}`}
            aria-label="Toggle mobile menu"
          >
            <Menu className="h-6 w-6" />
          </SheetTrigger>
          <div
            className={`hidden md:flex items-center space-x-1 lg:space-x-2 md:max-lg:[&_button:not([aria-label])]:px-2 ${!showLogo ? "absolute right-4" : ""}`}
          >
            <ThemeToggle />
            {isAuthenticated ? (
              <>
                {user?.is_admin && (
                  <Button
                    variant="outline"
                    onClick={() => navigate("/admin")}
                    className="border-primary/50 text-primary hover:bg-primary/10"
                  >
                    <Shield className="hidden h-4 w-4 mr-1 lg:block" />
                    Admin
                  </Button>
                )}
                <Button
                  variant="outline"
                  onClick={() => navigate("/dashboard")}
                >
                  <LayoutDashboard className="hidden h-4 w-4 mr-1 lg:block" />
                  Dashboard
                </Button>
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={() => navigate("/profile")}
                  aria-label="Profile"
                >
                  <User className="h-4 w-4" />
                </Button>
              </>
            ) : !autoLogin ? (
              <>
                <Button
                  variant="outline"
                  onClick={() => handleAuthNavigation()}
                >
                  Sign In
                </Button>
                {signupEnabled && (
                  <Button onClick={() => handleAuthNavigation("signup")}>
                    Sign Up
                  </Button>
                )}
              </>
            ) : null}
          </div>
        </div>
      </header>

      <SheetContent aria-describedby={undefined}>
        <SheetHeader>
          <SheetTitle className="text-lg font-semibold">Navigation</SheetTitle>
        </SheetHeader>
        <nav
          aria-label="Mobile navigation"
          className="mt-4 space-y-1 [&_button]:min-h-11"
        >
          <Link
            to="/search"
            className={`flex min-h-11 items-center rounded-md px-2 text-muted-foreground hover:text-foreground ${
              location.pathname === "/search" ? "text-foreground" : ""
            }`}
            onClick={() => setIsMobileMenuOpen(false)}
          >
            Explore
          </Link>
          <Link
            to="/providers"
            className={`flex min-h-11 items-center rounded-md px-2 text-muted-foreground hover:text-foreground ${
              location.pathname === "/providers" ? "text-foreground" : ""
            }`}
            onClick={() => setIsMobileMenuOpen(false)}
          >
            Providers
          </Link>
          <Link
            to="/#how-it-works"
            className={`flex min-h-11 items-center rounded-md px-2 text-muted-foreground hover:text-foreground ${
              isHowItWorks ? "text-foreground" : ""
            }`}
            onClick={() => setIsMobileMenuOpen(false)}
          >
            How It Works
          </Link>
          {communityPagesEnabled && (
            <>
              <Link
                to="/ethos"
                className={`flex min-h-11 items-center rounded-md px-2 text-muted-foreground hover:text-foreground ${
                  location.pathname === "/ethos" ? "text-foreground" : ""
                }`}
                onClick={() => setIsMobileMenuOpen(false)}
              >
                Ethos
              </Link>
              <Link
                to="/contribute"
                className={`flex min-h-11 items-center rounded-md px-2 text-muted-foreground hover:text-foreground ${
                  location.pathname === "/contribute" ? "text-foreground" : ""
                }`}
                onClick={() => setIsMobileMenuOpen(false)}
              >
                Contribute
              </Link>
            </>
          )}
          <div className="pt-4 border-t space-y-3">
            <div className="flex items-center justify-between">
              <ThemeToggle />
            </div>
            <div className="flex flex-col space-y-2">
              {isAuthenticated ? (
                <>
                  {user?.is_admin && (
                    <Button
                      variant="outline"
                      className="border-primary/50 text-primary hover:bg-primary/10"
                      onClick={() => {
                        setIsMobileMenuOpen(false);
                        navigate("/admin");
                      }}
                    >
                      <Shield className="h-4 w-4 mr-1" />
                      Admin
                    </Button>
                  )}
                  <Button
                    onClick={() => {
                      setIsMobileMenuOpen(false);
                      navigate("/dashboard");
                    }}
                  >
                    <LayoutDashboard className="h-4 w-4 mr-1" />
                    Dashboard
                  </Button>
                  <Button
                    variant="outline"
                    onClick={() => {
                      setIsMobileMenuOpen(false);
                      navigate("/profile");
                    }}
                  >
                    <User className="h-4 w-4 mr-1" />
                    Profile
                  </Button>
                </>
              ) : !autoLogin ? (
                <>
                  <Button
                    variant="outline"
                    onClick={() => {
                      setIsMobileMenuOpen(false);
                      handleAuthNavigation();
                    }}
                  >
                    Sign In
                  </Button>
                  {signupEnabled && (
                    <Button
                      onClick={() => {
                        setIsMobileMenuOpen(false);
                        handleAuthNavigation("signup");
                      }}
                    >
                      Sign Up
                    </Button>
                  )}
                </>
              ) : null}
            </div>
          </div>
        </nav>
      </SheetContent>
    </Sheet>
  );
}
