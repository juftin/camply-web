import {
  Component,
  type ReactNode,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import {
  Map as LibreMap,
  Marker,
  NavigationControl,
  AttributionControl,
  type MapEventType,
  setWorkerUrl,
} from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import workerUrl from "maplibre-gl/dist/maplibre-gl-worker.mjs?worker&url";
import { Button } from "@/components/ui/button";
import {
  basemapConfig,
  displayLatitude,
  fitLocations,
  nearestLongitude,
  viewportBounds,
  type GeoBounds,
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
  onMove?: (bounds: GeoBounds, camera: MapCamera) => void;
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
  const container = useRef<HTMLDivElement>(null);
  const movement = useRef(onMove);
  movement.current = onMove;
  const initial = useRef(camera);
  const [map, setMap] = useState<LibreMap | null>(null);
  const [error, setError] = useState("");
  const [tileError, setTileError] = useState(false);
  const [ready, setReady] = useState(false);
  const [attempt, setAttempt] = useState(0);
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
    let instance: LibreMap | undefined;
    try {
      const config = basemapConfig();
      setReady(false);
      const credit = document.createElement("a");
      credit.href = config.link;
      credit.textContent = config.text;
      credit.target = "_blank";
      credit.rel = "noopener noreferrer";
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
        style: {
          version: 8,
          sources: {
            basemap: {
              type: "raster",
              tiles: [config.url],
              tileSize: 256,
              minzoom: 0,
              maxzoom: config.maxNativeZoom,
              attribution: credit.outerHTML,
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
        },
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
      instance.addControl(
        new AttributionControl({ compact: false }),
        "bottom-right",
      );
      const emit = () => {
        if (!instance || lastFit.current === null) return;
        const b = instance.getBounds(),
          c = instance.getCenter();
        if (!b) return;
        const camera = { lat: c.lat, lng: c.lng, zoom: instance.getZoom() };
        initial.current = camera;
        initialFitKey.current = lastFit.current;
        movement.current?.(
          viewportBounds(b.getWest(), b.getSouth(), b.getEast(), b.getNorth()),
          camera,
        );
      };
      const failure = (event: MapEventType["error"]) => {
        if ("sourceId" in event && event.sourceId === "basemap")
          setTileError(true);
        else setError(event.error.message || "Map could not load.");
      };
      const loaded = () => setReady(true);
      const contextLost = () =>
        setError("The map graphics context was lost. Please retry the map.");
      instance.on("load", loaded);
      instance.on("webglcontextlost", contextLost);
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
        observer.disconnect();
        instance?.off("load", loaded);
        instance?.off("webglcontextlost", contextLost);
        instance?.off("moveend", emit);
        instance?.off("error", failure);
        instance?.remove();
        instance = undefined;
      };
    } catch (failure) {
      instance?.remove();
      instance = undefined;
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
      element.title = pin.label;
      element.setAttribute("aria-label", pin.label);
      if (element instanceof HTMLButtonElement) element.type = "button";
      else element.setAttribute("role", "img");
      const icon = document.createElement("span");
      icon.className = `camply-map-pin ${pin.count ? "camply-map-group" : pin.type === "campground" ? "camply-map-camp" : "camply-map-area"}`;
      icon.textContent = pin.count
        ? String(pin.count)
        : pin.type === "campground"
          ? "⛺"
          : "▲";
      icon.setAttribute("aria-hidden", "true");
      element.appendChild(icon);
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
  }, [map, locations]);

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
              map?.refreshTiles("basemap");
            }}
          >
            Retry tiles
          </Button>
        </div>
      )}
      <div
        ref={container}
        aria-label="Interactive campground map"
        className={`camply-map relative z-0 ${className}`}
      />
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
