#!/usr/bin/env python3
"""CI-only checkpoint recovery with queued changes and duplicate detection."""

import json
import subprocess
import time
import uuid
from pathlib import Path

import cdc_smoke as smoke
import kubernetes_cdc_smoke as kube

K = ["kubectl", "-n", kube.NAMESPACE]
LAYERS = ("bronze", "silver", "gold")


def run(*args, timeout=300):
    subprocess.run(K + list(args), check=True, timeout=timeout)


def uid(layer):
    return smoke.command(K + [
        "get", "pods", "-l", f"app.kubernetes.io/component=spark-{layer}",
        "-o", "jsonpath={.items[0].metadata.uid}",
    ])


def main():
    smoke.postgres = kube.postgres
    smoke.trino_query = kube.trino_query
    report = {"status": "failed", "checks": []}
    email = f"recovery-{uuid.uuid4().hex}@example.invalid"

    def wait(label, sql, expected=1):
        report["checks"].append(smoke.wait_for(label, sql, lambda n: n == expected, 600, 5))

    try:
        customer = int(kube.postgres(
            "INSERT INTO customers(name,email,city,segment) "
            f"VALUES ('Recovery fixture','{email}','Casablanca','B2C') RETURNING id"
        ))
        wait("before:bronze", smoke.bronze_sql(customer, "c"))
        wait("before:silver", smoke.silver_sql(customer, "Casablanca"))
        wait("before:gold", smoke.gold_sql(customer, "Casablanca"))
        old = {layer: uid(layer) for layer in LAYERS}
        for layer in reversed(LAYERS):
            run("scale", f"deployment/cdc-spark-{layer}", "--replicas=0")
            run("wait", "--for=delete", "pod", "-l",
                f"app.kubernetes.io/component=spark-{layer}", "--timeout=180s")
        kube.postgres(f"UPDATE customers SET city='Rabat' WHERE id={customer}")
        for layer in LAYERS:
            run("scale", f"deployment/cdc-spark-{layer}", "--replicas=1")
            run("rollout", "status", f"deployment/cdc-spark-{layer}", "--timeout=300s")
            deadline = time.monotonic() + 180
            while time.monotonic() < deadline:
                new = uid(layer)
                if new and new != old[layer]:
                    break
                time.sleep(3)
            else:
                raise RuntimeError(f"{layer} pod was not replaced")
        wait("after:bronze:queued-update", smoke.bronze_sql(customer, "u"))
        wait("after:bronze:no-duplicate-insert", smoke.bronze_sql(customer, "c"))
        wait("after:silver", smoke.silver_sql(customer, "Rabat"))
        wait("after:gold", smoke.gold_sql(customer, "Rabat"))
        kube.postgres(f"DELETE FROM customers WHERE id={customer}")
        wait("after:bronze:delete", smoke.bronze_sql(customer, "d"))
        wait("after:silver:delete", smoke.silver_sql(customer, deleted=True))
        wait("after:gold:delete", smoke.gold_sql(customer), 0)
        report["status"] = "passed"
    finally:
        path = Path("artifacts/kubernetes-recovery.json")
        path.parent.mkdir(exist_ok=True)
        path.write_text(json.dumps(report, indent=2) + "\n")
        print(json.dumps(report), flush=True)
        kube.postgres(f"DELETE FROM customers WHERE email='{email}'")
        # Restore desired replicas even on failure for diagnostics.
        for layer in LAYERS:
            run("scale", f"deployment/cdc-spark-{layer}", "--replicas=1")


if __name__ == "__main__":
    main()
