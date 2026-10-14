import { useEffect, useMemo, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { MapComponent } from "./MapComponent";
import { ScanForm } from "./ScanForm";
import { Button } from "./ui/button";
import {
  useMapFeatures,
  useMapMembers,
  useMapSummary,
} from "@/hooks/useSearch";
import { mapQueryParams, type SearchExploreParams } from "@/lib/api";
import {
  detailUrl,
  toCampground,
  type GeoBounds,
  type MapCamera,
  type MapPin,
} from "@/lib/maps";
import type { SearchMapGroup, MapSearchResult } from "@/lib/structs";
import { toTitleCase } from "@/lib/utils";

export interface SavedMapView {
  context: string;
  camera: MapCamera;
  bounds: GeoBounds;
}
type Selection =
  | { kind: "location"; item: MapSearchResult }
  | { kind: "group"; group: SearchMapGroup; bounds: GeoBounds };
interface Props {
  params: SearchExploreParams;
  saved: SavedMapView | null;
  onSave: (view: SavedMapView) => void;
}

export const ExploreMap = ({ params, saved, onSave }: Props) => {
  const context = JSON.stringify(mapQueryParams(params));
  const restored = useRef(saved?.context === context ? saved : null);
  const summary = useMapSummary(params);
  const [viewport, setViewport] = useState<{
    bounds: GeoBounds;
    zoom: number;
  } | null>(
    restored.current
      ? {
          bounds: restored.current.bounds,
          zoom: Math.round(restored.current.camera.zoom),
        }
      : null,
  );
  const features = useMapFeatures(params, viewport);
  const [selected, setSelected] = useState<Selection | null>(null);
  const [showMembers, setShowMembers] = useState(false);
  const [groupFit, setGroupFit] = useState<{
    bounds: GeoBounds;
    key: string;
  } | null>(null);
  const members = useMapMembers(
    params,
    selected?.kind === "group" && showMembers
      ? { bounds: selected.bounds, cellId: selected.group.cell_id }
      : null,
  );
  const panel = useRef<HTMLDivElement>(null);
  const returnFocus = useRef<HTMLElement | null>(null);
  const timer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  useEffect(() => () => clearTimeout(timer.current), []);
  useEffect(() => {
    if (selected) panel.current?.focus();
  }, [selected]);
  const select = (selection: Selection) => {
    returnFocus.current =
      document.activeElement instanceof HTMLElement
        ? document.activeElement
        : null;
    setSelected(selection);
    setShowMembers(false);
  };
  const close = () => {
    setSelected(null);
    setShowMembers(false);
    returnFocus.current?.focus();
  };
  const refresh = () => {
    close();
    void summary.refetch();
    void features.refetch();
  };
  const pins: MapPin[] = useMemo(
    () =>
      (features.data?.features ?? []).map((feature) =>
        feature.kind === "location"
          ? {
              id: feature.item.id,
              lat: feature.item.latitude!,
              lng: feature.item.longitude!,
              label: toTitleCase(
                feature.item.campground_name ||
                  feature.item.recreation_area_name ||
                  "Place",
              ),
              type:
                feature.item.entity_type === "Campground"
                  ? "campground"
                  : "recreation-area",
              onSelect: () => select({ kind: "location", item: feature.item }),
            }
          : {
              id: feature.cell_id,
              lat: feature.latitude,
              lng: feature.longitude,
              label: `${feature.count} places`,
              count: feature.count,
              onSelect: () =>
                select({
                  kind: "group",
                  group: feature,
                  bounds: features.data!.viewport,
                }),
            },
      ),
    [features.data],
  );
  const placeSummary = (item: MapSearchResult) => (
    <div className="space-y-2">
      <h3 className="font-semibold">
        {toTitleCase(
          item.campground_name || item.recreation_area_name || "Place",
        )}
      </h3>
      <p className="text-sm text-muted-foreground">
        {item.provider_name} ·{" "}
        {item.entity_type === "Campground" ? "Campground" : "Recreation Area"}
        {[item.city, item.state, item.country].filter(Boolean).length
          ? ` · ${[item.city, item.state, item.country].filter(Boolean).join(", ")}`
          : ""}
      </p>
      <div className="flex gap-2">
        <Button size="sm" variant="outline" asChild>
          <Link to={detailUrl(item)}>Details</Link>
        </Button>
        {item.entity_type === "Campground" && item.campground_id && (
          <ScanForm
            preselectedCampground={toCampground(item)}
            preselectedProviderId={item.provider_id}
            trigger={<Button size="sm">Monitor</Button>}
          />
        )}
      </div>
    </div>
  );

  if (summary.isError)
    return (
      <div role="alert" className="rounded border p-4">
        Map summary could not load. List results remain available.{" "}
        <Button variant="outline" onClick={() => void summary.refetch()}>
          Retry map summary
        </Button>
      </div>
    );
  if (summary.isPending) return <p role="status">Loading map summary…</p>;
  if (summary.data?.total === 0)
    return <p role="status">No places match your search.</p>;
  return (
    <section aria-label="Explore map" className="space-y-3 min-w-0">
      {!!summary.data?.unmappable_total && (
        <p className="text-sm text-muted-foreground">
          {summary.data.unmappable_total} matching{" "}
          {summary.data.unmappable_total === 1 ? "place" : "places"} cannot be
          mapped;{" "}
          {summary.data.unmappable_total === 1 ? "it remains" : "they remain"}{" "}
          in the list.
        </p>
      )}
      {summary.data?.mappable_total === 0 ? (
        <p role="status">
          No mappable locations match. Use the list to browse these places.
        </p>
      ) : (
        <MapComponent
          pins={pins}
          bounds={groupFit?.bounds ?? summary.data?.bounds ?? null}
          fitKey={groupFit?.key ?? context}
          fitMaxZoom={groupFit ? 19 : 12}
          camera={restored.current?.camera}
          className="h-[55vh] lg:h-[65vh] rounded-lg border"
          onMove={(bounds, camera) => {
            onSave({ context, bounds, camera });
            clearTimeout(timer.current);
            timer.current = setTimeout(() => {
              setViewport({
                bounds,
                zoom: Math.max(0, Math.min(19, Math.round(camera.zoom))),
              });
            }, 150);
          }}
        />
      )}
      {features.isFetching && (
        <p role="status" className="text-sm text-muted-foreground">
          Updating map locations…
        </p>
      )}
      {features.isError && (
        <div role="alert">
          Map locations could not load.{" "}
          <Button
            variant="outline"
            size="sm"
            onClick={() => void features.refetch()}
          >
            Retry map locations
          </Button>
        </div>
      )}
      {selected && (
        <div
          ref={panel}
          tabIndex={-1}
          aria-label="Selected map location"
          className="rounded-lg border bg-card p-4 space-y-3 focus-visible:outline focus-visible:outline-2"
        >
          <Button variant="ghost" size="sm" onClick={close}>
            Close selection
          </Button>
          {selected.kind === "location" ? (
            placeSummary(selected.item)
          ) : (
            <>
              <h3 className="font-semibold">
                {selected.group.count} places in this group
              </h3>
              <div className="flex gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => {
                    const b = selected.group.bounds;
                    if (
                      (b.west === b.east && b.south === b.north) ||
                      (viewport?.zoom ?? 0) >= 19
                    )
                      setShowMembers(true);
                    else setGroupFit({ bounds: b, key: `group-${Date.now()}` });
                  }}
                >
                  Zoom in
                </Button>
                <Button size="sm" onClick={() => setShowMembers(true)}>
                  View places
                </Button>
              </div>
              {showMembers && (
                <>
                  {members.isPending && (
                    <p role="status">Loading group members…</p>
                  )}
                  {members.isError && (
                    <div role="alert">
                      Group members could not load.{" "}
                      <Button
                        variant="outline"
                        onClick={() => void members.refetch()}
                      >
                        Retry group members
                      </Button>
                    </div>
                  )}
                  {members.data &&
                    members.data.pages[0].total !== selected.group.count && (
                      <div role="status">
                        Catalog locations changed.{" "}
                        <Button variant="outline" onClick={refresh}>
                          Refresh map
                        </Button>
                      </div>
                    )}
                  <ul className="max-h-80 overflow-y-auto space-y-4">
                    {members.data?.pages
                      .flatMap((page) => page.items)
                      .map((item) => (
                        <li key={item.id} className="border-t pt-3">
                          {placeSummary(item)}
                        </li>
                      ))}
                  </ul>
                  {members.hasNextPage && (
                    <Button
                      variant="outline"
                      disabled={members.isFetchingNextPage}
                      onClick={() => void members.fetchNextPage()}
                    >
                      {members.isFetchingNextPage ? "Loading…" : "Load more"}
                    </Button>
                  )}
                </>
              )}
            </>
          )}
        </div>
      )}
    </section>
  );
};
