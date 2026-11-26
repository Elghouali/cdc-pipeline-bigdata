# Security hardening — phase 1A

## Local containment

- All Compose published ports are bound to loopback; internal containers still communicate over the Compose network.
- Use SSH forwarding for remote administration. Do not make service ports public.
- The initializer removes anonymous access from the warehouse. On an existing deployment, rerun the initializer with authorized storage credentials and verify that anonymous listing and object reads are denied. Existing credentials are not rotated by this change.
- The SSE endpoint validates JWTs and sends event metadata only. Streams are time-bounded; the frontend uses authenticated fetch rather than putting credentials in the URL. It reconnects on a bounded delay. The feed is best effort, not a durable consumer.
- The workflow asserts anonymous bucket listing denial, unauthenticated SSE rejection and loopback port bindings. Unit tests assert metadata-only payloads.

## Remaining risks

Trino is still not an engine-enforced read-only boundary. Local authenticated query users can access data unless proper Trino authorization and masking are deployed. Default secrets, source database privileges, internal network segmentation, TLS, query quotas, dependency scanning, and shared event fan-out are outstanding. The Helm and Kustomize scaffolds are not hardened by these Compose changes. No external exposure or production security guarantee is made.

## Phase 1B — local authorization and secrets

Trino now mounts file-based authorization and makes the Iceberg catalog read-only for all identities. The API service identity cannot read raw Bronze payload columns and masks selected names and emails. Direct Trino access is still trusted-local only: Trino identities are not authenticated, metadata and other indirect exposure paths need a separate review, and a local caller can select a different identity. Spark writes directly via Iceberg and is unaffected by Trino write denial. SQL API limits are 10,000 rows and 60 seconds, with a two-minute engine deadline. The login guard is per process and not a substitute for a distributed gateway rate limiter.

For existing deployments, add a new random DEBEZIUM_PASSWORD to .env, update JWT/admin configuration to non-placeholder values, recreate the PostgreSQL and Kafka Connect containers without removing volumes, then run make connector-register. The script sets the replication role password and PUTs connector config instead of deleting the connector; offsets and slot are retained. The Kafka Connect worker resolves the password from its environment. Rotate any previously exposed credentials separately. The existing admin user's stored password is not reset by a changed environment variable. API and other database roles, root object-storage credentials, authenticated Trino transport, distributed throttling and secret-manager integration remain outstanding. Environment variables are not a production secret vault.
