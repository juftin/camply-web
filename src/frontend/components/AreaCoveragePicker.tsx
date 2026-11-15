import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { getMonitoringCampgrounds } from "@/lib/api";
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
  const remove = (id: string) => {
    const next = { ...selected };
    delete next[id];
    onSelectedChange(next);
  };
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
        {choices.data?.eligible_total ?? "…"} eligible campgrounds. All coverage
        automatically includes future eligible campgrounds.
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
        <>
          <p role="status" aria-live="polite">
            {Object.keys(selected).length} selected
          </p>
          <ul className="space-y-1">
            {Object.entries(selected).map(([id, name]) => (
              <li key={id} className="flex items-center gap-2 min-w-0">
                <span className="break-words min-w-0">{name || id}</span>
                <Button
                  type="button"
                  size="sm"
                  variant="ghost"
                  aria-label={`Remove ${name || id}`}
                  onClick={() => remove(id)}
                >
                  Remove
                </Button>
              </li>
            ))}
          </ul>
          <Input
            type="search"
            aria-label="Search area campgrounds"
            value={query}
            onChange={(event) => {
              setQuery(event.target.value);
              setOffset(0);
            }}
          />
          {choices.isPending && <p aria-live="polite">Loading campgrounds…</p>}
          {choices.isError && (
            <p role="alert">
              Campgrounds could not load.{" "}
              <Button
                type="button"
                variant="outline"
                onClick={() => void choices.refetch()}
              >
                Retry choices
              </Button>
            </p>
          )}
          {choices.data?.items.map((item) => (
            <label key={item.id} className="flex items-start gap-2 break-words">
              <input
                type="checkbox"
                checked={item.id in selected}
                onChange={(event) =>
                  event.target.checked
                    ? onSelectedChange({ ...selected, [item.id]: item.name })
                    : remove(item.id)
                }
              />
              {item.name}
            </label>
          ))}
          {choices.data && !choices.data.items.length && (
            <p>
              {choices.data.eligible_total
                ? "No campgrounds match this search."
                : "No eligible campgrounds. Saved unavailable choices remain selected until removed."}
            </p>
          )}
          <div className="flex gap-2">
            <Button
              type="button"
              variant="outline"
              disabled={!offset}
              onClick={() => setOffset((value) => Math.max(0, value - 50))}
            >
              Previous campgrounds
            </Button>
            <Button
              type="button"
              variant="outline"
              disabled={!choices.data?.has_more}
              onClick={() => setOffset((value) => value + 50)}
            >
              Next campgrounds
            </Button>
          </div>
        </>
      )}
    </fieldset>
  );
}
