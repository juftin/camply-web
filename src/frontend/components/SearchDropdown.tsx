import { Mountain, Tent, Loader2 } from "lucide-react";
import { toTitleCase } from "@/lib/utils";
import {
  useEffect,
  useLayoutEffect,
  useRef,
  useState,
  type RefObject,
} from "react";
import { SearchResult } from "@/lib/structs.ts";

interface SearchDropdownProps {
  results: SearchResult[];
  isLoading: boolean;
  error: Error | null;
  query: string;
  isOpen: boolean;
  onSelect: (result: SearchResult) => void;
  onViewAll?: () => void;
  isFetching?: boolean;
  selectedIndex?: number;
  anchorRef?: RefObject<HTMLDivElement>;
}

export function SearchDropdown({
  results,
  isLoading,
  error,
  query,
  isOpen,
  onSelect,
  onViewAll,
  isFetching,
  selectedIndex = -1,
  anchorRef,
}: SearchDropdownProps) {
  const panelRef = useRef<HTMLDivElement>(null);
  const itemRefs = useRef<(HTMLDivElement | null)[]>([]);
  const [placement, setPlacement] = useState<{
    above: boolean;
    height: number;
  }>();
  const visible = isOpen && query.trim().length >= 2;

  // The visual viewport also changes when an on-screen keyboard opens.
  useLayoutEffect(() => {
    const anchor = anchorRef?.current;
    const panel = panelRef.current;
    if (!visible || !anchor || !panel) return;
    const viewport = window.visualViewport;
    const phone = window.matchMedia("(max-width: 639.98px)");

    function updatePlacement() {
      if (!phone.matches || !anchor || !panel) {
        setPlacement(undefined);
        return;
      }
      const { top, bottom } = anchor.getBoundingClientRect();
      const viewportTop = viewport?.offsetTop ?? 0;
      const viewportHeight = viewport?.height ?? window.innerHeight;
      const viewportBottom = viewportTop + viewportHeight;
      if (bottom <= viewportTop || top >= viewportBottom) {
        setPlacement({ above: false, height: 0 });
        return;
      }
      // Leave 4px next to the field and 8px at the screen edge.
      const above = top - viewportTop - 12;
      const below = viewportBottom - bottom - 12;
      const desired = Math.min(
        panel.scrollHeight + 2,
        viewportHeight * 0.45,
        320,
      );
      const placeAbove = below < desired && above > below;
      const height = Math.floor(
        Math.max(0, Math.min(desired, placeAbove ? above : below)),
      );
      setPlacement((previous) =>
        previous?.above === placeAbove && previous.height === height
          ? previous
          : { above: placeAbove, height },
      );
    }

    updatePlacement();
    window.addEventListener("scroll", updatePlacement, { passive: true });
    window.addEventListener("resize", updatePlacement);
    viewport?.addEventListener("resize", updatePlacement);
    viewport?.addEventListener("scroll", updatePlacement);
    return () => {
      window.removeEventListener("scroll", updatePlacement);
      window.removeEventListener("resize", updatePlacement);
      viewport?.removeEventListener("resize", updatePlacement);
      viewport?.removeEventListener("scroll", updatePlacement);
    };
  }, [anchorRef, visible, query, results, isLoading, error]);

  useEffect(() => {
    const panel = panelRef.current;
    const selected = itemRefs.current[selectedIndex];
    if (!visible || !panel || !selected) return;
    const bounds = panel.getBoundingClientRect();
    const item = selected.getBoundingClientRect();
    const delta =
      item.top < bounds.top
        ? item.top - bounds.top - panel.clientTop
        : Math.max(
            0,
            item.bottom - bounds.top - panel.clientTop - panel.clientHeight,
          );
    if (delta !== 0) {
      panel.scrollTo({
        top: panel.scrollTop + delta,
        behavior: window.matchMedia?.("(prefers-reduced-motion: reduce)")
          ?.matches
          ? "instant"
          : "smooth",
      });
    }
  }, [selectedIndex, visible]);

  // Always render the dropdown container to prevent layout shifts
  return (
    <div
      ref={panelRef}
      data-search-suggestions=""
      style={
        placement && {
          maxHeight: placement.height,
          ...(placement.above && {
            top: "auto",
            bottom: "calc(100% + 0.25rem)",
            marginTop: 0,
          }),
        }
      }
      className={`absolute top-full left-0 right-0 mt-1 bg-background border border-border rounded-md shadow-lg z-50 max-h-[min(20rem,45dvh)] overflow-y-auto overscroll-contain motion-safe:transition-[opacity,transform] motion-safe:duration-200 ${
        visible && placement?.height !== 0
          ? "opacity-100 visible motion-safe:scale-100"
          : "opacity-0 invisible motion-safe:scale-95 pointer-events-none"
      }`}
    >
      {query.trim().length >= 2 && (
        <>
          {/* Only show loading spinner if we have no data and are loading */}
          {isLoading && results.length === 0 ? (
            <div className="flex items-center justify-center p-4">
              <Loader2 className="h-4 w-4 animate-spin mr-2" />
              <span className="text-sm text-muted-foreground">
                Searching campgrounds...
              </span>
            </div>
          ) : error ? (
            <div className="p-4">
              <p className="text-sm text-red-600 text-center">
                Failed to search campgrounds. Please try again.
              </p>
            </div>
          ) : results.length === 0 && !isLoading ? (
            <div className="p-4">
              <p className="break-words text-sm text-muted-foreground text-center">
                No campgrounds found for "{query}". Try a different search term.
              </p>
            </div>
          ) : (
            <div className="py-1 relative">
              {/* Subtle loading indicator when fetching new data */}
              {isFetching && results.length > 0 && (
                <div className="absolute top-1 right-2 z-10">
                  <Loader2 className="h-3 w-3 animate-spin text-muted-foreground" />
                </div>
              )}
              {results.map((result, index) => (
                <div
                  key={result.id}
                  ref={(el) => (itemRefs.current[index] = el)}
                  className={`min-h-11 px-4 py-3 cursor-pointer transition-colors border-b last:border-b-0 ${
                    index === selectedIndex
                      ? "bg-primary/15 ring-1 ring-primary/20"
                      : "hover:bg-muted"
                  } ${isFetching ? "opacity-75" : "opacity-100"}`}
                  onClick={() => onSelect(result)}
                >
                  <div className="flex items-start space-x-3">
                    <div className="flex-shrink-0 mt-0.5">
                      {result.entity_type === "RecreationArea" ? (
                        <Mountain className="h-4 w-4 text-primary" />
                      ) : (
                        <Tent className="h-4 w-4 text-primary" />
                      )}
                    </div>
                    <div className="flex-1 min-w-0">
                      <h4 className="text-sm font-medium text-foreground truncate">
                        {toTitleCase(
                          result.entity_type === "RecreationArea"
                            ? result.recreation_area_name || ""
                            : result.campground_name || "",
                        )}
                      </h4>
                      <p className="break-words text-xs text-muted-foreground">
                        {toTitleCase(result.provider_name)}
                      </p>
                      {result.entity_type === "Campground" &&
                        result.recreation_area_name && (
                          <p className="break-words text-xs text-muted-foreground">
                            in {toTitleCase(result.recreation_area_name)}
                          </p>
                        )}
                    </div>
                    <div className="shrink-0">
                      <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-primary/10 text-primary">
                        {result.entity_type === "RecreationArea"
                          ? "Area"
                          : "Camp"}
                      </span>
                    </div>
                  </div>
                </div>
              ))}
              {results.length > 0 && onViewAll && (
                <div
                  className="min-h-11 content-center px-4 py-2 sm:min-h-0 bg-muted/40 hover:bg-muted cursor-pointer break-words text-center text-xs font-medium text-primary border-t transition-colors"
                  onClick={onViewAll}
                >
                  View all results for "{query}" →
                </div>
              )}
            </div>
          )}
        </>
      )}
    </div>
  );
}
