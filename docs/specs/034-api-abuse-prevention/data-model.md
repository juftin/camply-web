# Quota Data Model

| Entity  | Fields and constraints                                                                                                                                                                                             |
| ------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Policy  | Stable server-defined operation scope, positive maximum request count, positive window in seconds, and client IP or verified account identity                                                                      |
| Subject | Canonical client network identity or server-resolved account ID. Trusted gateway IP requires verified provenance. Direct mode uses the ASGI peer. Normalize IPv4-mapped IPv6 as IPv4 and group native IPv6 by /64. |
| Counter | Keyed by policy and subject. Non-negative count and positive expiry within the policy window. Expiry does not move when a request increments the counter.                                                          |

The first request opens a window and increments its counter. Requests through the threshold are admitted. Further requests receive the remaining wait in seconds. A previously inactive subject can start a new window after expiry. In-memory storage is capacity bounded. Distributed updates and expiry use one atomic operation. The existing user, session and scan schemas do not change.
