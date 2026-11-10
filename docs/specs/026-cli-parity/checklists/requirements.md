# Specification readiness: CLI parity

- [x] Pinned legacy release and “v1” terminology are explicit.
- [x] All eight core commands, optional TUI, root behavior and search option aliases are inventoried with primary-source links.
- [x] YAML defaults/precedence, environment inputs and state formats are covered.
- [x] All 19 provider names, 17 GoingToCamp selectors and 10 notification channels have replacement dispositions.
- [x] Current code foundations and missing capabilities are distinguished.
- [x] Prioritized journeys, edge cases, requirements and measurable acceptance outcomes are defined.
- [x] Intentional changes are separated from deferred/blocked parity gaps.
- [x] Shared-engine reuse accounts for current peer import boundaries and optional dependencies.
- [x] Initial tasks cover only current-provider discovery, campground availability and provider/matching reuse; all D01–D13 TODOs are excluded from initial acceptance gates.
- [x] Search forever is the intended default; legacy mode switches and detailed lifecycle semantics remain open for later brainstorming.
- [x] `--notify-first-try` and both offline-search flags are explicitly deferred.
- [x] Permits and Rich-click are tracked explicitly without claiming unverified legacy permit support.
- [x] Initial command/option/default/precedence contract matches the approved tree, including exact campground lookup and complete area expansion.
- [x] Installed-command tests must cover real argument parsing, displayed stays, continued checking after a match and cancellation cleanup; internal tests alone cannot pass acceptance.
- [x] Initial CLI is console-only: Pushover, notification flags/credentials and test-notifications are deferred; no new recipient environment variable is required.
- [x] Implement and execute initial runtime acceptance checks, including installed base wheel/sdist commands on Python 3.11/3.14. This certifies the initial scope; D01–D13 remain deferred.
