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

## Verified evidence — 2026-11-26

Integration run [45886441779](https://github.com/Elghouali/cdc-pipeline-bigdata/actions/runs/45886441779), commit `e8f8da13eca0a06960647127677c72e1a8513ea9`, passed the live lifecycle, recovery checks, business checks, reconciliation, and bounded benchmark. The 100-row source transaction took 0.161 s (reported 619.528 source rows/s). All 100 rows were first observed after commit in Bronze at 17.168 s, Silver at 47.897 s, and Gold at 68.989 s. These are sequentially polled batch completion observations, not end-to-end sustained throughput or percentile latency. Download the `cdc-smoke-evidence` artifact for the measured JSON. Manual integration dispatch now offers 100, 1000, and 5000-row bursts and records runner CPU/memory. Larger runs have not yet been verified.

CI run [45886441837](https://github.com/Elghouali/cdc-pipeline-bigdata/actions/runs/45886441837) passed all nine jobs, scanned both application images and dependencies, and published both application images. Frontend and repository dependency scan reports showed zero blocking or unfixed HIGH findings in the scanned scope. The API still has unfixed HIGH findings; full production release remains blocked.

### Kubernetes incremental validation

The new Kubernetes source and broker smoke workflow creates an isolated kind cluster. It validates all rendered resources against the Kubernetes API, applies only the Helm source/broker subset, checks the real SQL schema and six-table publication, checks PostgreSQL persistence across pod replacement, and sends/consumes one Kafka message. The full chart remains experimental; this workflow does not install or validate the lakehouse, API or frontend in Kubernetes. Results are pending until the workflow actually passes. No cloud resources are provisioned.

## Catalog extension (verification pending)

The source/broker smoke passed in [run 45894923792](https://github.com/Elghouali/cdc-pipeline-bigdata/actions/runs/45894923792). The next revision adds private MinIO bucket initialization, MariaDB persistence, locally built Hive Metastore, and a Trino coordinator with the existing read-only policy. The isolated workflow checks bucket anonymity denial, Hive catalog discovery and rejected schema writes. This is not yet a complete CDC workload in Kubernetes: Spark job supervision, Debezium registration, persistent checkpoints, API/frontend and monitoring remain outstanding. Kustomize remains render-only. The integration push runs now exercise 100/1000/5000-row isolated bursts; results must be read from completed runs before reporting performance.

## Kubernetes streaming extension — pending runtime evidence

The catalog smoke passed in [run 45898904887](https://github.com/Elghouali/cdc-pipeline-bigdata/actions/runs/45898904887). The extended chart adds optional Kafka Connect/Debezium, a replication-role and registration Job, and three separately supervised Kubernetes Deployments using the real Spark jobs. The initial test uses local[2] in each driver pod, not the standalone master/worker cluster. Recreate strategy and one replica per layer avoid concurrent writers during normal rolling updates. Bronze/Silver checkpoints remain in private S3 storage. The test stages drivers, runs the same insert/update/delete acceptance checks through Gold with kubectl, and uploads the evidence. This does not yet prove distributed executor scaling, driver restart recovery on Kubernetes, production security or application/monitoring deployment. API vulnerability remediation remains a separate release gate.

### Streaming smoke follow-up

Run [45900688836](https://github.com/Elghouali/cdc-pipeline-bigdata/actions/runs/45900688836) verified Debezium registration but timed out before Bronze table initialization. Archived cluster evidence shows Bronze entered CrashLoopBackOff (six restarts); prior diagnostics did not capture the Spark process exception. The chart specified an invalid AWS SDK v1 environment credential-provider class for Hadoop S3A; it now uses `com.amazonaws.auth.EnvironmentVariableCredentialsProvider` in both Spark and Hive. The Spark image also ensures a writable home for UID 185 and the driver supplies explicit Ivy paths. These address identifiable startup defects, not a confirmed root cause for that specific crash. The revised test stops after repeated driver failures and captures current/previous sanitized Spark logs, exit codes, restart counts and the last Trino readiness response. The new runtime test must pass before claiming streaming validation.

### Topic provisioning and CI scheduling correction

Run [45904578380](https://github.com/Elghouali/cdc-pipeline-bigdata/actions/runs/45904578380) confirmed Bronze table creation but its streaming queries failed with Kafka UnknownTopicOrPartitionException; Silver remained Pending with insufficient CPU. The connector registration Job now provisions each configured CDC topic with one partition and verifies the leader before connector registration. Existing partition counts are never changed. A dedicated values-ci.yaml reduces CPU requests only for the disposable kind environment while preserving normal defaults and memory limits. Stage readiness now requires live upstream pods, all expected tables and the initial synthetic customer in each layer, rather than empty table creation. Final Gold readiness is checked after the insert/update/delete test. Runtime validation remains pending.

## Recovery, application and monitoring extension — awaiting validation

Run [45906790633](https://github.com/Elghouali/cdc-pipeline-bigdata/actions/runs/45906790633) verified 17 medallion tables and the insert/update/delete lifecycle in kind. The next smoke scales down all three Spark deployments, queues an update while they are stopped, restores the pods without changing S3 checkpoints, and verifies one Bronze insert/update plus correct Silver/Gold state and subsequent deletion. The API runs non-root with a separate schema and non-superuser database login; the console smoke verifies login, protected events, read queries, actual Spark driver state and absence of source SELECT permission. Prometheus scrapes the API's real per-pod telemetry; Grafana provisions a dashboard, with four Prometheus alert rules loaded. Monitoring storage is ephemeral; Alertmanager delivery, persistent history, TLS, CNI enforcement and full disaster recovery are not asserted. All new acceptance checks must finish before reporting these milestones as verified.

### Separate distributed and release gates

A dedicated standalone Spark kind workflow compares the same deterministic 32-partition CPU workload with one and two real worker pods; it requires distinct remote executor hosts and identical checksums. Wall-clock results are evidence only, not a guaranteed speedup or distributed CDC capacity measurement. The strict release-security workflow scans all 16 listed runtime/candidate images and fails for every HIGH or CRITICAL result, including those without fixes. The Debian API runtime now avoids curl and runs as an unprivileged UID. An Alpine alternative is evaluated independently with import/unit tests and a strict scan; it is not the default until proven compatible and less vulnerable. Image IDs/repository digests are recorded; digest locking, TLS and full image provenance are still outstanding. The optional ingress-only NetworkPolicy is rendered in CI but disabled by default: kind's default CNI does not establish policy enforcement. Validate allow/deny flows with a policy-capable CNI before production use.
