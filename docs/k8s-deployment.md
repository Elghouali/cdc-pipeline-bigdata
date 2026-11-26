# Experimental Kubernetes templates

Docker Compose is the supported integration-tested local deployment. The Helm and Kustomize resources are incomplete and must not be installed as a full production stack. Missing lakehouse and connector services, credential wiring, supervision, and network policies are tracked in [deployment readiness](DEPLOYMENT_READINESS.md).

## Isolated runtime validation

The [Kubernetes source and broker smoke workflow](../.github/workflows/kubernetes-smoke.yml) uses a disposable kind cluster with generated test credentials. It validates the complete rendered chart and Kustomize dev/prod overlays with server-side dry-run, then applies only the Helm PostgreSQL, Zookeeper and single Kafka broker resources with shared config and secrets. It checks logical WAL, the six-table publication, persistence across a PostgreSQL pod replacement, and Kafka message delivery. A successful run would validate that subset only. Review the Actions evidence before relying on it.

## Local rendering

From the repository root, use Helm 3 and supply all six required credential values from an external, protected values file plus the actual schema:

```bash
helm template cdc helm/cdc-pipeline --namespace cdc-pipeline \\
  -f /path/to/protected-values.yaml \\
  --set-file postgres.initSql=sql/init.sql \\
  --set-file postgres.seedSql=sql/seed.sql
kubectl kustomize k8s/overlays/dev
kubectl kustomize k8s/overlays/prod
````

The protected values file must supply postgres.password, minio.password, api.secretKey, api.adminPassword, mariadb.hivePassword and grafana.adminPassword. Never commit actual credentials. Rendered Secrets contain sensitive data. Source initialization occurs only on an empty PostgreSQL volume; this does not migrate an existing volume. Kafka supports one broker only; multi-broker replication and durable ZooKeeper are not implemented. Kustomize is render-only for runtime purposes and does not bootstrap the PostgreSQL schema yet. The full stack is not ready for EKS, GKE, AKS or a shared cluster.
