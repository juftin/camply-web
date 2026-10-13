# camply ⛺️

The Campsite Finder — Find campsites at sold-out campgrounds.

`camply` is a standalone CLI tool that monitors campsite booking providers (such as Recreation.gov) and notifies you when openings become available.

## Installation

```bash
pip install camply
```

## Quickstart

### 1. Search for Campgrounds

```bash
camply campgrounds --search "Glacier Basin"
```

### 2. Search for Campsite Availability

```bash
camply campsites --campground 232463 --start-date 2026-08-01 --end-date 2026-08-05
```

### 3. Continuous Monitoring with Notifications

Configure your Pushover credentials:

```bash
camply configure --pushover-user-key YOUR_KEY --pushover-app-token YOUR_TOKEN
```

Then start continuous monitoring:

```bash
camply campsites --campground 232463 --start-date 2026-08-01 --end-date 2026-08-05 --continuous --notifications pushover
```

## Documentation

For full documentation and advanced features, visit [github.com/juftin/camply](https://github.com/juftin/camply).
