# CDC Pipeline — Oracle Cloud VM Deployment Guide

Deploy the full CDC pipeline on an Oracle Cloud Infrastructure (OCI) Ubuntu instance.

---

## Prerequisites on your VM

SSH into the VM first:

```bash
ssh ubuntu@instance-20260513-2243-bigdata-g15
```

### 1. Install Docker Engine

```bash
sudo apt-get update
sudo apt-get install -y ca-certificates curl gnupg lsb-release

sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
  | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
  https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" \
  | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Allow your user to run Docker without sudo
sudo usermod -aG docker ubuntu
newgrp docker

# Verify
docker --version
docker compose version
```

### 2. Install Git and Make

```bash
sudo apt-get install -y git make
```

---

## Open Ports in Oracle Cloud

By default OCI blocks everything except SSH. Open ports in two places.

### A — OCI Security List (web console)

Go to: **OCI Console → Networking → Virtual Cloud Networks → your VCN → Security Lists → Default**

Add an **Ingress Rule** for each port:

| Port | Protocol | Service |
|------|----------|---------|
| 3000 | TCP | Frontend |
| 8000 | TCP | API |
| 8080 | TCP | Trino UI |
| 8083 | TCP | Kafka Connect |
| 8085 | TCP | Spark Master UI |
| 8088 | TCP | Superset |
| 9001 | TCP | MinIO Console |
| 3001 | TCP | Grafana |
| 9090 | TCP | Prometheus |

### B — Ubuntu iptables (required — Oracle images block all non-SSH ports by default)

```bash
for port in 3000 8000 8080 8083 8085 8088 9001 3001 9090; do
  sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport $port -j ACCEPT
done

# Persist across reboots
sudo apt-get install -y iptables-persistent
sudo netfilter-persistent save
```

---

## Deploy the Project

### 1. Clone the repository

```bash
git clone <your-repo-url> cdc-pipeline
cd cdc-pipeline
```

### 2. Create and fill the `.env` file

```bash
cp .env.example .env
nano .env
```

Minimum required changes — replace every `change_me_*` value and add your VM's public IP to `CORS_ORIGINS`:

```dotenv
POSTGRES_USER=postgres
POSTGRES_PASSWORD=<strong-password>

MINIO_ROOT_USER=minioadmin
MINIO_ROOT_PASSWORD=<strong-password>

MARIADB_ROOT_PASSWORD=<strong-password>
MARIADB_HIVE_PASSWORD=<strong-password>

# Generate: python3 -c "import secrets; print(secrets.token_hex(32))"
SUPERSET_SECRET_KEY=<generated-value>
SUPERSET_ADMIN_PASSWORD=<strong-password>

# Generate: openssl rand -hex 32
API_SECRET_KEY=<generated-value>
API_ACCESS_TOKEN_EXPIRE_MINUTES=60
API_ADMIN_PASSWORD=<strong-password>

GRAFANA_ADMIN_PASSWORD=<strong-password>

# Replace <VM_PUBLIC_IP> with your Oracle VM's public IP
CORS_ORIGINS=http://localhost:3000,http://localhost:5173,http://<VM_PUBLIC_IP>:3000
```

### 3. (Optional) Reduce Spark memory for smaller VMs

If your VM has less than 16 GB RAM, edit `docker-compose.yml`:

```bash
# Change SPARK_WORKER_MEMORY from 3G to 2G
sed -i 's/SPARK_WORKER_MEMORY: 3G/SPARK_WORKER_MEMORY: 2G/' docker-compose.yml
```

### 4. Start the full stack

```bash
make up
```

Wait 60–90 seconds, then verify:

```bash
make status
```

All containers should show `healthy` or `running`.

### 5. Activate the CDC pipeline

```bash
make connector-register   # register the Debezium connector
make spark-all            # submit Bronze → Silver → Gold jobs
make simulate             # (optional) start the data simulator
```

Or all four steps at once:

```bash
make pipeline-start
```

---

## Access Services from Your Browser

Replace `<VM_PUBLIC_IP>` with your Oracle VM's actual public IP.

| Service | URL | Default login |
|---------|-----|---------------|
| Frontend | `http://<VM_PUBLIC_IP>:3000` | `admin` / `API_ADMIN_PASSWORD` |
| API docs | `http://<VM_PUBLIC_IP>:8000/docs` | — |
| Trino UI | `http://<VM_PUBLIC_IP>:8080` | — |
| Spark UI | `http://<VM_PUBLIC_IP>:8085` | — |
| MinIO Console | `http://<VM_PUBLIC_IP>:9001` | `MINIO_ROOT_USER` / `MINIO_ROOT_PASSWORD` |
| Superset | `http://<VM_PUBLIC_IP>:8088` | `admin` / `SUPERSET_ADMIN_PASSWORD` |
| Grafana | `http://<VM_PUBLIC_IP>:3001` | `admin` / `GRAFANA_ADMIN_PASSWORD` |
| Prometheus | `http://<VM_PUBLIC_IP>:9090` | — |

---

## Troubleshooting

### Services not reachable from browser

1. Check OCI Security List has an ingress rule for the port
2. Check iptables: `sudo iptables -L INPUT -n | grep <port>`
3. Check the container is running: `docker compose ps`
4. Check CORS: open browser DevTools → Network tab → look for a CORS error on `/api` calls → add your IP to `CORS_ORIGINS` in `.env`, then `make down && make up`

### Container keeps restarting

```bash
docker logs cdc-kafka-connect --tail 50
docker logs cdc-hive-metastore --tail 50
```

### Out of memory

```bash
free -h
docker stats --no-stream   # see per-container usage
```

Reduce `SPARK_WORKER_MEMORY` in `docker-compose.yml` if under 16 GB.

### Full reset

```bash
make reset   # wipes all volumes — 3-second abort window
make up
```

---

## VM Sizing

| Shape | RAM | Verdict |
|-------|-----|---------|
| 2 OCPU / 8 GB | 8 GB | Minimal — reduce Spark to 2G |
| 4 OCPU / 16 GB | 16 GB | Recommended |
| 4 OCPU / 32 GB | 32 GB | Comfortable with room for data |

Disk: **50 GB minimum** to hold Docker images and Iceberg data.
