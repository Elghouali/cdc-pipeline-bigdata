# Deployment readiness

## Supported deployment

Docker Compose is the integration-tested local stack, not an Internet-facing production service. The frontend uses a multi-stage Node build and unprivileged Nginx on port 3000; `make dev` keeps the Vite development server. Same-origin /api and /auth proxy paths preserve authorization headers and disable response buffering for SSE. Nginx resolves the configured API service at startup; restart the frontend if the API container IP changes. No public exposure is enabled.

CI builds both application images and publishes SHA and latest tags after test, render and scanner jobs succeed. Use SHA or digest references for controlled deployments. Trivy HIGH/CRITICAL runtime and dependency results are published as JSON artifacts. Development image publication now fails on any CRITICAL or any HIGH with a listed fix. Unfixed HIGH findings are printed and remain production release blockers: run the same gate with --release to enforce zero HIGH/CRITICAL findings in the scanned scope. No claim is made that infrastructure images are scanned or that current findings are zero. Version tags are not immutable digests.

## Benchmark methodology

The integration runner inserts a unique, bounded customer burst (100 rows by default) in one PostgreSQL transaction. It measures source transaction time, source insert throughput and first observed completion of each layer, then cleans up only the fixture and reconciles active keys. Sequential polling introduces observation delay and does not measure event-level p50/p95/p99 or sustained capacity. The JSON artifact is evidence, not a production SLO. For a fuller load test, repeat at several sizes with recorded CPU/RAM, cold/warm runs, sustained concurrent writes, per-event timestamps and fault injection.

## Kubernetes status

Helm and Kustomize rendering are checked in CI. Templates use correct application image names, frontend port, API credential injection and Spark image family. API HPA is disabled until shared authentication throttling and cache design exist. Kustomize overlays use the same namespace and service names; they are alternatives, not simultaneous deployments. The chart still lacks complete MinIO initialization, MariaDB/Hive, Trino, Kafka Connect, source seed/replication, job supervision, credential wiring, runtime telemetry volume, network policies, and cluster-level security. There is no verified Kubernetes install, no automatic production deployment and no released v1.0. A complete cluster implementation and real deployment test are required before marking this done. Do not install experimental manifests in a shared/production environment.

## Remaining release gates

- Review vulnerability results; remediate critical/high issues and pin trusted images.
- Deploy and verify a complete isolated Kubernetes topology, with PVCs, per-service credentials, restricted network and tested configuration.
- Establish measured sustained throughput, p50/p95/p99 latency and recovery SLOs.
- Validate coordinated off-host full-stack backups, safe compaction, credential rotation, source reconciliation, and disaster recovery.
- Record release evidence before tagging a production-ready version.

## Vulnerability remediation baseline

CI run 45877293192 found 60 HIGH API and 15 HIGH / 5 CRITICAL frontend package findings. The five critical entries affected Alpine nginx (four CVEs) and brotli-libs (one CVE), with fixed versions listed. Other fixable findings included Alpine OS libraries, Debian libzstd1, and vendored jaraco.context/wheel in setuptools. Both runtime builds now refresh OS security packages; the API production stage removes unnecessary packaging build tools and checks dependency consistency and imports. The frontend restores the unprivileged runtime user after package upgrades. CI pulls current base images before building and blocks publication on critical or fixable high findings; subsequent scans must confirm remediation. Unfixed Debian findings cannot be assumed fixed by upgrading, and their production risk still requires remediation or a documented security review. Reports are uploaded even when the gate blocks publishing. Infrastructure image scanning and digest pinning remain outstanding.

### Follow-up on enforced scan

CI run 45880392103 passed integration but correctly blocked publication: all API fixable HIGH findings and all frontend findings except six Nginx CVEs were removed. The API still has 57 HIGH findings without a listed fix. The vendor Nginx image retained nginx 1.30.6-r1 after a general package upgrade. The frontend runtime now installs nginx >= 1.30.7-r0 from Alpine's signed stable repositories, uses an explicit non-root configuration with writable temporary paths, and substitutes only API_UPSTREAM. The minimum package version is a build requirement, not an exemption or a guarantee of zero vulnerabilities. CI must demonstrate availability of the patched package, successful application proxying, and a passing scan before publication. If the package is unavailable the build fails; do not fall back to the vulnerable version. Full production release remains blocked by the API's outstanding HIGH findings.
