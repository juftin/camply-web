# GoingToCamp provider TODOs

## Registered but disabled GoingToCamp deployments (IDs 13-25)

These deployments are registered as thin subclasses in `camply.providers.going_to_camp.variations` and seeded **disabled** by migration `e7a41c5b9d02`. On 2026-11-06 every public `/api/transactionlocation` request from the development environment returned an Azure WAF bot challenge (HTTP 403), so none could be verified. Before enabling each one (a follow-up migration setting `providers.enabled = true`), verify from an unblocked network that `/api/transactionlocation`, `/api/resourceLocation`, `/api/bookingcategories`, `/api/resourcecategory`, `/api/availability/map`, and `/create-booking/results` still work:

- [ ] **Wisconsin State Parks** (ID 13, `https://wisconsin.goingtocamp.com`, US / WI)
- [ ] **Michigan State Parks** (ID 14, `https://midnrreservations.com`, US / MI)
- [ ] **Tacoma Power Parks** (ID 15, `https://tacomapower.goingtocamp.com`, US / WA)
- [ ] **Parks Canada** (ID 16, `https://reservation.pc.gc.ca`, CA)
- [ ] **BC Parks** (ID 17, `https://camping.bcparks.ca`, CA / BC)
- [ ] **Ontario Parks** (ID 18, `https://reservations.ontarioparks.ca`, CA / ON)
- [ ] **Nova Scotia Parks** (ID 19, `https://novascotia.goingtocamp.com`, CA / NS)
- [ ] **Manitoba Parks** (ID 20, `https://manitoba.goingtocamp.com`, CA / MB)
- [ ] **Newfoundland & Labrador Provincial Parks** (ID 21, `https://nlcamping.ca`, CA / NL)
- [ ] **Gatineau Park (NCC)** (ID 22, `https://reservations.ncc-ccn.gc.ca`, CA / QC)
- [ ] **Long Point Region Conservation Authority** (ID 23, `https://longpoint.goingtocamp.com`, CA / ON)
- [ ] **Maitland Valley Conservation Authority** (ID 24, `https://maitlandvalley.goingtocamp.com`, CA / ON)
- [ ] **St. Clair Region Conservation Authority** (ID 25, `https://stclair.goingtocamp.com`, CA / ON)

## Legacy CLI deployments not registered

These legacy deployments did not return the WAF challenge but also do not expose a working GoingToCamp API, so they are not registered (checked 2026-11-06):

- [ ] **Maryland Department of Natural Resources** (`https://parkreservations.maryland.gov`): `/api/transactionlocation` returns 404 and the site now appears to run the Aspira platform (`aspiraone` session cookie). Needs a different provider adapter.
- [ ] **New Brunswick Provincial Parks** (`https://parcsnbparks.ca`): redirects to `www.parcsnbparks.ca`, where `/api/transactionlocation` returns 404. Needs endpoint rediscovery.
- [ ] **Algonquin Highlands** (`algonquinhighlands.goingtocamp.com`): hostname no longer resolves.
- [ ] **Saugeen Valley Conservation Authority** (`saugeen.goingtocamp.com`): hostname no longer resolves.

## Platform follow-ups

- [ ] Support backcountry non-specific zone/access-point permits (`BookingModel = 5`, `ResourceModel in (1, 2, 3, 4)`) once backcountry permit scanning is added to the shared worker (`PLAN.md` Phase 3 Permits).
- [ ] Enforce provider `maxStay` / per-night minimum-stay restrictions and RV length (`max_vehicle_length`) filters in the shared worker poller.
- [ ] Persist site-level amenity and RV length facets into `search` discovery rows (`T3.2.1b`) and future `campsites` catalog tables.
- [ ] Coordinate rate limiting and cached catalog filter lookups across distributed worker processes.
