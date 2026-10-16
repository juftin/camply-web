import * as React from "react";
import { Github } from "lucide-react";
import { Link } from "react-router-dom";
import { Header } from "@/components/Header";
import { CamplyLogo } from "@/components/CamplyLogo";

interface LayoutProps {
  children: React.ReactNode;
}

export function Layout({ children }: LayoutProps) {
  return (
    <div className="min-h-screen bg-background">
      <Header />

      {/* Main Content */}
      <main>{children}</main>

      {/* Footer */}
      <footer className="py-12 px-4 border-t">
        <div className="container mx-auto">
          <div className="flex flex-col md:flex-row justify-between items-center">
            <Link to="/" aria-label="camply home" className="mb-4 md:mb-0">
              <CamplyLogo height={32} />
            </Link>
            <div className="flex flex-wrap items-center justify-center md:justify-start gap-6 text-sm text-muted-foreground">
              <Link to="/faq" className="hover:text-foreground">
                FAQ
              </Link>
              <Link to="/privacy" className="hover:text-foreground">
                Privacy Policy
              </Link>
              <Link to="/terms" className="hover:text-foreground">
                Terms of Service
              </Link>
              <Link to="/contact" className="hover:text-foreground">
                Contact
              </Link>
              <a
                href="https://github.com/juftin/camply/tree/web"
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-1 hover:text-foreground"
              >
                <Github className="h-4 w-4" />
                Built in Public
              </a>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}
