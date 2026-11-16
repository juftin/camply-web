# Notification Architecture

camply separates availability detection from alert delivery so provider checks never block on outbound HTTP calls and every pending alert is revalidated right before sending.

## Interface and payload

All notification channels implement `BaseNotificationProvider` under `camply.notifications` and accept a `NotificationDTO` (`title`, `message`, `booking_url`, `url_title`, `park_name`, `campsite_name`, `start_date`, `end_date`, `metadata`).

`CAMPLY_NOTIFICATION_MODE` controls alert granularity across both runtimes:

- **`summary` (default):** Sends one alert per saved scan when new matching sites open, linking to `{CAMPLY_APP_URL}/dashboard/scans/{scan_id}#results`.
- **`direct`:** Sends individual site alerts pointing directly to the provider's booking URL.

## Supported channels

Each user chooses either **Pushover** (default) or **ntfy** in account settings:

- **Pushover:** Requires a deployment `PUSHOVER_APP_TOKEN` and the user's Pushover user key.
- **ntfy:** Assigns each user an editable unique topic (`camply-<7-char-id>`), using `CAMPLY_NTFY_SUBSCRIPTION_URL` (default `https://ntfy.sh`) for user subscriptions and optional `CAMPLY_NTFY_PUBLISH_URL` for private server-side publishing. Users can also supply a custom server URL and optional bearer token.

`POST /api/me/notifications/test` validates unsaved settings and sends a single test message directly through the chosen channel without creating a scan or outbox record.

## Pre-send revalidation and delivery paths

Before sending any queued alert, both standalone and distributed adapters recheck scan ownership, active status, user eligibility, current UTC date cutoff, `allowed_weekdays`, `min_stay_length`, and target linkage (`scan_revision` for area scans). If no qualifying stay remains, the delivery is skipped cleanly.

- **Standalone outbox:** Inserts `notification_outbox` intents atomically in the same transaction as `scan_results`, retries transient failures after 120 seconds (up to 4 total attempts), and prunes terminal rows after 24 hours.
- **Distributed tasks:** Enqueues Celery tasks (`camply.notifications.send_pushover_notification` or `send_ntfy_notification`).
- **Area scan coalescing:** `area_alerts.py` batches new recreation-area openings under `delivery_key="area-summary"` across a 5-second window (`area-outbox` loop or Beat schedule) so multi-campground rounds produce one clean summary instead of a flood of messages.
