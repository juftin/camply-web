# Night-selection contracts

## Saved scan interface

Existing create, list, detail and PATCH routes gain `allowed_weekdays`, a nonempty list of strict integers from 0 (Monday) to 6 (Sunday). The field is optional on create/PATCH, normalized by sorting and removing duplicates, and always present on responses. Explicit null, empty lists, out-of-range values, booleans, strings and fractions return validation errors. Creation omission means all seven; PATCH omission means preserve. An explicit `[0, 1, 2, 3, 4, 5, 6]` removes a restriction. `[4, 5]` means weekend nights.

Creating or changing date/night/stay criteria returns 422 with actionable text if the remaining date range cannot contain the requested consecutive stay. Validate merged PATCH values before mutation. Unknown campgrounds, ownership, duplicate subscriptions, and account restrictions keep their existing responses. Merely observing expiration or toggling activity does not trigger search-criteria validation.

## Web interaction

Label the control “Nights of the week”; provide seven named, keyboard-operable pressed-state buttons. Defaults select all seven. “Weekends” replaces selection with Friday/Saturday; “Any night” selects all seven. Individual buttons can modify either selection. Explain that these are occupied nights, and Friday/Saturday can check out Sunday. Empty selection and impossible date/day/minimum combinations show actionable errors. Quick-date buttons alter only dates. Saved night preferences populate editing and appear on cards and details, with “Any night” for unrestricted preferences.

## Matching and delivery

Interpret weekdays on booking calendar dates, filter date boundaries/expiration/selection before grouping, and never combine sites or excluded nights. Results, counts, direct and summary alert detection and delivery use the same rule. Both runtimes revalidate queued notifications against current scan ownership, target linkage and preferences. No matching opening means skip. Shared polling and raw observations remain independent of night preferences.

## CLI

Retain `--weekends` (adds Friday and Saturday) and repeatable case-insensitive `--day`, including existing full names and abbreviations. No selector allows all days. `--weekends --day Sunday` unions Friday/Saturday/Sunday. Date pairs remain independent of weekday selection. CLI exact stays and web minimum stays differ only in presentation, not eligible-night semantics. No external CLI alert channel is introduced.
