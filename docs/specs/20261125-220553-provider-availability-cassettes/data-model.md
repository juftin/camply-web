# Test Data for Provider Availability Cassettes

## Provider scenario

A test case identifies a concrete provider by registry ID and has a stable, unique case key within that provider. Its inputs are the native campground ID, arrival, checkout, equipment category and vehicle length when applicable, and any provider-specific public options. Campground IDs stay opaque strings.

- Checkout is after arrival. Expected nights are within `arrival <= night < checkout`.
- The expected result contains at least one known campsite ID, its expected nights, and a normalized name or type.
- An equipment case has the expected compatible site and, where matching is supported, evidence for a known available incompatible site and the reason it is excluded.
- Each registered provider has at least two distinct positive search inputs. Use distinct supported equipment requests where possible. Document capability gaps and vary the campground or dates when a second equipment request is unavailable.

## Cassette

Each scenario references its own checked-in cassette. Match the HTTP method, origin, path, query, and any body fields that identify the provider, campground, dates, or applicable upstream options. Retain the response structure required by camply. Keep credentials, personal data, and live session material out of the committed file.

A refresh candidate remains separate until the selected case passes strict offline replay and the candidate is reviewed. Replace the search inputs, expected results, verification date, and cassette together.

## Refresh entry

For each scenario, record its case key, public booking URL, campground name and native ID, search options, last verified date, and test and cassette locations. Include the provider-specific steps to find a suitable open stay or choose a replacement. Track a deferred refresh without changing the last successful verification date.
