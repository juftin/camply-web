# DESIGN_NOTIFICATIONS: Notification Architecture

This document defines the architecture for the notification layer in `camply`, focusing on a standardized interface, multiple provider support, and asynchronous delivery.

## Standalone delivery

Standalone stores delivery intents in the same transaction as successful scan results and uses one asynchronous outbox consumer. It commits `sending` and increments the attempt count before HTTP; it records `sent` only after explicit Pushover acceptance. Missing application/user credentials or current ineligibility produce a skip. Invalid payloads, malformed acceptance responses, and permanent upstream rejection fail. Transport errors, HTTP 429, and server failures retry after 120 seconds, with three retries and four total sends. Interrupted attempts retain their consumed budget and are retried on startup unless exhausted.

Standalone honors the shared summary/direct setting. Summaries persist the matching site snapshots, then reapply current filters and dates to each site and recalculate the count before sending. No remaining match produces a skip. Direct alerts use the same filtering helper as the results API, including only qualifying consecutive stay blocks. SQLite lock contention during acknowledgment retries the database write rather than sending a second request; other storage failures make readiness fail.

Before every send, validate current owner/scan/target linkage, active scan, enabled user, optional invitation, current filters, credentials, and dates. The date cutoff is the current UTC calendar day: remove earlier nights and nights outside the current target, then reapply the minimum consecutive stay requirement. Include only eligible dates in the delivered payload. Queued intents contain no credentials; outcomes store allowlisted categories rather than raw errors. Terminal records are pruned after 24 hours; pending/retry rows persist.

A process failure after upstream acceptance but before recording `sent` can produce a duplicate; exactly-once external delivery is not claimed. Local operational attempt history is separate, in memory, capped at 1,000 entries/24 hours. Distributed mode retains its Celery notification adapter and existing task contract.

## 🎯 Architecture Goals

1. **Standardization**: All notification channels must implement a unified `BaseNotificationProvider`.
2. **Asynchronous Delivery**: Notifications are handled by dedicated Celery tasks to avoid blocking the scanning worker.
3. **User-Centric**: Users can configure their own notification preferences and keys (e.g., Pushover user key, Webhook URL).
4. **Resilience**: Implement retries and error tracking for failed notifications.

---

## 🏗️ Core Interface: `BaseNotificationProvider`

Every notification channel must inherit from this ABC.

```python
class BaseNotificationProvider(ABC):
    @property
    @abstractmethod
    def id(self) -> str:
        """Unique slug: e.g., 'pushover', 'email', 'webhook'"""
        pass

    @abstractmethod
    async def send_alert(self, user_config: Dict[str, Any], payload: NotificationDTO) -> None:
        """
        Deliver the notification to the user using their specific configuration.
        """
        pass
```

---

## 📦 The Unified DTO: `NotificationDTO`

The data structure sent to the notification providers.

- `title`: `String` (e.g., "Campsite Available: Yosemite")
- `message`: `String` (Detailed description including dates and site info)
- `booking_url`: `String` (Camply scan-results link in summary mode; provider booking link in direct mode)
- `url_title`: `String` (`View campsites` for summaries; defaults to `Book Now` for direct and previously queued payloads)
- `park_name`: `String`
- `campsite_name`: `String`
- `start_date`: `Date`
- `end_date`: `Date`
- `metadata`: `Dict[String, Any]` (Provider-specific raw attributes)

---

## 🚀 Notification Workflow

### 1. Detection

The **Smart Poller** identifies a match between a `ScanResult` and a `UserScan`.

### 2. Dispatch

The worker defaults to **one summary per saved scan per check** containing new matching openings. It enqueues `camply.notifications.send_pushover_notification` with the user ID, serialized DTO and scan ID. The summary counts newly opened matching sites and links to `{CAMPLY_APP_URL}/dashboard/scans/{scan_id}#results`, preserving any frontend path prefix. Separate saved scans receive separate summaries.

`CAMPLY_NOTIFICATION_MODE=direct` preserves individual site alerts with provider booking links for local deployments. `summary` is the default in every environment. Both modes apply the same site preferences and minimum consecutive stay as the API. Newly available nights outside qualifying stay blocks do not trigger alerts. Unchanged openings remain silent; openings can alert again after disappearing and returning.

Before storing results or detecting new openings, the worker discards nights before the current UTC date and outside the target's check-in/check-out interval. Minimum stays are evaluated on the remaining nights, matching API expiration, so expired nights cannot cause an alert that opens to no qualifying results.

Snapshots retain campsite names, types and electric/accessibility attributes, so opening a summary requires no live provider request. The list represents the latest successful check, not a permanent history; availability may change before booking.

### 3. Delivery

The `send_notification_task` does the following:

1. Fetches the user's `pushover_token` or other configured provider keys from the DB, revalidates scan ownership and active state, and skips suspended users.
2. Selects the appropriate `BaseNotificationProvider`.
3. Calls `provider.send_alert(user_config, notification_dto)`.
4. Records successful delivery in metrics. A `notification_history` table remains optional/future work.

See the [implementation plan](../specs/009-campsite-alerts/plan.md) and [configuration](../operations/CONFIGURATION.md) for deployment settings and migration requirements.

---

## 🛠️ Supported Providers (Roadmap)

1. **Pushover (MVP)**:
   - _Config_: `user_key`
   - _Status_: High Priority
2. **Webhooks**:
   - _Config_: `webhook_url`
   - _Status_: High Priority (Discord, Slack, etc.)
3. **Email (SMTP)**:
   - _Config_: `email_address`
   - _Status_: Medium Priority
4. **Apprise**:
   - _Config_: `email_address`
   - _Status_: Medium Priority (Universal wrapper for 50+ services)
5. **Ntfy**:
   - _Config_: `topic_url`
   - _Status_: Medium Priority

---

## 🔒 Security & Performance

- **Secrets Management**: User notification tokens must be handled securely in the database.
- **Rate Limiting**: Implementation of provider-specific rate limiting (e.g., Twilio/SMS limits) to prevent excessive costs or API bans.
- **Failover**: If a primary notification method fails, we can optionally fall back to a secondary method if configured.
