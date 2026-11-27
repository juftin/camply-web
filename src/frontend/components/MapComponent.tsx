import {
  Component,
  Fragment,
  type ReactNode,
  useEffect,
  useId,
  useMemo,
  useRef,
  useState,
} from "react";
import {
  Map as LibreMap,
  Marker,
  Popup,
  NavigationControl,
  type MapEventType,
  type StyleSpecification,
  setWorkerUrl,
} from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import workerUrl from "maplibre-gl/dist/maplibre-gl-worker.mjs?worker&url";
import { Info } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  basemapConfig,
  displayLatitude,
  fitLocations,
  initialMapAttributions,
  isOpenFreeMapStyleUrl,
  nearestLongitude,
  parseMapAttributions,
  viewportBounds,
  type GeoBounds,
  type MapAttributionItem,
  type MapCamera,
  type MapPin,
} from "@/lib/maps";

setWorkerUrl(workerUrl);

interface MapLocation {
  lat: number;
  lng: number;
  label?: string;
  type?: "recreation-area" | "campground";
  id?: string;
}
interface MapComponentProps {
  latitude?: number;
  longitude?: number;
  label?: string;
  primaryType?: MapLocation["type"];
  additionalLocations?: MapLocation[];
  zoom?: number;
  className?: string;
  pins?: MapPin[];
  bounds?: GeoBounds | null;
  fitKey?: string;
  fitMaxZoom?: number;
  camera?: MapCamera | null;
  onMove?: (bounds: GeoBounds, camera: MapCamera, initial?: boolean) => void;
}

const MapCanvas = ({
  latitude,
  longitude,
  label,
  primaryType = "recreation-area",
  additionalLocations = [],
  zoom = 12,
  className = "h-64 rounded-lg border",
  pins,
  bounds,
  fitKey,
  fitMaxZoom = 12,
  camera,
  onMove,
}: MapComponentProps) => {
  const tooltipId = useId();
  const attributionId = useId();
  const container = useRef<HTMLDivElement>(null);
  const attributionRef = useRef<HTMLDivElement>(null);
  const attributionButtonRef = useRef<HTMLButtonElement>(null);
  const movement = useRef(onMove);
  movement.current = onMove;
  const initial = useRef(camera);
  const [map, setMap] = useState<LibreMap | null>(null);
  const [error, setError] = useState("");
  const [tileError, setTileError] = useState(false);
  const [ready, setReady] = useState(false);
  const [idle, setIdle] = useState(false);
  const [attributions, setAttributions] = useState<MapAttributionItem[]>([]);
  const [attributionOpen, setAttributionOpen] = useState(false);
  const [attempt, setAttempt] = useState(0);
  const failedSources = useRef<Set<string>>(new Set());
  const lastFit = useRef<string | null>(null);
  const locations = useMemo<MapPin[]>(
    () =>
      pins ?? [
        ...(latitude !== undefined && longitude !== undefined
          ? [
              {
                id: "primary",
                lat: latitude,
                lng: longitude,
                label: label || "Location",
                type: primaryType,
              },
            ]
          : []),
        ...additionalLocations.map((p, i) => ({
          ...p,
          id: p.id ?? `related-${i}`,
          label: p.label || "Campground",
        })),
      ],
    [pins, latitude, longitude, label, primaryType, additionalLocations],
  );
  const locationsKey = JSON.stringify(
    locations.map((p) => [p.id, p.lat, p.lng]),
  );
  const target = bounds === undefined ? fitLocations(locations) : bounds;
  const key = fitKey ?? locationsKey;
  const initialFitKey = useRef(key);

  useEffect(() => {
    if (!container.current) return;
    const trackedFailedSources = failedSources.current;
    let instance: LibreMap | undefined;
    try {
      const config = basemapConfig();
      const baseAttributions = initialMapAttributions(config);
      const isOpenFreeMap =
        config.kind === "style" && isOpenFreeMapStyleUrl(config.styleUrl);
      trackedFailedSources.clear();
      setReady(false);
      setIdle(false);
      setAttributions(baseAttributions);
      setAttributionOpen(false);
      let style: string | StyleSpecification;
      if (config.kind === "style") {
        style = config.styleUrl;
      } else {
        style = {
          version: 8,
          sources: {
            basemap: {
              type: "raster",
              tiles: [config.url],
              tileSize: 256,
              minzoom: 0,
              maxzoom: config.maxNativeZoom,
            },
          },
          layers: [
            {
              id: "basemap",
              type: "raster",
              source: "basemap",
              paint: { "raster-fade-duration": 0 },
            },
          ],
        };
      }
      instance = new LibreMap({
        container: container.current,
        center: initial.current
          ? [initial.current.lng, initial.current.lat]
          : [0, 20],
        zoom: initial.current?.zoom ?? 2,
        minZoom: 0,
        maxZoom: 19,
        maxPitch: 0,
        dragRotate: false,
        renderWorldCopies: true,
        attributionControl: false,
        fadeDuration: 0,
        style,
        transformRequest: (url) => ({
          url,
          credentials: "same-origin",
          referrerPolicy: "strict-origin",
        }),
      });
      instance.touchZoomRotate.disableRotation();
      instance.addControl(
        new NavigationControl({ showCompass: false }),
        "top-left",
      );
      const syncAttributions = () => {
        if (!instance || config.kind !== "style") return;
        const loadedStyle =
          typeof instance.getStyle === "function"
            ? instance.getStyle()
            : undefined;
        if (!loadedStyle?.sources) return;
        const raw: string[] = [];
        for (const [sourceId, sourceSpec] of Object.entries(
          loadedStyle.sources,
        )) {
          const runtimeSource =
            typeof instance.getSource === "function"
              ? instance.getSource(sourceId)
              : undefined;
          const attribution =
            runtimeSource?.attribution ??
            ("attribution" in sourceSpec &&
            typeof sourceSpec.attribution === "string"
              ? sourceSpec.attribution
              : undefined);
          if (attribution) raw.push(attribution);
        }
        const parsed = parseMapAttributions(raw, {
          stripOptionalOpenFreeMap: isOpenFreeMap,
        });
        if (parsed.length > 0 || !isOpenFreeMap) {
          setAttributions((previous) =>
            previous.length === parsed.length &&
            previous.every(
              (item, index) =>
                item.text === parsed[index].text &&
                item.href === parsed[index].href,
            )
              ? previous
              : parsed,
          );
        }
      };
      const onSourceData = (event: MapEventType["sourcedata"]) => {
        if (
          event.sourceDataType === "metadata" ||
          event.sourceDataType === "visibility"
        )
          syncAttributions();
      };
      const emit = (event?: MapEventType["moveend"]) => {
        if (!instance || lastFit.current === null) return;
        const b = instance.getBounds(),
          c = instance.getCenter();
        if (!b) return;
        const camera = { lat: c.lat, lng: c.lng, zoom: instance.getZoom() };
        const initialMovement =
          !event?.originalEvent &&
          (!initial.current ||
            (camera.lat === initial.current.lat &&
              camera.lng === initial.current.lng &&
              camera.zoom === initial.current.zoom &&
              lastFit.current === initialFitKey.current));
        initial.current = camera;
        initialFitKey.current = lastFit.current;
        movement.current?.(
          viewportBounds(b.getWest(), b.getSouth(), b.getEast(), b.getNorth()),
          camera,
          initialMovement,
        );
      };
      const failure = (event: MapEventType["error"]) => {
        if (
          "sourceId" in event &&
          typeof event.sourceId === "string" &&
          event.sourceId.length > 0
        ) {
          trackedFailedSources.add(event.sourceId);
          setTileError(true);
        } else {
          setError(event.error?.message || "Map could not load.");
        }
      };
      const loaded = () => {
        setReady(true);
        syncAttributions();
      };
      const markBusy = () => setIdle(false);
      const markIdle = () => setIdle(true);
      const contextLost = () =>
        setError("The map graphics context was lost. Please retry the map.");
      instance.on("load", loaded);
      instance.on("styledata", syncAttributions);
      instance.on("sourcedata", onSourceData);
      instance.on("movestart", markBusy);
      instance.on("dataloading", markBusy);
      instance.on("idle", markIdle);
      instance.on("webglcontextlost", contextLost);
      instance.on("move", emit);
      instance.on("moveend", emit);
      instance.on("error", failure);
      const observer = new ResizeObserver(() => instance?.resize());
      observer.observe(container.current);
      lastFit.current = initial.current ? initialFitKey.current : null;
      setMap(instance);
      if (initial.current) emit();
      setError("");
      setTileError(false);
      return () => {
        trackedFailedSources.clear();
        observer.disconnect();
        instance?.off("load", loaded);
        instance?.off("styledata", syncAttributions);
        instance?.off("sourcedata", onSourceData);
        instance?.off("movestart", markBusy);
        instance?.off("dataloading", markBusy);
        instance?.off("idle", markIdle);
        instance?.off("webglcontextlost", contextLost);
        instance?.off("move", emit);
        instance?.off("moveend", emit);
        instance?.off("error", failure);
        instance?.remove();
        instance = undefined;
      };
    } catch (failure) {
      instance?.remove();
      instance = undefined;
      setAttributions([]);
      setAttributionOpen(false);
      setError(
        failure instanceof Error
          ? failure.message
          : "Map could not initialize.",
      );
    }
    // The map owns one instance; changing locations updates its layers below.
  }, [attempt]);

  useEffect(() => {
    if (!map) return;
    const markers: {
      marker: Marker;
      lat: number;
      lng: number;
      dispose: () => void;
    }[] = [];
    for (const pin of locations) {
      if (
        !Number.isFinite(pin.lat) ||
        !Number.isFinite(pin.lng) ||
        Math.abs(pin.lat) > 90 ||
        Math.abs(pin.lng) > 180
      )
        continue;
      const element: HTMLElement = document.createElement(
        pin.onSelect ? "button" : "div",
      );
      element.className = "camply-map-marker";
      element.setAttribute("aria-label", pin.label);
      if (element instanceof HTMLButtonElement) element.type = "button";
      else {
        element.setAttribute("role", "img");
        element.tabIndex = 0;
      }
      const icon = document.createElement("span");
      icon.className = `camply-map-pin ${pin.count ? "camply-map-group" : pin.type === "campground" ? "camply-map-camp" : "camply-map-area"}`;
      icon.textContent = pin.count
        ? String(pin.count)
        : pin.type === "campground"
          ? "⛺"
          : "▲";
      icon.setAttribute("aria-hidden", "true");
      element.appendChild(icon);
      const content = document.createElement("div");
      content.setAttribute("role", "tooltip");
      content.id = `${tooltipId}-${markers.length}`;
      const name = document.createElement("strong");
      name.textContent = pin.label;
      content.appendChild(name);
      if (pin.description) {
        const details = document.createElement("p");
        details.textContent = pin.description;
        content.appendChild(details);
      }
      const popup = new Popup({
        closeButton: false,
        closeOnClick: false,
        focusAfterOpen: false,
        offset: 22,
        maxWidth: "min(240px, calc(50vw - 40px))",
        className: "camply-map-tooltip",
      }).setDOMContent(content);
      let hovered = false;
      let focused = false;
      const hidePopup = () => {
        popup.remove();
        element.removeAttribute("aria-describedby");
      };
      const showPopup = () => {
        element.setAttribute("aria-describedby", content.id);
        popup
          .setLngLat([
            nearestLongitude(pin.lng, map.getCenter().lng),
            displayLatitude(pin.lat),
          ])
          .addTo(map);
      };
      const enter = () => {
        hovered = true;
        showPopup();
      };
      const leave = () => {
        hovered = false;
        if (!focused) hidePopup();
      };
      const focus = () => {
        focused = true;
        showPopup();
      };
      const blur = () => {
        focused = false;
        if (!hovered) hidePopup();
      };
      const dismiss = (event: KeyboardEvent) => {
        if (event.key === "Escape") hidePopup();
      };
      element.addEventListener("mouseenter", enter);
      element.addEventListener("mouseleave", leave);
      element.addEventListener("focus", focus);
      element.addEventListener("blur", blur);
      element.addEventListener("keydown", dismiss);
      const activate = (event: MouseEvent) => {
        event.stopPropagation();
        pin.onSelect?.();
      };
      const keyboard = (event: KeyboardEvent) => {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          event.stopPropagation();
          pin.onSelect?.();
        }
      };
      if (pin.onSelect) {
        element.addEventListener("click", activate);
        element.addEventListener("keydown", keyboard);
      }
      const marker = new Marker({ element, anchor: "center" })
        .setLngLat([
          nearestLongitude(pin.lng, map.getCenter().lng),
          displayLatitude(pin.lat),
        ])
        .addTo(map);
      markers.push({
        marker,
        lat: pin.lat,
        lng: pin.lng,
        dispose: () => {
          element.removeEventListener("click", activate);
          element.removeEventListener("keydown", keyboard);
          element.removeEventListener("mouseenter", enter);
          element.removeEventListener("mouseleave", leave);
          element.removeEventListener("focus", focus);
          element.removeEventListener("blur", blur);
          element.removeEventListener("keydown", dismiss);
          hidePopup();
          marker.remove();
        },
      });
    }
    const reposition = () => {
      for (const { marker, lat, lng } of markers)
        marker.setLngLat([
          nearestLongitude(lng, map.getCenter().lng),
          displayLatitude(lat),
        ]);
    };
    map.on("moveend", reposition);
    return () => {
      map.off("moveend", reposition);
      markers.forEach(({ dispose }) => dispose());
    };
  }, [map, locations, tooltipId]);

  useEffect(() => {
    if (!map || !target || lastFit.current === key) return;
    lastFit.current = key;
    const east = target.east < target.west ? target.east + 360 : target.east;
    if (target.west === target.east && target.south === target.north)
      map.jumpTo({
        center: [target.west, displayLatitude(target.south)],
        zoom,
      });
    else
      map.fitBounds(
        [
          [target.west, displayLatitude(target.south)],
          [east, displayLatitude(target.north)],
        ],
        { padding: 28, maxZoom: fitMaxZoom, animate: false },
      );
  }, [map, target, key, zoom, fitMaxZoom]);

  useEffect(() => {
    if (!attributionOpen) return;
    const onPointerDown = (event: MouseEvent) => {
      if (
        attributionRef.current &&
        !attributionRef.current.contains(event.target as Node)
      )
        setAttributionOpen(false);
    };
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key !== "Escape") return;
      const focusInside = attributionRef.current?.contains(
        document.activeElement,
      );
      setAttributionOpen(false);
      if (focusInside) attributionButtonRef.current?.focus();
    };
    document.addEventListener("mousedown", onPointerDown);
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("mousedown", onPointerDown);
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [attributionOpen]);

  return (
    <div className="space-y-2">
      {!ready && !error && !tileError && <p role="status">Loading map…</p>}
      {error && (
        <div role="alert" className="rounded border p-3 text-sm">
          {error}{" "}
          <Button
            variant="outline"
            size="sm"
            onClick={() => {
              failedSources.current.clear();
              setMap(null);
              setAttempt((n) => n + 1);
            }}
          >
            Retry map
          </Button>
        </div>
      )}
      {tileError && (
        <div role="status" className="rounded border p-3 text-sm">
          Basemap tiles could not load. Locations and list results remain
          available.{" "}
          <Button
            variant="outline"
            size="sm"
            onClick={() => {
              setTileError(false);
              for (const sourceId of failedSources.current)
                map?.refreshTiles(sourceId);
              failedSources.current.clear();
            }}
          >
            Retry tiles
          </Button>
        </div>
      )}
      <div className="relative">
        <div
          ref={container}
          aria-label="Interactive campground map"
          data-map-idle={idle ? "true" : "false"}
          className={`camply-map relative z-0 ${className}`}
        />
        {!error && attributions.length > 0 && (
          <div
            ref={attributionRef}
            className="absolute bottom-2 right-2 z-10 flex flex-col items-end"
          >
            {attributionOpen && (
              <div
                id={attributionId}
                role="region"
                aria-label="Map attribution details"
                className="mb-1.5 flex w-max max-w-[min(18rem,calc(100vw-3rem))] flex-wrap items-center justify-end gap-x-1.5 gap-y-0.5 rounded-md border bg-popover px-2.5 py-1.5 text-xs text-popover-foreground shadow-md"
              >
                {attributions.map((item, index) => (
                  <Fragment key={`${item.href ?? ""}|${item.text}`}>
                    {index > 0 && (
                      <span
                        aria-hidden="true"
                        className="text-muted-foreground"
                      >
                        ·
                      </span>
                    )}
                    {item.href ? (
                      <a
                        href={item.href}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="hover:underline underline-offset-2"
                      >
                        {item.text}
                      </a>
                    ) : (
                      <span>{item.text}</span>
                    )}
                  </Fragment>
                ))}
              </div>
            )}
            <button
              ref={attributionButtonRef}
              type="button"
              aria-label="Map attribution"
              aria-expanded={attributionOpen}
              aria-controls={attributionId}
              title="Map attribution"
              onClick={() => setAttributionOpen((open) => !open)}
              className="inline-flex h-6 w-6 items-center justify-center rounded-full border bg-background/90 text-muted-foreground shadow-sm backdrop-blur-sm transition-colors hover:bg-background hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            >
              <Info className="h-3.5 w-3.5" aria-hidden="true" />
            </button>
          </div>
        )}
      </div>
    </div>
  );
};

class MapBoundary extends Component<
  { children: ReactNode },
  { failed: boolean }
> {
  state = { failed: false };
  static getDerivedStateFromError() {
    return { failed: true };
  }
  render() {
    return this.state.failed ? (
      <div role="alert">
        Map could not render.{" "}
        <Button onClick={() => this.setState({ failed: false })}>
          Retry map
        </Button>
      </div>
    ) : (
      this.props.children
    );
  }
}
export const MapComponent = (props: MapComponentProps) => (
  <MapBoundary>
    <MapCanvas {...props} />
  </MapBoundary>
);
