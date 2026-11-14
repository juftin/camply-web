import { useRef, useState } from "react";
import { ChevronLeft, ChevronRight } from "lucide-react";
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

export function DestinationDetails({ name, details }: DestinationDetailsProps) {
  if (!details) return null;
  return (
    <DestinationContent
      key={`${name}/${details.source_url}/${details.fetched_at}`}
      name={name}
      details={details}
    />
  );
}

function DestinationContent({
  name,
  details,
}: {
  name: string;
  details: DetailsSnapshot;
}) {
  const [failedPhotos, setFailedPhotos] = useState<string[]>([]);
  const [activeUrl, setActiveUrl] = useState<string | null>(null);
  const trigger = useRef<HTMLButtonElement | null>(null);
  const gallery = useRef<HTMLDivElement | null>(null);
  const provenance = useRef<HTMLParagraphElement | null>(null);
  const photos = (details.photos || []).filter(
    (photo) => safeUrl(photo.url) && !failedPhotos.includes(photo.url),
  );
  const activeIndex = Math.max(
    0,
    photos.findIndex((photo) => photo.url === activeUrl),
  );
  const activePhoto = photos[activeIndex];
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
        <Card ref={gallery} tabIndex={-1} className="min-w-0">
          <CardHeader>
            <CardTitle>Photos</CardTitle>
          </CardHeader>
          <CardContent>
            <div
              className={
                photos.length === 1
                  ? "max-w-xl"
                  : "grid grid-cols-2 gap-3 sm:grid-cols-4"
              }
            >
              {photos.map((photo, index) => (
                <button
                  key={photo.url}
                  type="button"
                  className="block aspect-[4/3] w-full overflow-hidden rounded-md bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
                  aria-label={`View ${name} photo ${index + 1}`}
                  onClick={(event) => {
                    trigger.current = event.currentTarget;
                    setActiveUrl(photo.url);
                  }}
                >
                  <img
                    src={photo.url}
                    alt={photo.caption || `${name} photo ${index + 1}`}
                    width={photo.width || undefined}
                    height={photo.height || undefined}
                    loading="lazy"
                    referrerPolicy="no-referrer"
                    className="h-full w-full object-cover"
                    onError={() => failPhoto(photo.url)}
                  />
                </button>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      <Dialog
        open={Boolean(activeUrl && activePhoto)}
        onOpenChange={(open) => {
          if (!open) setActiveUrl(null);
        }}
      >
        {activePhoto && (
          <DialogContent
            className="max-h-[95dvh] w-[calc(100%-2rem)] max-w-4xl overflow-y-auto"
            onCloseAutoFocus={(event) => {
              event.preventDefault();
              if (trigger.current?.isConnected) trigger.current.focus();
              else if (gallery.current)
                gallery.current.querySelector("button")?.focus();
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
              <img
                src={activePhoto.url}
                alt={activePhoto.caption || `${name} photo ${activeIndex + 1}`}
                width={activePhoto.width || undefined}
                height={activePhoto.height || undefined}
                referrerPolicy="no-referrer"
                className="max-h-[60dvh] w-full object-contain"
                onError={() => failPhoto(activePhoto.url)}
              />
              <figcaption className="space-y-1 text-sm">
                {activePhoto.caption && <p>{activePhoto.caption}</p>}
                {activePhoto.credit && (
                  <p className="text-muted-foreground">
                    Credit: {activePhoto.credit}
                  </p>
                )}
                {safeUrl(activePhoto.source_url) && (
                  <a
                    href={safeUrl(activePhoto.source_url)!}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-primary underline"
                  >
                    Photo source
                  </a>
                )}
              </figcaption>
            </figure>
            {photos.length > 1 && (
              <div className="flex justify-between gap-3">
                <Button
                  variant="outline"
                  aria-label="Previous photo"
                  onClick={() => changePhoto(-1)}
                >
                  <ChevronLeft className="mr-1 h-4 w-4" />
                  Previous
                </Button>
                <Button
                  variant="outline"
                  aria-label="Next photo"
                  onClick={() => changePhoto(1)}
                >
                  Next
                  <ChevronRight className="ml-1 h-4 w-4" />
                </Button>
              </div>
            )}
          </DialogContent>
        )}
      </Dialog>

      {hasPractical ? (
        <Card className="min-w-0">
          <CardHeader>
            <CardTitle>Practical information</CardTitle>
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
