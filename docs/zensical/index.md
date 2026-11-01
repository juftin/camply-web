# Find your next campsite

**camply** watches campground availability and alerts you when a stay matches your plans. Explore campgrounds on a map, save a scan for your dates, and open the provider's booking page when a campsite becomes available.

**[Open camply at camply.juftin.dev →](https://camply.juftin.dev)**

## Get started

- **Use the hosted app:** [find a campground and create a scan](using-camply.md).
- **Run it on your machine:** [start the standalone app](self-hosting/standalone.md) with Python and SQLite.
- **Host your own instance:** choose [Docker Compose or Kubernetes](self-hosting/containers.md), then [configure login and alerts](configuration.md).
- **Contribute:** follow the [development guide](development.md) or browse the [technical references](reference.md).

camply finds availability; reservations are completed with the booking provider. An alert does not hold a campsite for you.

## About these docs

These guides cover everyday use and setup. Detailed engineering and operations documents are linked from the [reference directory](reference.md).

The site is built locally with [Zensical](https://zensical.org/). Run `task docs:serve` from the repository root to preview it at <http://127.0.0.1:8001>, or `task docs:build` to generate `build/docs`.

camply is licensed under [PolyForm Noncommercial 1.0.0](https://github.com/juftin/camply-web/blob/main/LICENSE).
