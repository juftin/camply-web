# Using camply

Start at **[camply.rocks](https://camply.rocks)**, or open your own instance. Sign in if the instance requires it.

To discover campgrounds and monitor availability locally in your terminal, see the
[command-line guide](cli.md). The CLI uses live provider APIs and console output
without a web account or database.

## Find a campground

Use Explore to search for a campground or browse the map. Open a campground to see its details and start monitoring it. Available providers and campgrounds depend on the instance's catalog.

## Save a scan

Choose your campground, arrival and departure dates, and minimum stay length. Save the scan to monitor matching openings. Manage your scans from the dashboard and open a scan to see its latest results.

Results group matching stays by date, with campsite details and links to book through the provider. You can edit a scan when your plans change or delete it when you no longer need it.

## Receive alerts

camply currently sends alerts through Pushover. Configure your Pushover user key in your account settings. Self-hosted instances also need a [Pushover application token](configuration.md#notifications) from the instance owner.

By default, an alert summarizes new openings and links to the scan's results. Availability changes quickly; follow the booking link and complete the reservation with the provider.

## Setting up a fresh instance

If you run your own instance and the catalog is empty, use **Sync Providers** in Admin Operations. The initial import can take time. Once it finishes, search for a campground and create your first scan.

See [configuration](configuration.md) for login and notification settings, or [standalone setup](self-hosting/standalone.md) to run camply locally.
