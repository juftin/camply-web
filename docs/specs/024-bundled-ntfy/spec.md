# Bundled ntfy and semantic chart releases

Deploy optional ntfy alongside Camply, enabled by default. Derive ntfy.example.com from example.com for Ingress and Gateway API, with explicit hostname/base URL and TLS overrides. Preserve home-ops public anonymous subscriptions and cluster-only publishing. Persist cache and attachments with one non-root replica and Recreate updates. Disabling ntfy must remove its resources.

Publish charts only for stable releases under the unprefixed semantic version, selecting the matching v-prefixed application image. Do not publish chart aliases or main-build charts. Container image publication remains unchanged.
