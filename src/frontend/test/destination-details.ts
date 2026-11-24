import type { DestinationDetails } from "@/lib/structs";

export function destinationDetails(
  overrides: Partial<DestinationDetails> = {},
): Required<DestinationDetails> {
  return {
    source_url: "https://provider.example.test/park",
    fetched_at: "2026-11-14T23:30:00-08:00",
    description: null,
    directions: "<p>Follow the signed road.</p>",
    accessibility: null,
    fee_information: null,
    stay_limit: null,
    photos: [
      {
        url: "https://images.example.test/first.jpg",
        caption: "A synthetic lake view",
        credit: "Synthetic park archive",
        width: 800,
        height: 600,
        is_primary: true,
        source_url: "https://provider.example.test/photos/first",
      },
      {
        url: "https://images.example.test/second.jpg",
        caption: null,
        credit: null,
        is_primary: false,
      },
    ],
    activities: ["Walking"],
    amenities: ["Water", "Boat launch (nearby)"],
    links: [{ label: "Park map", url: "https://provider.example.test/map" }],
    hours: [{ label: "Day use", value: "8 a.m. until sunset" }],
    vehicle_limits: [{ label: "Park motorhome limit", value: "35 feet" }],
    ...overrides,
  };
}
