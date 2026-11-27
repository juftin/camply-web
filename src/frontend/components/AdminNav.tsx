import { useEffect, useRef } from "react";
import { Link, useLocation } from "react-router-dom";
import {
  LayoutDashboard,
  Users,
  Mail,
  Radio,
  Activity,
  History,
} from "lucide-react";
import { cn } from "@/lib/utils";

const NAV_ITEMS = [
  { label: "Overview", path: "/admin", icon: LayoutDashboard, exact: true },
  { label: "Users", path: "/admin/users", icon: Users, exact: false },
  {
    label: "Invitations",
    path: "/admin/invitations",
    icon: Mail,
    exact: false,
  },
  { label: "Scans", path: "/admin/scans", icon: Radio, exact: false },
  {
    label: "Operations",
    path: "/admin/operations",
    icon: Activity,
    exact: false,
  },
  { label: "Audit Log", path: "/admin/audit", icon: History, exact: false },
];

export function AdminNav() {
  const location = useLocation();
  const navRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const nav = navRef.current;
    const active = nav?.querySelector<HTMLElement>('[aria-current="page"]');
    if (!nav || !active) return;

    const revealActiveTab = () => {
      const { left, right } = active.getBoundingClientRect();
      const bounds = nav.getBoundingClientRect();
      if (left < bounds.left) nav.scrollLeft += left - bounds.left;
      if (right > bounds.right) nav.scrollLeft += right - bounds.right;
    };

    if (!document.fonts) {
      revealActiveTab();
      return;
    }

    // Fallback text widths can leave the active tab clipped after the font swaps.
    let cancelled = false;
    void document.fonts.ready.then(() => {
      if (!cancelled) revealActiveTab();
    });
    return () => {
      cancelled = true;
    };
  }, [location.pathname]);

  const isActive = (item: (typeof NAV_ITEMS)[0]) => {
    if (item.exact) {
      return location.pathname === item.path;
    }
    return location.pathname.startsWith(item.path);
  };

  return (
    <div className="border-b mb-6">
      <div
        ref={navRef}
        className="flex min-w-0 items-center space-x-1 sm:space-x-2 overflow-x-auto pb-2"
      >
        {NAV_ITEMS.map((item) => {
          const Icon = item.icon;
          const active = isActive(item);
          return (
            <Link
              key={item.path}
              to={item.path}
              aria-current={active ? "page" : undefined}
              className={cn(
                "inline-flex min-h-11 shrink-0 items-center sm:min-h-0 gap-1.5 px-3 py-1.5 rounded-md text-sm font-medium transition-colors whitespace-nowrap",
                active
                  ? "bg-primary text-primary-foreground shadow-sm"
                  : "text-muted-foreground hover:text-foreground hover:bg-muted",
              )}
            >
              <Icon className="h-4 w-4" />
              {item.label}
            </Link>
          );
        })}
      </div>
    </div>
  );
}
