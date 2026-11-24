# Using the web app

Open [camply.rocks](https://camply.rocks) or your own camply instance and sign in if prompted.

Prefer the terminal? See the [command-line guide](cli.md) for local searches without an account or database.

## Find a campground

Use **Explore** to search by name or browse the map. Open a campground to inspect its details, photos, and recent availability, then start a scan from that page.

## Save a scan

Choose your target (a single campground or a recreation area), arrival and departure dates, and minimum stay length.

By default, scans match **Any night**. To watch only specific nights of the week:

- Choose **Weekends** to match Friday and Saturday occupied nights (Sunday checkout for a 2-night stay).
- Choose individual weekdays in any combination (for example, Friday through Sunday) to match only consecutive stays on those nights.

Save the scan to monitor openings from your dashboard. You can edit dates, stay length, nights of the week, or site filters anytime without recreating the scan.

## Receive alerts

Configure alerts in your account settings using either **Pushover** or **ntfy**:

- **Pushover:** Enter your Pushover user key. Self-hosted instances also need a server-side application token from the instance maintainer.
- **ntfy:** Pick the instance's default server, `ntfy.sh`, or a custom ntfy server, subscribe to your topic in the ntfy app, and add an access token if your server requires one.

Use **Send test notification** in account settings to confirm delivery before relying on a scan.

By default, camply sends one summary alert per scan when new matching openings appear, linking directly to your scan results. Campsites disappear quickly—open the provider's booking link in the results to reserve your spot.

## Fresh self-hosted instances

If you just started your own instance and no campgrounds appear in Explore, open **Admin Operations** and run **Sync Providers**. See the [self-hosting guide](self-hosting/index.md) for setup and configuration.
