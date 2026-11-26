# Experimental Kubernetes templates

Docker Compose is the supported integration-tested local deployment. The Helm and Kustomize resources are incomplete and must not be installed as a full production stack. Missing lakehouse and connector services, credential wiring, supervision, and network policies are tracked in [deployment readiness](DEPLOYMENT_READINESS.md).

## Isolated runtime validation

The [Kubernetes source and broker smoke workflow](../.github/workflows/kubernetes-smoke.yml) uses a disposable kind cluster with generated test credentials. It validates the complete rendered chart and Kustomize dev/prod overlays with server-side dry-run, then applies only the Helm PostgreSQL, Zookeeper and single Kafka broker resources with shared config and secrets. It checks logical WAL, the six-table publication, persistence across a PostgreSQL pod replacement, and Kafka message delivery. A successful run would validate that subset only. Review the Actions evidence before relying on it.

## Local rendering

From the repository root, use Helm 3 and supply all seven required credential values from an external, protected values file plus the actual schema:

```bash
helm template cdc helm/cdc-pipeline --namespace cdc-pipeline \\
  -f /path/to/protected-values.yaml \\
  --set-file postgres.initSql=sql/init.sql \
  --set-file trino.accessRules=security/trino-access-control.json \\
  --set-file postgres.seedSql=sql/seed.sql
kubectl kustomize k8s/overlays/dev
kubectl kustomize k8s/overlays/prod
````

The protected values file must supply postgres.password, minio.password, api.secretKey, api.adminPassword, mariadb.hivePassword, mariadb.rootPassword and grafana.adminPassword. Never commit actual credentials. Rendered Secrets contain sensitive data. Source initialization occurs only on an empty PostgreSQL volume; this does not migrate an existing volume. Kafka supports one broker only; multi-broker replication and durable ZooKeeper are not implemented. Kustomize is render-only for runtime purposes and does not bootstrap the PostgreSQL schema yet. The full stack is not ready for EKS, GKE, AKS or a shared cluster.

The [source/broker smoke run](https://github.com/Elghouali/cdc-pipeline-bigdata/actions/runs/45894923792) passed. The extended smoke adds private object storage, MariaDB, Hive and Trino validation; runtime results are pending. Trino 435 supports environment-backed secrets (https://trinodb.github.io/docs.trino.io/435/security/secrets.html). The custom Hive image is built from hive/Dockerfile and loaded into kind; other clusters require a trusted registry image. Do not expose any experimental services publicly.

### Streaming mode (experimental)

For rendering the streaming subset, supply `connect.enabled=true`, `streaming.enabled=true`, `--set-file connect.config=config/debezium-connector.json` and an additional protected `connect.password` value. Build `spark/Dockerfile` from repository root and configure `streaming.image` to the image in your trusted registry. The smoke workflow uses a locally loaded kind image. Streaming mode replaces the standalone Spark master/worker templates with a single local-mode pod per layer; it is not a distributed Spark deployment. Start Bronze, then Silver once all Bronze tables exist, then Gold once all Silver tables exist. The disposable CI workflow orchestrates this; full Helm install is not supported. Verify the latest run before relying on the path.

The CI-only resource overlay `helm/cdc-pipeline/values-ci.yaml` is not a production sizing recommendation. The connector registration Job provisions CDC topics before registering the connector and refuses unexpected partition counts; do not resize existing CDC topics without an explicit replay/migration plan. The staged CI test waits for actual synthetic fixture records, not just table existence.

### Experimental application and observability

Supply a separate protected `api.databasePassword`; the API DB bootstrap job provisions the dedicated schema and login. Start it before the API. For existing installations, migrating API accounts/alerts from public to api_runtime is a separate operator action; no automatic data migration is performed. The local-pod mode uses driver REST endpoints and Gold refresh sidecar; no standalone Spark history is available. Enable `monitoring.enabled=true` for internal Prometheus and Grafana services with ephemeral data and provisioned dashboard. No public Ingress is enabled. Use a protected port-forward only in the disposable test cluster.

The isolated distributed Spark workflow uses the standalone master/worker templates and a synthetic CPU benchmark; it does not replace the local-pod CDC acceptance path. Optional ingress policies (security.networkPolicy.enabled) are only for the local streaming chart; test on a capable CNI, keep a dedicated namespace, and explicitly configure external ingress/egress if required. The release-security workflow is intentionally strict and independent of development publication; a red release gate means production deployment is not approved.
