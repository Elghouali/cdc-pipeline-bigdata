#!/usr/bin/env python3
"""CI-only master-container restart; preserve volumes and re-launch drivers."""
import json
import subprocess
import time
import urllib.request


def run(*args, timeout=300):
    subprocess.run(args, check=True, timeout=timeout)


def main():
    run("docker", "compose", "restart", "spark-master", timeout=120)
    deadline = time.monotonic() + 180
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen("http://localhost:8085/json", timeout=5) as response:
                master = json.load(response)
            if len([worker for worker in master.get("workers", []) if worker.get("state") == "ALIVE"]) >= 3:
                break
        except (OSError, ValueError):
            pass
        time.sleep(5)
    else:
        raise TimeoutError("Spark workers did not reconnect to the master")
    run("make", "spark-all", "GOLD_REFRESH_SECONDS=30", timeout=660)
    print("PASS recovery:master_restarted_and_drivers_submitted", flush=True)


if __name__ == "__main__":
    main()
