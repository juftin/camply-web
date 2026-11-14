# Destination enrichment UI/UX

## User journey and layout

Keep the current campground and recreation-area routes, heading, provider booking link, campground Monitor action, description, map, and related destinations. Within the current maximum-width content column, place the photo gallery immediately before the description/map card and practical information immediately after the gallery. No new route or blocking enrichment request is introduced.

```text
Destination name                  Existing booking / Monitor actions
Photos: [photo] [photo] [photo] [photo]     (only when images exist)
Practical information                     (only populated sections)
  Directions / Accessibility / Fees / Stay limit
  Amenities / Activities / Hours / Vehicle limits / Official links
  Source · Updated date
Existing description and map
Existing child / related campgrounds
```

The gallery has two columns below the existing `sm` breakpoint (640px) and up to four above it, with a 4:3 thumbnail aspect ratio and at most 12 images. A single image occupies a restrained full-width frame. Images are buttons with a visible keyboard-focus outline and an accessible name describing the destination and photo number. Lazy-load remote images with no-referrer policy and reserve space to avoid layout shifts.

## Photo dialog

Clicking or keyboard-activating a thumbnail opens the existing accessible Dialog, containing an uncropped, object-contain image, photo count, caption, credit, source link when available, and explicit Previous/Next controls. The dialog has an accessible title. ArrowLeft/ArrowRight change photos while the dialog is open; controls wrap at the endpoints. Escape closes it, focus is trapped while open and restored to the trigger on close. Hide navigation controls for a single image. Controls work by keyboard and touch without requiring swipe gestures.

Render source captions faithfully. When absent, use destination name and image number for alternative text rather than inventing scene descriptions. Never synthesize photographer credit. Photos belong only to the entity supplying the details: no automatic parent-photo fallback on campground pages.

## Practical information

Use current Card typography, spacing, colors, and themes. Narrative fields use the existing sanitized CollapsibleDescription component; lists use semantic headings/lists. Hours and vehicle limits retain source labels and units. Label distance-qualified amenities as nearby rather than implying they are within the campground. Official links open in a new tab with safe protocols and `noopener noreferrer`. Keep source and last-successful-refresh information with populated details, including photo-less details.

## State behavior

| State                           | Visible behavior                                                                               |
| ------------------------------- | ---------------------------------------------------------------------------------------------- |
| Existing detail query loading   | Existing page skeleton; no additional loading dependency                                       |
| No snapshot                     | Existing destination page, with no empty gallery or placeholder photo                          |
| Empty photos, useful details    | Practical information and provenance remain visible                                            |
| One photo fails                 | Remove it from thumbnails/navigation; preserve other content                                   |
| All photos fail                 | Omit gallery; keep practical information and existing page                                     |
| Refresh fails / old cached data | Keep the cached content and truthful successful-refresh date; no spinner or raw upstream error |
| Optional section absent         | Omit its heading and container                                                                 |

Verify desktop/mobile and light/dark rendering, keyboard dialog controls and focus return, sanitizer/link behavior, source credits, and one/all broken-image states with synthetic fixtures. Existing map, booking, and monitoring actions remain reachable without any image loading successfully.
