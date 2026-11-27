# GoingToCamp provider TODOs

## GoingToCamp deployment verification (2026-11-16)

Live verification against `/api/transactionlocation`, `/api/resourceLocation`, `/api/bookingcategories`, `/api/resourcecategory`, `/api/equipment`, `/api/attribute/filterable`, `/api/availability/map`, and `/create-booking/results` confirmed 13 additional live GoingToCamp deployments alongside Washington State Parks (ID 12). All 13 are registered in `camply.providers.going_to_camp.variations` with permanent `Provider` IDs 14–26 and an Alembic seed migration:

- [x] **Wisconsin State Parks** (`https://wisconsin.goingtocamp.com`, US / WI, ID 14)
- [x] **Michigan State Parks** (`https://midnrreservations.com`, US / MI, ID 15)
- [x] **Tacoma Power Parks** (`https://tacomapower.goingtocamp.com`, US / WA, ID 16)
- [x] **Parks Canada** (`https://reservation.pc.gc.ca`, CA, ID 17)
- [x] **BC Parks** (`https://camping.bcparks.ca`, CA / BC, ID 18)
- [x] **Ontario Parks** (`https://reservations.ontarioparks.ca`, CA / ON, ID 19)
- [x] **Nova Scotia Parks** (`https://novascotia.goingtocamp.com`, CA / NS, ID 20)
- [x] **Manitoba Parks** (`https://manitoba.goingtocamp.com`, CA / MB, ID 21)
- [x] **Newfoundland & Labrador Provincial Parks** (`https://www.nlcamping.ca`, CA / NL, ID 22)
- [x] **Gatineau Park (NCC)** (`https://reservations.ncc-ccn.gc.ca`, CA / QC, ID 23)
- [x] **Long Point Region Conservation Authority** (`https://longpoint.goingtocamp.com`, CA / ON, ID 24)
- [x] **Maitland Valley Conservation Authority** (`https://maitlandvalley.goingtocamp.com`, CA / ON, ID 25)
- [x] **St. Clair Region Conservation Authority** (`https://stclair.goingtocamp.com`, CA / ON, ID 26)

### Candidates no longer on GoingToCamp

- [x] **Maryland Department of Natural Resources** (`https://parkreservations.maryland.gov`): `/api/*` returns **HTTP 404**; now operates on a white-label ReserveAmerica / Aspira portal.
- [x] **New Brunswick Provincial Parks** (`https://www.parcsnbparks.ca`): `/api/*` returns **HTTP 404**; operates on a custom reservation portal.
- [x] **Algonquin Highlands** (`https://algonquinhighlands.goingtocamp.com`): Host unreachable (`ConnectError`); bookings moved to `https://www.algonquinhighlands.ca`.
- [x] **Saugeen Valley Conservation Authority** (`https://saugeen.goingtocamp.com`): Host unreachable (`ConnectError`); bookings moved to `https://www.saugeenconservation.ca`.

## Platform follow-ups

- [ ] Support backcountry non-specific zone/access-point permits (`BookingModel = 5`, `ResourceModel in (1, 2, 3, 4)`) once backcountry permit scanning is added to the shared worker (`PLAN.md` Phase 3 Permits).
- [ ] Enforce provider `maxStay` / per-night minimum-stay restrictions and RV length (`max_vehicle_length`) filters in the shared worker poller.
- [ ] Persist site-level amenity and RV length facets into `search` discovery rows (`T3.2.1b`) and future `campsites` catalog tables.
- [ ] Coordinate rate limiting and cached catalog filter lookups across distributed worker processes.
