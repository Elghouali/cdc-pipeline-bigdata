# Kubernetes Deployment Guide

This guide covers deploying the CDC Medallion Lakehouse Pipeline to any
Kubernetes cluster (EKS, GKE, AKS, or on-prem) using either the Helm chart
or the Kustomize overlays.

## Prerequisites

- A Kubernetes cluster (v1.25+)
- `kubectl` configured to talk to the cluster
- `helm` v3.10+ (for the Helm path)
- A default `StorageClass` (or one supplied via `global.storageClass`)
- For HPA: the `metrics-server` add-on installed in the cluster
- For Ingress: an ingress controller (e.g. `ingress-nginx`)

## Option A — Helm

The Helm chart lives in `helm/cdc-pipeline`. Three values are required and
have no defaults (the chart fails fast if they are missing):

- `postgres.password`
- `minio.password`
- `api.secretKey`

### Install

```bash
helm install cdc-pipeline helm/cdc-pipeline \
  --namespace cdc-pipeline --create-namespace \
  --set postgres.password=CHANGE_ME_PG \
  --set minio.password=CHANGE_ME_MINIO \
  --set api.secretKey=CHANGE_ME_APISECRET
```

For real environments, store secrets in a values file encrypted with
[helm-secrets](https://github.com/jkroepke/helm-secrets) instead of `--set`:

```bash
helm secrets install cdc-pipeline helm/cdc-pipeline \
  --namespace cdc-pipeline --create-namespace \
  -f secrets.enc.yaml
```

### Enable Ingress

```bash
helm upgrade cdc-pipeline helm/cdc-pipeline \
  --reuse-values \
  --set ingress.enabled=true \
  --set ingress.host=cdc.example.com \
  --set ingress.tls.enabled=true
```

### Enable Pod Disruption Budgets

```bash
helm upgrade cdc-pipeline helm/cdc-pipeline \
  --reuse-values --set podDisruptionBudget.enabled=true
```

### Upgrade

```bash
helm upgrade cdc-pipeline helm/cdc-pipeline --reuse-values
```

### Uninstall

```bash
helm uninstall cdc-pipeline --namespace cdc-pipeline
```

> PersistentVolumeClaims are intentionally **not** removed on uninstall.
> Delete them manually if you want to discard data:
> `kubectl delete pvc -n cdc-pipeline -l app.kubernetes.io/part-of=cdc-pipeline`

### Render without installing

```bash
helm template cdc-pipeline helm/cdc-pipeline \
  --set postgres.password=x --set minio.password=x --set api.secretKey=x
```

## Option B — Kustomize

Plain manifests live in `k8s/base`, with environment overlays in
`k8s/overlays/dev` and `k8s/overlays/prod`.

Kustomize does not template secrets — create the `cdc-secrets` Secret first:

```bash
kubectl create namespace cdc-pipeline
kubectl -n cdc-pipeline create secret generic cdc-secrets \
  --from-literal=POSTGRES_PASSWORD=CHANGE_ME_PG \
  --from-literal=MINIO_ROOT_PASSWORD=CHANGE_ME_MINIO \
  --from-literal=API_SECRET_KEY=CHANGE_ME_APISECRET \
  --from-literal=MARIADB_HIVE_PASSWORD=hive \
  --from-literal=GRAFANA_ADMIN_PASSWORD=admin
```

### Deploy the dev overlay

```bash
kubectl apply -k k8s/overlays/dev
```

### Deploy the prod overlay

The prod overlay scales replicas up, raises resource limits, and adds
PodDisruptionBudgets for postgres and kafka.

```bash
kubectl apply -k k8s/overlays/prod
```

### Preview rendered manifests

```bash
kubectl kustomize k8s/overlays/dev
```

## Verifying the deployment

```bash
kubectl get pods -n cdc-pipeline
kubectl get svc -n cdc-pipeline
kubectl get hpa -n cdc-pipeline
```

All pods should reach `Running` / `Ready`. Startup order is handled by
init containers (Kafka waits for Zookeeper, Spark workers wait for the
Spark master).

## Notes and scaling

- Kafka runs as a single-broker StatefulSet for simplicity. To run a real
  multi-broker cluster, raise `kafka.replicas`, give each pod a distinct
  `broker.id` derived from the pod ordinal, and increase the replication
  factor of the internal offsets/transaction-state topics.
- Spark workers, the API, and the frontend are horizontally scalable.
  The API and frontend ship with a HorizontalPodAutoscaler
  (CPU target 70%, 1-5 replicas).
- Persistent data uses `ReadWriteOnce` PVCs. On managed clouds this maps
  to EBS / Persistent Disk / Azure Disk via the default StorageClass.
