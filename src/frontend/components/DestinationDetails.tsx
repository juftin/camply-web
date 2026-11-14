import { useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import useEmblaCarousel from "embla-carousel-react";
import { ChevronLeft, ChevronRight, Expand } from "lucide-react";
import type { DestinationDetails as DetailsSnapshot } from "@/lib/structs";
import { sanitizeAndRenderHTML } from "@/lib/utils";
import { CollapsibleDescription } from "@/components/CollapsibleDescription";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

interface DestinationDetailsProps {
  name: string;
  details?: DetailsSnapshot | null;
  children?: ReactNode;
}

function safeUrl(value?: string | null): string | null {
  try {
    const url = new URL(value || "");
    return ["http:", "https:"].includes(url.protocol) &&
      !url.username &&
      !url.password
      ? url.href
      : null;
  } catch {
    return null;
  }
}

function safeNarrative(value: string): string {
  const template = document.createElement("template");
  template.innerHTML = sanitizeAndRenderHTML(value).__html;
  template.content.querySelectorAll("a").forEach((anchor) => {
    const href = safeUrl(anchor.getAttribute("href"));
    if (href) {
      anchor.href = href;
      anchor.target = "_blank";
      anchor.rel = "noopener noreferrer";
    } else {
      anchor.removeAttribute("href");
      anchor.removeAttribute("target");
    }
  });
  return template.innerHTML;
}

export function DestinationDetails({
  name,
  details,
  children,
}: DestinationDetailsProps) {
  if (!details) return <>{children}</>;
  return (
    <DestinationContent
      key={`${name}/${details.source_url}/${details.fetched_at}`}
      name={name}
      details={details}
    >
      {children}
    </DestinationContent>
  );
}

function DestinationContent({
  name,
  details,
  children,
}: {
  name: string;
  details: DetailsSnapshot;
  children?: ReactNode;
}) {
  const [failedPhotos, setFailedPhotos] = useState<string[]>([]);
  const [activeUrl, setActiveUrl] = useState<string | null>(null);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [carouselRef, carouselApi] = useEmblaCarousel({
    loop: true,
    breakpoints: { "(prefers-reduced-motion: reduce)": { duration: 0 } },
  });
  const trigger = useRef<HTMLButtonElement | null>(null);
  const gallery = useRef<HTMLDivElement | null>(null);
  const provenance = useRef<HTMLParagraphElement | null>(null);
  const photos = useMemo(
    () =>
      (details.photos || []).filter(
        (photo) => safeUrl(photo.url) && !failedPhotos.includes(photo.url),
      ),
    [details.photos, failedPhotos],
  );
  useEffect(() => {
    if (!carouselApi) return;
    const selectPhoto = () => {
      setActiveUrl(photos[carouselApi.selectedScrollSnap()]?.url || null);
    };
    carouselApi.on("select", selectPhoto).on("reInit", selectPhoto);
    return () => {
      carouselApi.off("select", selectPhoto).off("reInit", selectPhoto);
    };
  }, [carouselApi, photos]);
  const activeIndex = Math.max(
    0,
    photos.findIndex((photo) => photo.url === activeUrl),
  );
  const activePhoto = photos[activeIndex];
  useEffect(() => {
    if (
      !dialogOpen &&
      gallery.current?.contains(document.activeElement) &&
      document.activeElement?.closest('[aria-hidden="true"]')
    ) {
      gallery.current
        .querySelector<HTMLButtonElement>('button[tabindex="0"]')
        ?.focus({ preventScroll: true });
    }
  }, [activeIndex, dialogOpen]);
  const sourceUrl = safeUrl(details.source_url);
  const date = new Date(details.fetched_at);
  const updated = Number.isNaN(date.getTime())
    ? null
    : date.toLocaleDateString("en-US", {
        month: "short",
        day: "numeric",
        year: "numeric",
        timeZone: "UTC",
      });
  const narratives = [
    ["Directions", details.directions],
    ["Accessibility", details.accessibility],
    ["Fees", details.fee_information],
    ["Stay limit", details.stay_limit],
  ].filter((entry): entry is [string, string] => Boolean(entry[1]?.trim()));
  const lists = [
    { title: "Amenities", items: details.amenities || [] },
    { title: "Activities", items: details.activities || [] },
  ].filter((list) => list.items.length);
  const facts = [
    { title: "Hours and seasons", items: details.hours || [] },
    { title: "Vehicle limits", items: details.vehicle_limits || [] },
  ].filter((list) => list.items.length);
  const links = (details.links || []).filter((link) => safeUrl(link.url));
  const hasPractical =
    narratives.length || lists.length || facts.length || links.length;

  function changePhoto(direction: number) {
    const next = (activeIndex + direction + photos.length) % photos.length;
    setActiveUrl(photos[next].url);
    carouselApi?.scrollTo(next);
  }

  function failPhoto(url: string) {
    const remaining = photos.filter((photo) => photo.url !== url);
    setFailedPhotos((previous) => [...previous, url]);
    if (activeUrl === url) {
      setActiveUrl(
        remaining[Math.min(activeIndex, remaining.length - 1)]?.url || null,
      );
    }
  }

  return (
    <>
      {photos.length > 0 && (
        <Card
          ref={gallery}
          tabIndex={-1}
          className="min-w-0"
          role="region"
          aria-roledescription="carousel"
          aria-label={`${name} photos`}
          onKeyDown={(event) => {
            if (
              photos.length > 1 &&
              (event.key === "ArrowLeft" || event.key === "ArrowRight")
            ) {
              event.preventDefault();
              changePhoto(event.key === "ArrowLeft" ? -1 : 1);
            }
          }}
        >
          <CardHeader>
            <CardTitle>Photos</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <figure className="space-y-3">
              <div className="relative">
                <div ref={carouselRef} className="overflow-hidden rounded-md">
                  <div className="flex touch-pan-y">
                    {photos.map((photo, index) => (
                      <div
                        key={photo.url}
                        className="min-w-0 flex-[0_0_100%]"
                        role="group"
                        aria-roledescription="slide"
                        aria-label={`Photo ${index + 1} of ${photos.length}`}
                        aria-hidden={index !== activeIndex}
                      >
                        <button
                          type="button"
                          tabIndex={index === activeIndex ? 0 : -1}
                          className="relative block aspect-video w-full bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-ring"
                          aria-label={`View ${name} photo ${index + 1}`}
                          title="View full screen"
                          onClick={(event) => {
                            trigger.current = event.currentTarget;
                            setActiveUrl(photo.url);
                            setDialogOpen(true);
                          }}
                        >
                          <img
                            src={photo.url}
                            alt={photo.caption || `${name} photo ${index + 1}`}
                            width={photo.width || undefined}
                            height={photo.height || undefined}
                            loading="lazy"
                            draggable={false}
                            referrerPolicy="no-referrer"
                            className="h-full w-full object-cover"
                            onError={() => failPhoto(photo.url)}
                          />
                          <span
                            aria-hidden="true"
                            className="absolute bottom-3 right-3 rounded-md bg-black/60 p-2 text-white"
                          >
                            <Expand className="h-4 w-4" />
                          </span>
                        </button>
                      </div>
                    ))}
                  </div>
                </div>
                {photos.length > 1 && (
                  <PhotoNavigation
                    onPrevious={() => changePhoto(-1)}
                    onNext={() => changePhoto(1)}
                  />
                )}
              </div>
              <PhotoCaption photo={activePhoto} />
            </figure>
          </CardContent>
        </Card>
      )}

      <Dialog
        open={Boolean(dialogOpen && activePhoto)}
        onOpenChange={(open) => {
          setDialogOpen(open);
        }}
      >
        {activePhoto && (
          <DialogContent
            className="max-h-[95dvh] w-[calc(100%-2rem)] max-w-4xl overflow-y-auto"
            onCloseAutoFocus={(event) => {
              event.preventDefault();
              if (
                trigger.current?.isConnected &&
                !trigger.current.closest('[aria-hidden="true"]')
              )
                trigger.current.focus();
              else if (gallery.current)
                gallery.current
                  .querySelector<HTMLButtonElement>('button[tabindex="0"]')
                  ?.focus();
              else provenance.current?.focus();
            }}
            onKeyDown={(event) => {
              if (event.key === "ArrowLeft" || event.key === "ArrowRight") {
                event.preventDefault();
                changePhoto(event.key === "ArrowLeft" ? -1 : 1);
              }
            }}
          >
            <DialogHeader>
              <DialogTitle>{name} photos</DialogTitle>
              <DialogDescription aria-live="polite">
                Photo {activeIndex + 1} of {photos.length}
              </DialogDescription>
            </DialogHeader>
            <figure className="space-y-3">
              <div className="relative">
                <img
                  src={activePhoto.url}
                  alt={
                    activePhoto.caption || `${name} photo ${activeIndex + 1}`
                  }
                  width={activePhoto.width || undefined}
                  height={activePhoto.height || undefined}
                  referrerPolicy="no-referrer"
                  className="max-h-[60dvh] w-full object-contain"
                  onError={() => failPhoto(activePhoto.url)}
                />
                {photos.length > 1 && (
                  <PhotoNavigation
                    onPrevious={() => changePhoto(-1)}
                    onNext={() => changePhoto(1)}
                  />
                )}
              </div>
              <PhotoCaption photo={activePhoto} />
            </figure>
          </DialogContent>
        )}
      </Dialog>

      {children}

      {hasPractical ? (
        <Card className="min-w-0">
          <CardHeader>
            <CardTitle>Know before you go</CardTitle>
          </CardHeader>
          <CardContent className="space-y-6">
            {narratives.map(([title, value]) => (
              <section key={title} className="space-y-2">
                <h3 className="font-medium">{title}</h3>
                <CollapsibleDescription description={safeNarrative(value)} />
              </section>
            ))}
            {lists.map(({ title, items }) => (
              <section key={title} className="space-y-2">
                <h3 className="font-medium">{title}</h3>
                <ul className="list-inside list-disc space-y-1 text-sm text-muted-foreground">
                  {items.map((item, index) => (
                    <li key={`${index}/${item}`}>{item}</li>
                  ))}
                </ul>
              </section>
            ))}
            {facts.map(({ title, items }) => (
              <section key={title} className="space-y-2">
                <h3 className="font-medium">{title}</h3>
                <dl className="space-y-2 text-sm">
                  {items.map(({ label, value }, index) => (
                    <div
                      key={`${index}/${label}`}
                      className="grid gap-1 sm:grid-cols-2"
                    >
                      <dt>{label}</dt>
                      <dd className="whitespace-pre-line text-muted-foreground">
                        {value}
                      </dd>
                    </div>
                  ))}
                </dl>
              </section>
            ))}
            {links.length > 0 && (
              <section className="space-y-2">
                <h3 className="font-medium">Official links</h3>
                <ul className="space-y-2 text-sm">
                  {links.map(({ label, url }, index) => (
                    <li key={`${index}/${url}`}>
                      <a
                        href={safeUrl(url)!}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-primary underline"
                      >
                        {label}
                      </a>
                    </li>
                  ))}
                </ul>
              </section>
            )}
          </CardContent>
        </Card>
      ) : null}

      {(sourceUrl || updated) && (
        <p
          ref={provenance}
          tabIndex={-1}
          className="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-muted-foreground"
        >
          {sourceUrl && (
            <a
              href={sourceUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="underline"
            >
              Source
            </a>
          )}
          {updated && (
            <time dateTime={details.fetched_at}>Updated {updated} (UTC)</time>
          )}
        </p>
      )}
    </>
  );
}

function PhotoNavigation({
  onPrevious,
  onNext,
}: {
  onPrevious: () => void;
  onNext: () => void;
}) {
  return (
    <>
      <Button
        variant="outline"
        size="icon"
        className="absolute left-3 top-1/2 h-11 w-11 -translate-y-1/2 rounded-full border-white/20 bg-black/60 text-white hover:bg-black/80 hover:text-white"
        aria-label="Previous photo"
        onClick={onPrevious}
      >
        <ChevronLeft className="h-5 w-5" />
      </Button>
      <Button
        variant="outline"
        size="icon"
        className="absolute right-3 top-1/2 h-11 w-11 -translate-y-1/2 rounded-full border-white/20 bg-black/60 text-white hover:bg-black/80 hover:text-white"
        aria-label="Next photo"
        onClick={onNext}
      >
        <ChevronRight className="h-5 w-5" />
      </Button>
    </>
  );
}

function PhotoCaption({
  photo,
}: {
  photo: NonNullable<DetailsSnapshot["photos"]>[number];
}) {
  return photo.caption ? (
    <figcaption className="text-sm">{photo.caption}</figcaption>
  ) : null;
}
