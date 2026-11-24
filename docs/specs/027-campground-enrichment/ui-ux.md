# Destination enrichment UI/UX

## User journey and layout

Keep the current campground and recreation-area routes, heading, provider booking link, campground Monitor action, description, map, and related destinations. Within the current maximum-width content column, place the photo carousel immediately before the description/map card and the “Know before you go” section immediately after that card, below the map. If coordinates are absent, keep this section after the overview. No new route or blocking enrichment request is introduced.

```text
Destination name                  Existing booking / Monitor actions
Photos: [one large photo]                 (only when images exist)
        Previous / Next over image edges
Existing description and map
Know before you go                       (only populated sections)
  Directions / Accessibility / Fees / Stay limit
  Amenities / Activities / Hours / Vehicle limits / Official links
  Source · Updated date
Existing child / related campgrounds
```

Use Embla Carousel's React adapter, the same engine used by shadcn/ui Carousel, with existing shadcn buttons. The carousel shows one photo at a time in a reserved 16:9 frame, with only its caption below the image when supplied. Place 44px Previous/Next buttons over the left/right edges, centered vertically. Show the photo count only inside the full-screen viewer, after the user opens a photo. Never put navigation in a row below the image. ArrowLeft/ArrowRight while focused, mouse dragging, and horizontal touch swipes cycle through the images and wrap at either end. Vertical touch scrolling remains available; dragging does not open the viewer. Hide navigation controls for one photo; do not autoplay and honor reduced-motion preferences. Only the selected slide is exposed to assistive technology or keyboard tabbing. Images are buttons with a visible keyboard-focus outline and an accessible name describing the destination and photo number. Lazy-load remote images with no-referrer policy and reserve space to avoid layout shifts.

## Photo dialog

Clicking or keyboard-activating the current photo opens the existing accessible Dialog, containing an uncropped, object-contain image, photo count, caption when available, and the same overlaid Previous/Next controls. Neither view displays a credit line or a “Photo source” link below images. The dialog has an accessible title. ArrowLeft/ArrowRight change photos while the dialog is open; controls wrap at the endpoints and update the carousel selection. Escape closes it, focus is trapped while open and restored to the selected photo on close so it never lands on a hidden slide. Hide navigation controls for a single image. Controls work by keyboard and touch without requiring swipe gestures.

Render source captions faithfully. When absent, use destination name and image number for alternative text rather than inventing scene descriptions. Never synthesize photographer credit. Photos belong only to the entity supplying the details: no automatic parent-photo fallback on campground pages.

## Know before you go

Use current Card typography, spacing, colors, and themes. Narrative fields use the existing sanitized CollapsibleDescription component; lists use semantic headings/lists. Hours and vehicle limits retain source labels and units. Label distance-qualified amenities as nearby rather than implying they are within the campground. Official links open in a new tab with safe protocols and `noopener noreferrer`. Keep source and last-successful-refresh information with populated details, including photo-less details.

## State behavior

| State                           | Visible behavior                                                                               |
| ------------------------------- | ---------------------------------------------------------------------------------------------- |
| Existing detail query loading   | Existing page skeleton; no additional loading dependency                                       |
| No snapshot                     | Existing destination page, with no empty gallery or placeholder photo                          |
| Empty photos, useful details    | Practical information and provenance remain visible                                            |
| One photo fails                 | Remove it from the carousel/navigation; preserve other content                                 |
| All photos fail                 | Omit gallery; keep practical information and existing page                                     |
| Refresh fails / old cached data | Keep the cached content and truthful successful-refresh date; no spinner or raw upstream error |
| Optional section absent         | Omit its heading and container                                                                 |

Verify desktop/mobile and light/dark rendering, keyboard dialog controls and focus return, sanitizer/link behavior, caption-only presentation, and one/all broken-image states with synthetic fixtures. Existing map, booking, and monitoring actions remain reachable without any image loading successfully.
