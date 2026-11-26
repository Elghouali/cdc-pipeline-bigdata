#!/usr/bin/env python3
"""CI-only failure injection: kill Bronze's child process group and verify restart."""
import json
import subprocess
import time

COMPOSE = ["docker", "compose", "exec", "-T", "spark-master"]


def status():
    raw = subprocess.check_output(
        COMPOSE + ["python3", "/opt/spark-apps/supervise.py", "--status"],
        text=True,
        timeout=15,
    )
    return next(row for row in map(json.loads, raw.splitlines()) if row["layer"] == "bronze")


def main():
    before = status()
    assert before["state"] == "running", before
    subprocess.run(
        COMPOSE + [
            "python3", "-c",
            "import os,signal,sys; os.killpg(int(sys.argv[1]), signal.SIGKILL)",
            str(before["pid"]),
        ],
        check=True,
        timeout=15,
    )
    deadline = time.monotonic() + 180
    while time.monotonic() < deadline:
        current = status()
        if (
            current.get("state") == "running"
            and current["generation"] > before["generation"]
            and current["pid"] != before["pid"]
            and current["supervisor"] == before["supervisor"]
        ):
            print("PASS recovery:bronze_driver_restarted", flush=True)
            return
        if current.get("state") == "exhausted":
            raise RuntimeError("Bronze supervisor exhausted its restart budget")
        time.sleep(5)
    raise TimeoutError("Bronze driver did not restart")


if __name__ == "__main__":
    main()
