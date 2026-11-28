# Fixture Decisions

- Discovery uses public responses through normal adapter methods. The existing search suite supplies synthetic edge-case coverage.
- Recreation.gov enrichment reads RIDB data. UseDirect reads park information and checks image availability. ReserveAmerica reads facility details after anonymous bootstrap. Preserve the minimum public data needed by each path.
- Catalog failure tests already exercise atomic refresh with synthetic inputs. Add representative recorded baselines and use deterministic failure injection to verify preservation.
- Metadata cases generally avoid season gates. When an endpoint uses a dated browsing grid, choose a supported date and freeze it during replay.

- The ReserveCalifornia facility image returned HTTP 403 during capture. The Arizona deployment supplied a successful Lost Dutchman park image and a campground image absence, so it represents UseDirect enrichment.
