import * as React from "react";
import { X, LucideIcon } from "lucide-react";
import { cn } from "@/lib/utils";

interface DismissibleBannerProps {
  id: string;
  children: React.ReactNode;
  className?: string;
  closeButtonClassName?: string;
  showCondition?: boolean;
  icon?: LucideIcon;
  storageType?: "session" | "local";
  dismissible?: boolean;
}

export function DismissibleBanner({
  id,
  children,
  className = "",
  closeButtonClassName = "",
  showCondition = true,
  icon: Icon,
  storageType = "session",
  dismissible = true,
}: DismissibleBannerProps) {
  const [isVisible, setIsVisible] = React.useState(() => {
    if (!dismissible) return true;
    if (typeof window !== "undefined") {
      const storage = storageType === "local" ? localStorage : sessionStorage;
      return storage.getItem(`banner-dismissed-${id}`) !== "true";
    }
    return true;
  });

  const handleDismiss = () => {
    if (!dismissible) return;
    setIsVisible(false);
    const storage = storageType === "local" ? localStorage : sessionStorage;
    storage.setItem(`banner-dismissed-${id}`, "true");
  };

  if (!showCondition || !isVisible) {
    return null;
  }

  return (
    <div className={className}>
      <div
        className={cn(
          "container relative mx-auto",
          dismissible && "max-sm:flex max-sm:items-center max-sm:gap-2",
        )}
      >
        <div className="flex min-w-0 flex-1 items-center justify-center gap-2">
          {Icon && <Icon className="h-5 w-5 flex-shrink-0" />}
          {children}
          {Icon && <Icon className="h-5 w-5 flex-shrink-0" />}
        </div>
        {dismissible && (
          <button
            type="button"
            onClick={handleDismiss}
            className={`grid h-11 w-11 shrink-0 place-items-center rounded focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring sm:absolute sm:right-0 sm:top-1/2 sm:h-auto sm:w-auto sm:-translate-y-1/2 sm:p-1 ${closeButtonClassName}`}
            aria-label="Close banner"
          >
            <X className="h-4 w-4" />
          </button>
        )}
      </div>
    </div>
  );
}
