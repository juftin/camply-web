# GoingToCamp provider TODOs

## Remaining GoingToCamp deployments to verify and register

`GoingToCampProvider` supports adding new GoingToCamp park systems as thin subclasses in `camply.providers.going_to_camp.variations` paired with a stable `Provider` identity and seed migration. Before enabling each candidate from the legacy CLI list, verify its current public `/api/transactionlocation`, `/api/resourceLocation`, `/api/bookingcategories`, `/api/resourcecategory`, `/api/availability/map`, and `/create-booking/results` endpoints (some deployments use regional Akamai/bot rules or updated domains):

- [ ] **Wisconsin State Parks** (`https://wisconsin.goingtocamp.com`, US / WI)
- [ ] **Maryland Department of Natural Resources** (`https://parkreservations.maryland.gov`, US / MD)
- [ ] **Michigan Department of Natural Resources** (`https://midnrreservations.com`, US / MI)
- [ ] **Tacoma Power Parks** (`https://tacomapower.goingtocamp.com`, US / WA)
- [ ] **Parks Canada** (`https://reservation.pc.gc.ca`, CA)
- [ ] **BC Parks** (`https://camping.bcparks.ca`, CA / BC)
- [ ] **Ontario Parks** (`https://reservations.ontarioparks.ca`, CA / ON)
- [ ] **Nova Scotia Parks** (`https://novascotia.goingtocamp.com`, CA / NS)
- [ ] **Manitoba Parks** (`https://manitoba.goingtocamp.com`, CA / MB)
- [ ] **New Brunswick Provincial Parks** (`https://parcsnbparks.ca`, CA / NB)
- [ ] **Newfoundland & Labrador Provincial Parks** (`https://nlcamping.ca`, CA / NL)
- [ ] **Gatineau Park (NCC)** (`https://reservations.ncc-ccn.gc.ca`, CA / QC)
- [ ] **Algonquin Highlands** (`https://algonquinhighlands.goingtocamp.com`, CA / ON)
- [ ] **Long Point Region Conservation Authority** (`https://longpoint.goingtocamp.com`, CA / ON)
- [ ] **Maitland Valley Conservation Authority** (`https://maitlandvalley.goingtocamp.com`, CA / ON)
- [ ] **Saugeen Valley Conservation Authority** (`https://saugeen.goingtocamp.com`, CA / ON)
- [ ] **St. Clair Region Conservation Authority** (`https://stclair.goingtocamp.com`, CA / ON)

## Platform follow-ups

- [ ] Support backcountry non-specific zone/access-point permits (`BookingModel = 5`, `ResourceModel in (1, 2, 3, 4)`) once backcountry permit scanning is added to the shared worker (`PLAN.md` Phase 3 Permits).
- [ ] Enforce provider `maxStay` / per-night minimum-stay restrictions and RV length (`max_vehicle_length`) filters in the shared worker poller.
- [ ] Persist site-level amenity and RV length facets into `search` discovery rows (`T3.2.1b`) and future `campsites` catalog tables.
- [ ] Coordinate rate limiting and cached catalog filter lookups across distributed worker processes.
