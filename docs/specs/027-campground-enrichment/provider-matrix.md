# Enrichment support across the other providers

**Verified**: 2026-11-13. This expands the [initial research](research.md) across every configured UseDirect deployment, ReserveAmerica, and Washington. Public read-only requests only; no production data changes or implementation. Counts and access outcomes are observations, not coverage guarantees.

## Results by configured provider

All ten UseDirect deployments returned HTTP 200 for their park catalogs, `GET fd/placeinfo/additional-place-info/{PlaceId}`, and a sampled `POST search/place`. Every deployment also had at least one verified park JPEG on its public booking site. Facility photos are less consistent.

| Provider                 | Verified park photo example                                                                                         | Sampled facility photo                                                                                                                 | Rich park description from `search/place`                                         |
| ------------------------ | ------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------- |
| California               | [Anza-Borrego, place 2](https://www.reservecalifornia.com/images/California/ParkImages/Place/2.jpg)                 | [Sempervirens, facility 335](https://www.reservecalifornia.com/images/California/ParkImages/Facility/335.jpg), under Big Basin/place 3 | 1,771 characters for Anza-Borrego                                                 |
| Florida                  | [Blue Spring, place 9](https://reserve.floridastateparks.org/Web/images/Florida/ParkImages/Place/9.jpg)             | Not found in four sampled facilities                                                                                                   | 675 characters for Blue Spring                                                    |
| Virginia                 | [Bear Creek Lake, place 1](https://reservevaparks.com/Web/images/Virginia/ParkImages/Place/1.jpg)                   | Not found in four sampled facilities                                                                                                   | 511 characters for Bear Creek Lake                                                |
| Minnesota                | [Maplewood, place 127](https://reservemn.usedirect.com/MinnesotaWeb/images/Minnesota/ParkImages/Place/127.jpg)      | Not found in four sampled facilities                                                                                                   | 235 characters for Maplewood                                                      |
| Ohio                     | [A.W. Marion, place 108](https://reserveohio.com/OhioCampWeb/images/Ohio/ParkImages/Place/108.jpg)                  | [A.W. Marion Campground, facility 60](https://reserveohio.com/OhioCampWeb/images/Ohio/ParkImages/Facility/60.jpg)                      | 313 characters for A.W. Marion                                                    |
| Arizona                  | [Alamo Lake, place 1](https://azstateparks.com/reserve/images/Arizona/ParkImages/Place/1.jpg)                       | Not found in four sampled facilities                                                                                                   | 705 characters for Alamo Lake                                                     |
| Missouri                 | [Arrow Rock, place 6](https://icampmo.usedirect.com/MSPWeb/images/Missouri/ParkImages/Place/6.jpg)                  | [Campground, facility 761](https://icampmo.usedirect.com/MSPWeb/images/Missouri/ParkImages/Facility/761.jpg)                           | 354 characters for Arrow Rock                                                     |
| Fairfax County           | [Burke Lake, place 7788](https://fairfax.usedirect.com/FairfaxFCPAWeb/images/FairfaxFCPA/ParkImages/Place/7788.jpg) | [Campgrounds, facility 3162](https://fairfax.usedirect.com/FairfaxFCPAWeb/images/FairfaxFCPA/ParkImages/Facility/3162.jpg)             | Empty for Burke Lake                                                              |
| Oregon Metro             | [Oxbow, place 102](https://reservemetro.usedirect.com/MetroWeb/images/OregonMetro/ParkImages/Place/102.jpg)         | Not found for either sampled Oxbow facility                                                                                            | 129 characters for Oxbow                                                          |
| Northern Territory       | [Davenport Ranges, place 2](https://parkbookings.nt.gov.au/Web/images/NorthernTerritory/ParkImages/Place/2.jpg)     | [Frew River campground, facility 2](https://parkbookings.nt.gov.au/Web/images/NorthernTerritory/ParkImages/Facility/2.jpg)             | 383 characters for Davenport Ranges                                               |
| ReserveAmerica           | No separate park catalog in our adapter                                                                             | Verified gallery data for Jackson Lake and Alger Island; zero photos for the sampled Florida primitive zone                            | Facility narratives, directions, amenities, seasons, and fee information verified |
| Washington / GoingToCamp | Thirteen images in the sampled official park gallery                                                                | Native booking API remains unverified; official gallery is park-level media                                                            | Official park website supplies descriptions and practical information             |

All positive image checks returned HTTP 200, `image/jpeg`, and JPEG signatures. Three representative UseDirect images and a ReserveAmerica image were also visually inspected. None of the checked legacy UseDirect assets matched the known generic `no-image.jpg` fallback. These are destination images; a facility-associated image can show surrounding scenery rather than individual campsites. A missing sampled asset does not mean the provider has no facility photos elsewhere.

## UseDirect: exact sources and request shapes

### Park and facility images

The public Florida and Virginia applications ship the same observed frontend bundle, and Minnesota ships a closely related bundle. The image templates are visible in [Florida's public application JavaScript](https://reserve.floridastateparks.org/Web/Keechma/js/main.js):

```text
{booking_root}/images/{enterprise}/ParkImages/Place/{PlaceId}.jpg
{booking_root}/images/{enterprise}/ParkImages/Facility/{FacilityId}.jpg
{booking_root}/images/{enterprise}/ParkImages/PlaceBanner/{PlaceId}.jpg
```

The frontend reads the deployment's `enterpriceName` setting for the enterprise component. Verified names are `California`, `Florida`, `Virginia`, `Minnesota`, `Ohio`, `Arizona`, `Missouri`, `FairfaxFCPA`, `OregonMetro`, and `NorthernTerritory`. Match capitalization and the complete booking root; these are not interchangeable hosts/paths.

California's newer React application uses an image base URL plus the same park-image layout. Its current public asset root worked directly under `https://www.reservecalifornia.com/`; an older `/Web/` path did not work. Anza-Borrego's park photo and banner both loaded; Sempervirens' facility image loaded, while three other facility requests returned 403. Do not interpret those 403 responses as successful empty galleries.

Sample banner requests succeeded for California, Missouri, and Oregon Metro. Several other sampled banners returned 404. Banners are optional, and can be large: the Oregon image exceeded the 4 MB research read cap. The research did not measure its complete size. Prefer a validated smaller park image over assuming every banner is suitable for a card.

The templates expose individual images, not a verified multi-photo gallery enumeration API. No photographer credits, alt text, or dimensions accompany these static URLs; do not invent that metadata.

### More useful descriptions than the catalogs

The bulk `fd/places` descriptions are often just names. The frontend's `POST search/place` response contains a richer `SelectedPlace.Description`, plus `Url`, `ImageUrl`, `BannerUrl`, coordinates, timezone, park size, and child facilities. It returned nonempty narratives in nine of ten sampled deployments; Burke Lake was empty.

The read-only probe used each sampled `PlaceId`, `StartDate: "11-20-2026"`, `Nights: 1`, `CustomerId: 0`, `NearbyLimit: 0`, `isSearchAllParks: false`, neutral coordinates, no ADA/equipment/amenity filters, and name sorting. Other frontend request fields were zero/null defaults. Responses identified the requested `SelectedPlace.PlaceId`.

This is a **dated search**, not a metadata-only endpoint: it also computes facility availability. Its descriptive fields are useful, but repeated requests have a different cost from static asset discovery. Any implementation should fetch/cache narratives through enrichment work, avoid user-request/scan coupling, and discard the response's availability when updating destination details. Do not add a full dated-search crawl to every ordinary catalog sync without measuring its cost.

### The API's image fields are not uniformly usable

- Virginia, Minnesota, Fairfax, Oregon Metro, and Northern Territory returned placeholder `ImageUrl` hosts such as `some-server`.
- Florida and Ohio returned image URLs on UAT/preproduction hosts.
- California's returned content-host URL gave HTTP 404 while its public booking-site photo worked.
- Nine sampled `BannerUrl` values were identical generic California paths, not destination-specific banners. The sampled generic URL also returned HTTP 404.

**Decision**: Use verified deployment-specific public image templates and validate each result. Do not trust URL-looking values, generic banners, or catalog key presence as evidence of a real photo.

### Practical park information

`GET fd/placeinfo/additional-place-info/{PlaceId}` worked on all ten configured API roots. Useful populated fields included official websites and hours; some samples also supplied motorhome/trailer lengths and a display flag. Examples included nonzero motorhome-length values for Florida, Virginia, Minnesota, Ohio, Arizona, and Missouri. Units were not established by this probe.

Values such as `"0"`, `"Not Available"`, empty strings, and nulls occur frequently. Respect `DisplayMaxTrailerLengthOnWeb`, retain source labels/units, and do not interpret zero as a zero-foot vehicle allowance. Northern Territory's day-use-hours field contained visitor-pass information, demonstrating that these fields can contain general prose rather than machine-readable schedules. The initial Fairfax sample was an administrative entry with no useful website/hours, so route support does not guarantee populated data.

## ReserveAmerica: verified multi-photo galleries

The [public application](https://a1.reserveamerica.com/) and its shipped JavaScript expose the facility-details request:

```text
GET https://a1.reserveamerica.com/jaxrs-json/facilities/{contract}/{facility}?detailsOnly=false
```

Anonymous cookies and token headers derived from those cookies were needed for successful facility requests. Public root/bootstrap requests intermittently returned 403; later normal anonymous requests succeeded. Direct uninitialized facility requests returned 401. No account login or credentials were used. Use the existing adapter's session lifecycle and preserve failures rather than treating them as no content.

| Facility                                                                                                                                 | Original photos | Amenities | Image verification                                                   |
| ---------------------------------------------------------------------------------------------------------------------------------------- | --------------- | --------- | -------------------------------------------------------------------- |
| [Jackson Lake State Park, `CO_50028`](https://a1.reserveamerica.com/jaxrs-json/facilities/CO/50028?detailsOnly=false)                    | 4               | 35        | One original photo returned HTTP 200 JPEG and was visually inspected |
| [Alger Island, `NY_695`](https://a1.reserveamerica.com/jaxrs-json/facilities/NY/695?detailsOnly=false)                                   | 6               | 20        | One original photo returned HTTP 200 JPEG                            |
| [Annutteliga Hammock primitive zone, `FLFS_1120158`](https://a1.reserveamerica.com/jaxrs-json/facilities/FLFS/1120158?detailsOnly=false) | 0               | 1         | Valid empty photo lists; practical details still present             |

Verified fields include `originalPhotos[]` and `facilityPhotos[]` with `photoURL` and `description`; amenities with IDs, names, and distance fields; narrative notes, directions, seasons, booking-window information, related links, and fee/cancellation text. Do not interpret an amenity's presence as on-site when its distance fields describe a nearby feature.

The two photo lists are alternative renditions: each sampled nonempty list had matching counts/captions. Do not concatenate them into duplicate galleries. `originalPhotos` contains relative paths with spaces, existing percent escapes, and literal `{pht}` tokens. Correct URL joining/encoding matters: an encoded original loaded while the sampled `/webphotos/{contract}/pid{id}/0` rendition returned 403. Public `www` image requests also returned 403 here. Preserve the working original source host independently of public booking URLs.

**Decision**: ReserveAmerica is ready for a scoped enrichment adapter design, including real galleries. Repeated access is still variable and some legitimate destinations have no photos. Broad coverage and source usage requirements remain release checks.

## Washington: official operator website fallback

The native Washington GoingToCamp catalog remained HTTP 403. Wisconsin, BC Parks, and Parks Canada catalog probes also returned 403; those outcomes do not establish media support or lack of support for other GoingToCamp deployments.

The [official Cape Disappointment park page](https://parks.wa.gov/find-parks/state-parks/cape-disappointment-state-park) returned HTTP 200 through a normal HTTP client. Its `parks_gallery_desc` section contained 13 distinct images with descriptive alt text. One gallery image was fetched and verified as HTTP 200 JPEG. Other parts of the page include unrelated recommendation images and icons, so extracting every `<img>` would attach incorrect images.

The page's booking link contains `resourceLocationId=-2147483633`, providing an explicit connection to the native campground identity. This is stronger evidence than name-only matching, but it does not make all park-gallery photos campground-specific. Preserve their park scope and source page; inspect each official page's links rather than inferring parent IDs or reusing dated booking parameters.

The page also offers park descriptions, facilities, accessibility, maps, and current information. This is HTML enrichment from the park operator, **not** a verified GoingToCamp media API. A generic Drupal `/jsonapi` request returned 404; no bulk JSON feed was established. Source discovery, field extraction, source usage, and reliable associations would require a separate adapter and fixtures.

## Revised priorities

1. Keep Recreation.gov export enrichment as the first implementation slice.
2. Add UseDirect park images and practical information across the ten verified deployments, plus facility images wherever validation succeeds. Richer descriptions from the dated search are an optional, measured extension.
3. Add ReserveAmerica facility details and original-photo galleries with its existing session handling. It offers more verified gallery structure than the single-image UseDirect paths.
4. Treat Washington official-site enrichment as a separate source adapter. Continue investigating native GoingToCamp media when access permits; do not let that uncertainty block the verified integrations.

The verified Recreation.gov, UseDirect, and ReserveAmerica sources are implemented in the [feature plan](plan.md); Washington scraping and native GoingToCamp media remain deferred. This survey sampled destinations, not every park/facility, and does not establish permission to reproduce or mirror images. No live payloads, visitor photos, session cookies, or third-party application code are committed.
