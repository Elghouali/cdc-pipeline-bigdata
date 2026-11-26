#!/usr/bin/env python3
"""Verify the private Kubernetes console, least privilege and monitoring."""

import base64
import contextlib
import json
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

import kubernetes_cdc_smoke as kube

K = ["kubectl", "-n", kube.NAMESPACE]


def secret(key):
    raw = subprocess.check_output(
        K + ["get", "secret", "cdc-secrets", "-o", f"jsonpath={{.data.{key}}}"],
        text=True, timeout=15,
    )
    return base64.b64decode(raw).decode()


def request(url, data=None, headers=None):
    req = urllib.request.Request(
        url, data=json.dumps(data).encode() if data is not None else None,
        headers={"Content-Type": "application/json", **(headers or {})},
    )
    with urllib.request.urlopen(req, timeout=15) as response:
        return response.read().decode()


def retry(label, check, timeout=240):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            if check():
                print(f"PASS {label}", flush=True)
                return
        except (OSError, ValueError, KeyError, subprocess.SubprocessError):
            pass
        time.sleep(5)
    raise TimeoutError(label)


@contextlib.contextmanager
def port_forward(service, local, remote):
    proc = subprocess.Popen(
        K + ["port-forward", f"svc/cdc-{service}", f"{local}:{remote}"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    try:
        yield f"http://127.0.0.1:{local}"
    finally:
        proc.terminate()
        proc.wait(timeout=10)


def denied(url, status):
    try:
        request(url)
    except urllib.error.HTTPError as exc:
        return exc.code == status
    return False


def main():
    checks = []
    report = {"status": "failed", "checks": checks}
    try:
        with port_forward("frontend", 13000, 80) as ui, port_forward(
            "prometheus", 19090, 9090
        ) as prom, port_forward("grafana", 13001, 3000) as graf:
            retry("frontend", lambda: "<html" in request(ui + "/").lower())
            checks.append("frontend")
            retry("proxy health", lambda: all(
                row["status"] == "up" for row in json.loads(request(ui + "/api/health"))
            ))
            checks.append("proxy health")
            assert denied(ui + "/api/events/stream", 401)
            checks.append("unauthenticated stream rejected")
            password = secret("API_ADMIN_PASSWORD")
            token = json.loads(request(ui + "/auth/login", {
                "username": "admin", "password": password,
            }))["access_token"]
            headers = {"Authorization": "Bearer " + token}
            assert json.loads(request(ui + "/auth/me", headers=headers))["username"] == "admin"
            result = request(ui + "/api/query", {"sql": "SELECT 1 AS probe"}, headers)
            assert json.loads(result.strip())["probe"] == 1, "unexpected query result"
            checks.append("authenticated read query")
            assert json.loads(request(ui + "/api/spark/running"))["count"] == 3
            checks.append("three live Spark drivers")

            # The API process is non-root and its DB role cannot read source PII.
            script = (
                "import asyncio,asyncpg,os; from config import settings\n"
                "async def main():\n"
                " assert os.getuid()==10001\n"
                " conn=await asyncpg.connect(settings.database_url)\n"
                " try:\n"
                "  assert await conn.fetchval('SELECT current_schema()')=='api_runtime'\n"
                "  assert not await conn.fetchval("
                "\"SELECT has_table_privilege(current_user, 'public.customers', 'SELECT')\")\n"
                "  assert not await conn.fetchval("
                "\"SELECT rolsuper FROM pg_roles WHERE rolname=current_user\")\n"
                " finally: await conn.close()\n"
                "asyncio.run(main())"
            )
            subprocess.run(K + ["exec", "deployment/cdc-api", "--", "python", "-c", script],
                           check=True, timeout=30)
            checks.append("nonroot least-privilege database role")

            def metric(expr, expected):
                query = urllib.parse.urlencode({"query": expr})
                result = json.loads(request(prom + "/api/v1/query?" + query))["data"]["result"]
                return len(result) == 1 and expected(float(result[0]["value"][1]))

            for expr, expected in [
                ('up{job="cdc-api"}', lambda n: n == 1),
                ("cdc_connector_healthy", lambda n: n == 1),
                ("sum(cdc_spark_driver_active)", lambda n: n == 3),
                ("time() - cdc_gold_last_success_timestamp_seconds", lambda n: 0 <= n < 900),
            ]:
                retry(expr, lambda e=expr, test=expected: metric(e, test))
                checks.append(expr)
            rules = json.loads(request(prom + "/api/v1/rules"))["data"]["groups"]
            assert any(g["name"] == "cdc" and len(g["rules"]) == 4 for g in rules)
            checks.append("four Prometheus alert rules loaded")
            retry("Grafana health", lambda: json.loads(request(graf + "/api/health"))["database"] == "ok")
            basic = base64.b64encode(("admin:" + secret("GRAFANA_ADMIN_PASSWORD")).encode()).decode()
            retry("Grafana dashboard", lambda: json.loads(request(
                graf + "/api/dashboards/uid/cdc-k8s-runtime", headers={"Authorization": "Basic " + basic}
            ))["dashboard"]["uid"] == "cdc-k8s-runtime")
            checks.append("Grafana dashboard provisioned")
            report["status"] = "passed"
    finally:
        path = Path("artifacts/kubernetes-console.json")
        path.parent.mkdir(exist_ok=True)
        path.write_text(json.dumps(report, indent=2) + "\n")
        print(json.dumps(report), flush=True)


if __name__ == "__main__":
    main()
