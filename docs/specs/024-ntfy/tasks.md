# Tasks

- [x] Persist and validate per-user provider choice and settings; migrate existing accounts.
- [x] Implement ntfy provider and route both delivery adapters by user selection.
- [x] Add Profile controls and regenerate API types.
- [x] Test settings, delivery, and migrations; update documentation.

- [x] Configure private publish and public subscription defaults at deployment level, support user custom-server overrides, and test fallback, endpoint privacy and delivery in both runtimes.

- [x] Add a server dropdown for the configured application server, ntfy.sh and a user-provided URL, with private publish settings hidden.

- [x] Show only the selected provider’s settings, save preferences together, and support editable user-ID-prefix topics with duplicate validation and a follow-up migration.

- [x] Prefix generated seven-character user-ID topics with `camply-` and migrate prior generated defaults while preserving custom topics.

- [x] Preview the complete subscription URL live from current fields, including generated topics and unsaved server/topic edits.

- [x] Add clipboard buttons for the selected public server URL, editable topic and live subscription URL, with success/error feedback and empty-value handling.
