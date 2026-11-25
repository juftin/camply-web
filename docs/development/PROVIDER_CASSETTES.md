# Provider Availability Cassettes

The backend test suite replays known-open searches against the real provider adapters and camply's equipment matching. The recorded nights can pass in the calendar and still replay. Review scenarios every 30 days and when a provider changes its booking flow or API response.

## Find a replacement stay

1. Open the booking link for the scenario below. Select overnight camping, the campground or loop, and the same equipment category and vehicle length if supported. Use the site list or availability calendar to find an open stay and note the site's published equipment limits. Try a weekday in the booking window or another campground in the same provider if the current campground is closed or sold out.
2. Confirm the expected site and nights on the booking site. For an equipment contrast, also identify an available site for the same nights that should be filtered out. Use the provider's calendar and site details independently of the test result.
3. Update the matching case in `tests/providers/availability_cases.py`. Keep its key. Change the campground ID and booking URL if needed, the arrival and checkout dates, equipment inputs, and expected and excluded sites. Expected nights must precede checkout.

For a year rollover, check the new season and release window first. For example, the Jumbo Rocks RV case moved from Dec. 7–9, 2026 to Jan. 11–12, 2027 after confirming site 089 was open for a 30-foot RV. The tent case kept its December dates.

### Find availability on each booking system

- **Recreation.gov** — Open the campground's Availability tab. Choose dates and equipment, then open the expected campsite's details. Its ID is in its campsite URL.
- **UseDirect** — Open the park and the facility or loop listed below. Select the dates and equipment in the reservation search or grid. For Fairfax County, use Lake Fairfax and its Campgrounds option. For Oregon Metro, choose Oxbow Regional Park and its campground. For Northern Territory, choose Litchfield National Park and Florence Falls 2WD Campground. Where the public link opens the general search, choose the park and campground by name.
- **GoingToCamp** — Use the linked resource location, choose an overnight booking category and search dates and equipment, then open the highlighted loop and campsite. If there are seasonal or group categories, check that the chosen campsite is open for the intended overnight stay. Preserve the resource-location ID, including the minus sign.
- **ReserveAmerica** — Use the campground calendar, select camping dates and equipment, and look up the site in the available results. Keep campground IDs in `contract_facility` form. The public booking site and the API use different hosts.

The test uses camply's normalized campsite types. A site offered for both RV and tent may have a single normalized type. For example, the Florida cases use two vehicle lengths at Oscar Scherer instead of treating its mixed-use sites as tent-only.

## Record and verify one scenario

Use the full pytest case identifier. The candidate path must be a new YAML file under the ignored `tmp/` directory. The recorder keeps public fields needed by the adapters, removes live session headers and unrelated content, and uses synthetic values for anonymous session replay.

```sh
case_key=recreation-gov/jumbo-rocks-rv
test_case="tests/providers/test_availability_cassettes.py::test_known_open_search[asyncio-${case_key}]"
candidate=tmp/provider-cassettes/jumbo-rocks-rv.yaml

task backend:test -- "$test_case" \
  --record-provider-availability "$case_key" \
  --provider-availability-candidate "$candidate"

task backend:test -- "$test_case" --provider-availability-candidate "$candidate"
```

Review the candidate's requests, headers, JSON bodies, and fixture diff for user data, credentials, live session values, and unrelated fields. Run the second command with outbound networking disabled. Copy the passing candidate to `tests/providers/cassettes/availability/<case-key>.yaml`, update the scenario's verified date below, and run the provider suite.

```sh
task backend:test -- tests/providers/test_availability_cassettes.py
```

If recording fails or inventory closes before capture, use another open stay or defer. Keep the previous case and cassette together, preserve the last successful verification date, and note the reason and next booking window below. Existing fixtures stay replayable independently of live inventory.

## Recorded searches

Arrival and checkout are local campground dates. The scenario key identifies its entry in `tests/providers/availability_cases.py` and its cassette under `tests/providers/cassettes/availability/`.

| Scenario key                       | Campground and native ID                                                                                                                                                        | Arrival to checkout      | Equipment filter | Expected site                              | Verified   |
| ---------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------ | ---------------- | ------------------------------------------ | ---------- |
| `recreation-gov/jumbo-rocks-tent`  | [Jumbo Rocks Campground](https://www.recreation.gov/camping/campgrounds/272300) (`272300`)                                                                                      | 2026-12-07 to 2026-12-09 | Tent             | 015 (`103820`)                             | 2026-11-25 |
| `recreation-gov/jumbo-rocks-rv`    | [Jumbo Rocks Campground](https://www.recreation.gov/camping/campgrounds/272300) (`272300`)                                                                                      | 2027-01-11 to 2027-01-12 | RV 30 ft         | 089 (`103860`)                             | 2026-11-25 |
| `reserve-california/rv-19ft`       | [Borrego Palm Canyon (sites 53-89)](https://www.reservecalifornia.com/park/2/327) (`327`)                                                                                       | 2026-12-07 to 2026-12-09 | RV 19 ft         | Campsite #53 (`4245`)                      | 2026-11-25 |
| `reserve-california/rv-26ft`       | [Borrego Palm Canyon (sites 53-89)](https://www.reservecalifornia.com/park/2/327) (`327`)                                                                                       | 2026-12-07 to 2026-12-09 | RV 26 ft         | Campsite #66 (`4258`)                      | 2026-11-25 |
| `florida-state-parks/rv-19ft`      | [Oscar Scherer State Park, Loop A](https://reserve.floridastateparks.org/Web/#!park/51/139) (`139`)                                                                             | 2026-12-07 to 2026-12-09 | RV 19 ft         | RV or Tent #008 (`2891`)                   | 2026-11-25 |
| `florida-state-parks/rv-36ft`      | [Oscar Scherer State Park, Loop A](https://reserve.floridastateparks.org/Web/#!park/51/139) (`139`)                                                                             | 2026-12-07 to 2026-12-09 | RV 36 ft         | RV or Tent #011 (`2894`)                   | 2026-11-25 |
| `virginia-state-parks/tent`        | [First Landing State Park, B - Collier Loop - (66-99, 101, 102)](https://reservevaparks.com/Web/#!park/10/59) (`59`)                                                            | 2027-05-10 to 2027-05-12 | Tent             | Tent Only-No Hookups #66 (`838`)           | 2026-11-25 |
| `virginia-state-parks/rv`          | [First Landing State Park, B - Collier Loop - (66-99, 101, 102)](https://reservevaparks.com/Web/#!park/10/59) (`59`)                                                            | 2027-05-10 to 2027-05-12 | RV 30 ft         | Electric/Water #73 (`826`)                 | 2026-11-25 |
| `minnesota-state-parks/tent`       | [Afton State Park, Hike In](https://reservemn.usedirect.com/MinnesotaWeb/#!park/92/778) (`778`)                                                                                 | 2027-03-08 to 2027-03-09 | Tent             | Hike-In #01 (`15579`)                      | 2026-11-25 |
| `minnesota-state-parks/rv`         | [Wild River Campground](https://reservemn.usedirect.com/MinnesotaWeb/#!park/106/895) (`895`)                                                                                    | 2026-12-07 to 2026-12-09 | RV 45 ft         | Drive-In Electric #61E (`12810`)           | 2026-11-25 |
| `ohio-state-parks/tent`            | [Hocking Hills Camp Sites 1-93](https://reserveohio.com/OhioCampWeb/#!park/103/458) (`458`)                                                                                     | 2027-04-19 to 2027-04-21 | Tent             | Campsite Non-Electric #081 (`19614`)       | 2026-11-25 |
| `ohio-state-parks/rv`              | [Hocking Hills Camp Sites 1-93](https://reserveohio.com/OhioCampWeb/#!park/103/458) (`458`)                                                                                     | 2027-04-19 to 2027-04-21 | RV 30 ft         | Campsite Electric #013 (`19539`)           | 2026-11-25 |
| `arizona-state-parks/rv-37ft`      | [Lost Dutchman Main Campground](https://azstateparks.com/reserve/#!park/13/64) (`64`)                                                                                           | 2027-04-05 to 2027-04-07 | RV 37 ft         | Rustic #14 (`1196`)                        | 2026-11-25 |
| `arizona-state-parks/rv-50ft`      | [Lost Dutchman Main Campground](https://azstateparks.com/reserve/#!park/13/64) (`64`)                                                                                           | 2027-04-05 to 2027-04-07 | RV 50 ft         | Rustic #04 (`1186`)                        | 2026-11-25 |
| `missouri-state-parks/rv-44ft`     | [Bennett Spring State Park, Campground 1](https://icampmo.usedirect.com/MSPWeb/#!park/11/763) (`763`)                                                                           | 2026-12-07 to 2026-12-09 | RV 44 ft         | Sewer/Electric/Water 50 amp #113 (`10529`) | 2026-11-25 |
| `missouri-state-parks/rv-86ft`     | [Bennett Spring State Park, Campground 1](https://icampmo.usedirect.com/MSPWeb/#!park/11/763) (`763`)                                                                           | 2026-12-07 to 2026-12-09 | RV 86 ft         | Sewer/Electric/Water 50 amp #118 (`10534`) | 2026-11-25 |
| `fairfax-county/other`             | [Lake Fairfax Park, Campgrounds](https://fairfax.usedirect.com/FairfaxFCPAWeb) (`3163`)                                                                                         | 2026-12-07 to 2026-12-09 | Other            | Mixed Use (Full Electric) #FC39 (`18632`)  | 2026-11-25 |
| `fairfax-county/rv`                | [Lake Fairfax Park, Campgrounds](https://fairfax.usedirect.com/FairfaxFCPAWeb) (`3163`)                                                                                         | 2026-12-07 to 2026-12-09 | Rv               | RV Only (Full Electric) #FC1 (`18652`)     | 2026-11-25 |
| `oregon-metro/tent`                | [Oxbow Regional Park Campground](https://reservemetro.usedirect.com/MetroWeb) (`107`)                                                                                           | 2027-05-17 to 2027-05-19 | Tent             | Tent Site #OC04 (`693`)                    | 2026-11-25 |
| `oregon-metro/rv`                  | [Oxbow Regional Park Campground](https://reservemetro.usedirect.com/MetroWeb) (`107`)                                                                                           | 2027-05-17 to 2027-05-19 | Rv               | RV Site #OC01 (`659`)                      | 2026-11-25 |
| `northern-territory/first-window`  | [Florence Falls 2WD Campground](https://parkbookings.nt.gov.au/Web) (`79`)                                                                                                      | 2026-12-07 to 2026-12-08 | Rv               | Campsite #N01 (`665`)                      | 2026-11-25 |
| `northern-territory/second-window` | [Florence Falls 2WD Campground](https://parkbookings.nt.gov.au/Web) (`79`)                                                                                                      | 2026-12-15 to 2026-12-16 | Rv               | Campsite #N01 (`665`)                      | 2026-11-25 |
| `washington-state-parks/cabin`     | [Deception Pass State Park](https://washington.goingtocamp.com/create-booking/results?resourceLocationId=-2147483624&transactionLocationId=-2147483630) (`-2147483624`)         | 2026-12-07 to 2026-12-09 | Cabin            | C2 (`-2147481328`)                         | 2026-11-25 |
| `washington-state-parks/rv`        | [Deception Pass State Park](https://washington.goingtocamp.com/create-booking/results?resourceLocationId=-2147483624&transactionLocationId=-2147483630) (`-2147483624`)         | 2026-12-07 to 2026-12-09 | RV 30 ft         | 345 (`-2147481286`)                        | 2026-11-25 |
| `reserve-america/tent`             | [Chatfield State Park](https://www.reserveamerica.com/camping/chatfield-state-park/r/campgroundDetails.do?contractCode=CO&parkId=50028) (`CO_50028`)                            | 2026-12-07 to 2026-12-09 | Tent             | 070 (`CO_50028_1273`)                      | 2026-11-25 |
| `reserve-america/rv`               | [Chatfield State Park](https://www.reserveamerica.com/camping/chatfield-state-park/r/campgroundDetails.do?contractCode=CO&parkId=50028) (`CO_50028`)                            | 2026-12-07 to 2026-12-09 | RV 30 ft         | 015 (`CO_50028_1338`)                      | 2026-11-25 |
| `wisconsin-state-parks/tent`       | [Devil's Lake State Park](https://wisconsin.goingtocamp.com/create-booking/results?resourceLocationId=-2147483634&transactionLocationId=-2147483634) (`-2147483634`)            | 2027-04-12 to 2027-04-14 | Tent             | G1 (`-2147482503`)                         | 2026-11-25 |
| `wisconsin-state-parks/rv`         | [Devil's Lake State Park](https://wisconsin.goingtocamp.com/create-booking/results?resourceLocationId=-2147483634&transactionLocationId=-2147483634) (`-2147483634`)            | 2027-04-12 to 2027-04-14 | RV 30 ft         | 88 (`-2147482827`)                         | 2026-11-25 |
| `michigan-state-parks/tent`        | [Tahquamenon Falls State Park](https://midnrreservations.com/create-booking/results?resourceLocationId=-2147483348&transactionLocationId=-2147483518) (`-2147483348`)           | 2026-12-07 to 2026-12-09 | Tent             | 174 (`-2147466893`)                        | 2026-11-25 |
| `michigan-state-parks/rv`          | [Tahquamenon Falls State Park](https://midnrreservations.com/create-booking/results?resourceLocationId=-2147483348&transactionLocationId=-2147483518) (`-2147483348`)           | 2026-12-07 to 2026-12-09 | RV 30 ft         | 154 (`-2147466689`)                        | 2026-11-25 |
| `tacoma-power-parks/tent`          | [Alder Lake](https://tacomapower.goingtocamp.com/create-booking/results?resourceLocationId=-2147483648&transactionLocationId=-2147483648) (`-2147483648`)                       | 2027-05-17 to 2027-05-19 | Tent             | 53 (`-2147483579`)                         | 2026-11-25 |
| `tacoma-power-parks/rv`            | [Alder Lake](https://tacomapower.goingtocamp.com/create-booking/results?resourceLocationId=-2147483648&transactionLocationId=-2147483648) (`-2147483648`)                       | 2027-05-17 to 2027-05-19 | RV 30 ft         | 324 (`-2147483433`)                        | 2026-11-25 |
| `parks-canada/rv-28ft`             | [Banff - Tunnel Mountain Village 2](https://reservation.pc.gc.ca/create-booking/results?resourceLocationId=-2147483648&transactionLocationId=-2147483648) (`-2147483648`)       | 2026-12-07 to 2026-12-09 | RV 28 ft         | A15 (`-2147474283`)                        | 2026-11-25 |
| `parks-canada/rv-35ft`             | [Banff - Tunnel Mountain Village 2](https://reservation.pc.gc.ca/create-booking/results?resourceLocationId=-2147483648&transactionLocationId=-2147483648) (`-2147483648`)       | 2026-12-07 to 2026-12-09 | RV 35 ft         | B70 (`-2147474460`)                        | 2026-11-25 |
| `bc-parks/group-rv`                | [Golden Ears Provincial Park](https://camping.bcparks.ca/create-booking/results?resourceLocationId=-2147483606&transactionLocationId=-2147483599) (`-2147483606`)               | 2027-03-08 to 2027-03-10 | RV               | G1-Golden Ears Group (`-2147480709`)       | 2026-11-25 |
| `bc-parks/group-other`             | [Golden Ears Provincial Park](https://camping.bcparks.ca/create-booking/results?resourceLocationId=-2147483606&transactionLocationId=-2147483599) (`-2147483606`)               | 2027-03-08 to 2027-03-10 | Other            | G3-Woodlands Group (`-2147472926`)         | 2026-11-25 |
| `ontario-parks/tent`               | [Algonquin - Mew Lake Campground](https://reservations.ontarioparks.ca/create-booking/results?resourceLocationId=-2147483585&transactionLocationId=-2147483581) (`-2147483585`) | 2026-12-07 to 2026-12-09 | Tent             | 45 (`-2147472331`)                         | 2026-11-25 |
| `ontario-parks/rv`                 | [Algonquin - Mew Lake Campground](https://reservations.ontarioparks.ca/create-booking/results?resourceLocationId=-2147483585&transactionLocationId=-2147483581) (`-2147483585`) | 2026-12-07 to 2026-12-09 | RV 30 ft         | 50 (`-2147472291`)                         | 2026-11-25 |
| `gatineau-park/first-window`       | [Gatineau Park, Winter](https://reservations.ncc-ccn.gc.ca/create-booking/results?resourceLocationId=-2147483647&transactionLocationId=-2147483647) (`-2147483647`)             | 2027-01-11 to 2027-01-12 | Tent             | GR5 (`-2147483270`)                        | 2026-11-25 |
| `gatineau-park/second-window`      | [Gatineau Park, Winter](https://reservations.ncc-ccn.gc.ca/create-booking/results?resourceLocationId=-2147483647&transactionLocationId=-2147483647) (`-2147483647`)             | 2027-01-12 to 2027-01-13 | Tent             | GR5 (`-2147483270`)                        | 2026-11-25 |

Minnesota uses an Afton hike-in tent site and a Wild River drive-in RV site. BC Parks uses the group camping calendar at Golden Ears. Camply classifies the two available group sites as RV and Other. The group inventory supplied no vehicle lengths. Recheck individual camping for a tent and vehicle-length contrast when those sites are bookable.

Northern Territory's Florence Falls 2WD and 4WD grids returned available sites with a single normalized RV category and no vehicle lengths. The two 2WD scenarios use distinct dates. Gatineau's Jan. 11 and Jan. 19 winter probes both returned only one normalized category, Tent. Its summer resource returned no available sites in the sampled January and May windows. Recheck the summer release for a second category. These constraints are listed in `EQUIPMENT_FALLBACKS` in `tests/providers/test_availability_cassettes.py`.

## Deferred initial recordings

These probes found no bookable inventory on 2026-11-25. Each provider has a named expected failure in the coverage check. Remove its entry from `SEASONAL_GAPS` in `tests/providers/test_availability_cassettes.py` once both cases and their refresh details are ready. The rest of the suite runs normally.

| Provider                        | Booking target and native ID                                                                                                                                                      | When to retry                                                                                                                                                                                                                                   |
| ------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Nova Scotia Parks               | [Rissers Beach Provincial Park](https://novascotia.goingtocamp.com/create-booking/results?resourceLocationId=-2147483635&transactionLocationId=-2147483632) (`-2147483635`)       | The June 7 probe was empty. The [Nova Scotia reservation page](https://parks.novascotia.ca/make-reservation) lists an April 2027 release. After release, look for open weekday tent and serviced RV sites.                                      |
| Manitoba Parks                  | [Birds Hill Campground](https://manitoba.goingtocamp.com/create-booking/results?resourceLocationId=-2147483644&transactionLocationId=-2147483641) (`-2147483644`)                 | May 24 and June 7 at Birds Hill and June 7 at Kiche Manitou were empty. Follow the [Manitoba reservation service schedule](https://gov.mb.ca/sd/parks/prs/index.html) for the Birds Hill release, then check the serviced and unserviced loops. |
| Newfoundland and Labrador Parks | [Butter Pot Provincial Park](https://www.nlcamping.ca/create-booking/results?resourceLocationId=-2147483646&transactionLocationId=-2147483646) (`-2147483646`)                    | May 24 and June 7 probes were empty. Check the [provincial campsite reservation service](https://www.gov.nl.ca/tcar/home/parks/reservations/) for the launch and use an in-season weekday.                                                      |
| Long Point Region               | [Backus Heritage Conservation Area](https://longpoint.goingtocamp.com/create-booking/results?resourceLocationId=-2147483648&transactionLocationId=-2147483648) (`-2147483648`)    | May 24 and June 7 probes were empty. Follow the [conservation authority's camping page](https://www.lprca.on.ca/outdoor-recreation/camping/) for the next nightly release.                                                                      |
| Maitland Valley                 | [Falls Reserve Conservation Area](https://maitlandvalley.goingtocamp.com/create-booking/results?resourceLocationId=-2147483648&transactionLocationId=-2147483648) (`-2147483648`) | May 24, June 7, and July 12 probes were empty. The [Falls Reserve camping page](https://mvca.on.ca/camping/frca-camping/) lists an early January reopening for reservations.                                                                    |
| St. Clair Region                | [Warwick Conservation Area](https://stclair.goingtocamp.com/create-booking/results?resourceLocationId=-2147483646&transactionLocationId=-2147483643) (`-2147483646`)              | May 24 and June 7 probes were empty. The [conservation authority](https://www.scrca.on.ca/conservation-lands/) lists Jan. 11, 2027 for online bookings. Try a weekday after the release.                                                        |

## Metadata recordings

Metadata replay covers discovery and exact lookup, published enrichment, catalog sync, and campsite listing. The inventory is in `tests/providers/metadata_cases.py`. Verification is independent of the seasonal availability recordings. The catalog cases that need a dated browse grid use December 7, 2026. Update the clock in `tests/providers/test_metadata_catalog_cassettes.py` together with those recordings if a new browse date is needed.

| Operation and case key       | Public verification target                                                                                                                                                         | Recording                                             | Last verified |
| ---------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------- | ------------- |
| `discovery/recreation-gov`   | [Jumbo Rocks](https://www.recreation.gov/camping/campgrounds/272300) (`272300`), Joshua Tree (`2782`)                                                                              | `discovery/recreation-gov.yaml`                       | 2026-11-25    |
| `discovery/usedirect`        | [South Camp](https://www.reservecalifornia.com/park/690/611) (`611`), [Pfeiffer Big Sur SP](https://parks.ca.gov/?page_id=29832) (`690`)                                           | `discovery/usedirect.yaml`                            | 2026-11-25    |
| `discovery/going-to-camp`    | [Deception Pass](https://washington.goingtocamp.com/create-booking/results?resourceLocationId=-2147483624&transactionLocationId=-2147483630) (`-2147483624`), parent `-2147483630` | `discovery/going-to-camp.yaml`                        | 2026-11-25    |
| `discovery/reserve-america`  | [Chatfield State Park](https://www.reserveamerica.com/campgroundDetails.do?contractCode=CO&parkId=50021) (`CO_50021`), Colorado state catalog                                      | `discovery/reserve-america.yaml`                      | 2026-11-25    |
| `enrichment/recreation-gov`  | [Jumbo Rocks](https://www.recreation.gov/camping/campgrounds/272300) and Joshua Tree, RIDB archive                                                                                 | `ridb/joshua-tree.zip`                                | 2026-11-25    |
| `enrichment/usedirect`       | [Lost Dutchman](https://azstateparks.com/reserve/#!park/13/64) campground (`64`) and park (`13`)                                                                                   | `enrichment/usedirect.yaml`                           | 2026-11-25    |
| `enrichment/reserve-america` | [Jackson Lake State Park](https://www.reserveamerica.com/campgroundDetails.do?contractCode=CO&parkId=50028) (`CO_50028`)                                                           | `enrichment/reserve-america.yaml`                     | 2026-11-25    |
| `catalog/recreation-gov`     | Jumbo Rocks site 001 (`103904`) and Joshua Tree (`2782`)                                                                                                                           | `catalog/recreation-gov.yaml`, `ridb/joshua-tree.zip` | 2026-11-25    |
| `catalog/usedirect`          | Borrego Palm Canyon site 53 (`4245`) and Anza-Borrego (`2`)                                                                                                                        | `catalog/usedirect.yaml`                              | 2026-11-25    |
| `catalog/going-to-camp`      | Deception Pass site 31 (`-2147481558`) and parent `-2147483630`                                                                                                                    | `catalog/going-to-camp.yaml`                          | 2026-11-25    |
| `catalog/reserve-america`    | Chatfield State Park site 001 (`CO_50021_3134`), Colorado state catalog                                                                                                            | `catalog/reserve-america.yaml`                        | 2026-11-25    |

Paths in the recording column are relative to `tests/providers/cassettes/metadata/`. ReserveAmerica records and replays a Colorado subset for discovery and sync, including its state pagination. ReserveAmerica has no recreation-area parent. GoingToCamp has no enrichment recording because its adapter has no enrichment path. The Lost Dutchman replay checks a successful park image and a campground without an image. The cassette retains only the image prefix the adapter needs.

For ReserveCalifornia discovery, search for `South Camp` in California. The recorded park catalog lists South Camp (`611`), Weyland Camp (`612`), and Main Camp (`767`) with online booking enabled. Group Sites A & B (`609`) and Day Use Lots 3 and 4 (`2092`, `2093`) are present with `AllowWebBooking: false`. Keep both the included and excluded rows when refreshing so the test exercises area expansion filtering.

### Refresh a single metadata recording

1. Verify the target, names, IDs, relationships, and known fields on the public provider source. Update the inventory and test expectations independently of the replay output.
2. Record the selected operation to a new candidate under `tmp/`. For example, use the following commands for Recreation.gov discovery.
3. Review the candidate for public data, synthetic session placeholders, and relevant request matching fields. Run the replay command with outbound networking disabled. Copy the passing candidate into the recording path and update its verification date. Leave the committed recording available if recording or replay fails.

```sh
node='tests/providers/test_metadata_discovery_cassettes.py::test_metadata_discovery[asyncio-recreation-gov]'
candidate=tmp/provider-metadata/recreation-gov-discovery.yaml

task backend:test -- "$node" \
  --record-provider-metadata discovery/recreation-gov \
  --provider-metadata-candidate "$candidate"
task backend:test -- "$node" --provider-metadata-candidate "$candidate"
```

For the shared Recreation.gov catalog and enrichment archive, download the [public RIDB export](https://ridb.recreation.gov/downloads/RIDBFullExport_V1_JSON.zip) into ignored storage. Use the archive tool to retain the selected area and campground, then review the compact ZIP members for public fields. With outbound networking disabled, run both tests against the same candidate. The catalog test uses the ZIP for sync and the existing YAML cassette for campsite listing. Replace `tests/providers/cassettes/metadata/ridb/joshua-tree.zip` and update its verification dates only after both tests pass.

```sh
uv run python -m tests.providers.metadata_archive \
  tmp/provider-metadata/ridb-full.zip tmp/provider-metadata/joshua-tree-candidate.zip \
  --area-id 2782 --campground-id 272300

candidate=tmp/provider-metadata/joshua-tree-candidate.zip
task backend:test -- \
  'tests/providers/test_metadata_enrichment_cassettes.py::test_metadata_enrichment[asyncio-recreation-gov]' \
  --provider-metadata-candidate "$candidate"
task backend:test -- \
  'tests/providers/test_metadata_catalog_cassettes.py::test_metadata_catalog[asyncio-recreation-gov]' \
  --provider-metadata-candidate "$candidate"
```
