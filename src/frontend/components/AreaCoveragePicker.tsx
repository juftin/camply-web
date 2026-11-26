import { useEffect, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { ChevronDown, X } from "lucide-react";
import { getMonitoringCampgrounds } from "@/lib/api";
import { cn } from "@/lib/utils";
import { Button } from "./ui/button";
import { Input } from "./ui/input";

/** Keep a provider/area draft's selected ID map independent of choice pagination. */
export function AreaCoveragePicker({
  providerId,
  areaId,
  mode,
  onModeChange,
  selected,
  onSelectedChange,
}: {
  providerId: number;
  areaId: string;
  mode: "all" | "selected";
  onModeChange: (mode: "all" | "selected") => void;
  selected: Record<string, string>;
  onSelectedChange: (selected: Record<string, string>) => void;
}) {
  const [query, setQuery] = useState("");
  const [offset, setOffset] = useState(0);
  const [open, setOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const choices = useQuery({
    queryKey: ["monitoring-campgrounds", providerId, areaId, query, offset],
    queryFn: () =>
      getMonitoringCampgrounds(providerId, areaId, {
        query,
        offset,
        limit: 50,
      }),
    retry: false,
  });

  useEffect(() => {
    if (mode !== "selected") {
      setOpen(false);
    }
  }, [mode]);

  useEffect(() => {
    if (!open) return;

    const handlePointerDown = (event: Event) => {
      if (
        dropdownRef.current &&
        !dropdownRef.current.contains(event.target as Node)
      ) {
        setOpen(false);
      }
    };

    // Intercept Escape on window capture before Radix Dialog's document listener closes the modal.
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        event.preventDefault();
        event.stopPropagation();
        setOpen(false);
        dropdownRef.current?.querySelector("button")?.focus();
      }
    };

    document.addEventListener("mousedown", handlePointerDown);
    document.addEventListener("touchstart", handlePointerDown);
    window.addEventListener("keydown", handleKeyDown, { capture: true });
    return () => {
      document.removeEventListener("mousedown", handlePointerDown);
      document.removeEventListener("touchstart", handlePointerDown);
      window.removeEventListener("keydown", handleKeyDown, { capture: true });
    };
  }, [open]);

  const remove = (id: string) => {
    const next = { ...selected };
    delete next[id];
    onSelectedChange(next);
  };
  const selectedEntries = Object.entries(selected);
  const triggerLabel =
    selectedEntries.length === 0
      ? "Select campgrounds…"
      : selectedEntries.length === 1
        ? selectedEntries[0][1] || selectedEntries[0][0]
        : `${selectedEntries.length} campgrounds selected`;

  return (
    <fieldset className="space-y-3 min-w-0">
      <legend className="font-medium">Campground coverage</legend>
      <label className="flex gap-2">
        <input
          type="radio"
          name="coverage-mode"
          checked={mode === "all"}
          onChange={() => onModeChange("all")}
        />
        All campgrounds
      </label>
      <p className="text-sm text-muted-foreground">
        {choices.data?.eligible_total ?? "…"} eligible campgrounds.
      </p>
      <label className="flex gap-2">
        <input
          type="radio"
          name="coverage-mode"
          checked={mode === "selected"}
          onChange={() => onModeChange("selected")}
        />
        Selected campgrounds
      </label>
      {mode === "selected" && (
        <div className="space-y-2 min-w-0">
          <p role="status" aria-live="polite" className="sr-only">
            {selectedEntries.length} selected
          </p>
          <div className="relative w-full" ref={dropdownRef}>
            <button
              type="button"
              aria-expanded={open}
              aria-haspopup="listbox"
              onClick={() => setOpen((prev) => !prev)}
              className={cn(
                "flex h-11 w-full sm:h-10 items-center justify-between rounded-md border border-input bg-background px-3 py-2 text-sm text-left ring-offset-background transition-colors hover:bg-accent/40 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2",
                selectedEntries.length === 0 && "text-muted-foreground",
              )}
            >
              <span className="truncate">{triggerLabel}</span>
              <ChevronDown
                className={cn(
                  "h-4 w-4 shrink-0 text-muted-foreground transition-transform",
                  open && "rotate-180",
                )}
              />
            </button>
            {open && (
              <div className="relative sm:absolute sm:top-full sm:left-0 z-50 mt-1.5 w-full rounded-md border bg-popover p-2 text-popover-foreground shadow-lg space-y-2">
                <Input
                  type="search"
                  aria-label="Search area campgrounds"
                  placeholder="Search campgrounds…"
                  value={query}
                  onChange={(event) => {
                    setQuery(event.target.value);
                    setOffset(0);
                  }}
                />
                {choices.isPending && (
                  <p aria-live="polite" className="px-1 text-sm">
                    Loading campgrounds…
                  </p>
                )}
                {choices.isError && (
                  <p role="alert" className="px-1 text-sm">
                    Campgrounds could not load.{" "}
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      onClick={() => void choices.refetch()}
                    >
                      Retry choices
                    </Button>
                  </p>
                )}
                <div
                  role="listbox"
                  aria-multiselectable="true"
                  className="max-h-48 overflow-y-auto space-y-1"
                >
                  {choices.data?.items.map((item) => (
                    <label
                      key={item.id}
                      className="flex min-h-11 items-center gap-2 rounded-sm sm:min-h-0 px-2 py-1.5 text-sm hover:bg-accent hover:text-accent-foreground cursor-pointer break-words"
                    >
                      <input
                        type="checkbox"
                        className="mt-0.5 shrink-0"
                        checked={item.id in selected}
                        onChange={(event) =>
                          event.target.checked
                            ? onSelectedChange({
                                ...selected,
                                [item.id]: item.name,
                              })
                            : remove(item.id)
                        }
                      />
                      <span className="min-w-0 break-words">{item.name}</span>
                    </label>
                  ))}
                  {choices.data && !choices.data.items.length && (
                    <p className="px-2 py-1.5 text-sm text-muted-foreground">
                      {choices.data.eligible_total
                        ? "No campgrounds match this search."
                        : "No eligible campgrounds. Saved unavailable choices remain selected until removed."}
                    </p>
                  )}
                </div>
                <div className="flex flex-wrap justify-between gap-2 border-t pt-2">
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    className="h-11 px-2.5 text-xs sm:h-8"
                    disabled={!offset}
                    onClick={() =>
                      setOffset((value) => Math.max(0, value - 50))
                    }
                  >
                    Previous campgrounds
                  </Button>
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    className="h-11 px-2.5 text-xs sm:h-8"
                    disabled={!choices.data?.has_more}
                    onClick={() => setOffset((value) => value + 50)}
                  >
                    Next campgrounds
                  </Button>
                </div>
              </div>
            )}
          </div>
          {selectedEntries.length > 0 && (
            <ul className="flex flex-wrap gap-1.5">
              {selectedEntries.map(([id, name]) => (
                <li
                  key={id}
                  className="inline-flex items-center gap-1 rounded-md border bg-muted/60 px-2 py-0.5 text-xs font-medium min-w-0 max-w-full"
                >
                  <span className="break-words min-w-0">{name || id}</span>
                  <button
                    type="button"
                    aria-label={`Remove ${name || id}`}
                    onClick={() => remove(id)}
                    className="grid min-h-9 min-w-9 shrink-0 place-items-center rounded-sm p-0.5 sm:min-h-0 sm:min-w-0 text-muted-foreground hover:bg-background hover:text-foreground"
                  >
                    <X className="h-3 w-3" />
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </fieldset>
  );
}
