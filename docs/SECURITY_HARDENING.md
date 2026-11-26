# Security hardening — phase 1A

## Local containment

- All Compose published ports are bound to loopback; internal containers still communicate over the Compose network.
- Use SSH forwarding for remote administration. Do not make service ports public.
- The initializer removes anonymous access from the warehouse. On an existing deployment, rerun the initializer with authorized storage credentials and verify that anonymous listing and object reads are denied. Existing credentials are not rotated by this change.
- The SSE endpoint validates JWTs and sends event metadata only. Streams are time-bounded; the frontend uses authenticated fetch rather than putting credentials in the URL. It reconnects on a bounded delay. The feed is best effort, not a durable consumer.
- The workflow asserts anonymous bucket listing denial, unauthenticated SSE rejection and loopback port bindings. Unit tests assert metadata-only payloads.

## Remaining risks

Trino is still not an engine-enforced read-only boundary. Local authenticated query users can access data unless proper Trino authorization and masking are deployed. Default secrets, source database privileges, internal network segmentation, TLS, query quotas, dependency scanning, and shared event fan-out are outstanding. The Helm and Kustomize scaffolds are not hardened by these Compose changes. No external exposure or production security guarantee is made.
