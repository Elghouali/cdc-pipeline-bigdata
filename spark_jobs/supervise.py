"""Bounded, single-writer Spark driver supervisor for local Compose."""

import argparse
import fcntl
import json
import os
import signal
import subprocess
import time
from pathlib import Path

LAYERS = ("bronze", "silver", "gold")


def state_path(layer):
    return Path(f"/tmp/cdc-{layer}.json")


def publish(layer, **fields):
    path = state_path(layer)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(fields) + "\n", encoding="utf-8")
    temporary.replace(path)


def command(layer, interval):
    args = [
        "/opt/spark/bin/spark-submit",
        "--master",
        "spark://spark-master:7077",
        "--conf",
        "spark.executor.memory=1g",
        "--conf",
        "spark.executor.cores=2",
        "--conf",
        "spark.cores.max=2",
        f"/opt/spark-apps/{layer}_job.py",
    ]
    if layer == "gold":
        args.extend(["--interval-seconds", str(interval)])
    return args


def supervise(layer, interval):
    lock = Path(f"/tmp/cdc-{layer}.lock").open("a", encoding="utf-8")
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        lock.close()
        return 0
    stopping = False
    child = None

    def shutdown(_signum, _frame):
        nonlocal stopping
        stopping = True
        if child is not None and child.poll() is None:
            try:
                os.killpg(child.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass

    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGINT, shutdown)
    failures = 0
    generation = 0
    try:
        with open(f"/tmp/cdc-{layer}.log", "a", encoding="utf-8") as log:
            while not stopping:
                generation += 1
                started = time.monotonic()
                child = subprocess.Popen(
                    command(layer, interval),
                    stdout=log,
                    stderr=subprocess.STDOUT,
                    start_new_session=True,
                )
                publish(
                    layer,
                    supervisor=os.getpid(),
                    pid=child.pid,
                    generation=generation,
                    state="running",
                )
                while child.poll() is None and not stopping:
                    time.sleep(1)
                if stopping:
                    try:
                        child.wait(timeout=20)
                    except subprocess.TimeoutExpired:
                        os.killpg(child.pid, signal.SIGKILL)
                        child.wait()
                    break
                code = child.wait()
                if time.monotonic() - started >= 600:
                    failures = 0
                failures += 1
                if failures >= 5:
                    publish(
                        layer,
                        supervisor=os.getpid(),
                        generation=generation,
                        state="exhausted",
                        exit_code=code,
                    )
                    return 1
                publish(
                    layer,
                    supervisor=os.getpid(),
                    generation=generation,
                    state="backoff",
                    exit_code=code,
                )
                deadline = time.monotonic() + min(60, 5 * 2 ** (failures - 1))
                while not stopping and time.monotonic() < deadline:
                    time.sleep(1)
    finally:
        lock.close()
    publish(layer, generation=generation, state="stopped")
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("layer", nargs="?", choices=LAYERS)
    parser.add_argument("--interval-seconds", type=int, default=300)
    parser.add_argument("--status", action="store_true")
    args = parser.parse_args()
    if args.status:
        for layer in LAYERS:
            path = state_path(layer)
            state = (
                json.loads(path.read_text()) if path.exists() else {"state": "absent"}
            )
            print(json.dumps({"layer": layer, **state}))
        return 0
    if not args.layer or args.interval_seconds <= 0:
        parser.error("Specify a layer and a positive refresh interval")
    return supervise(args.layer, args.interval_seconds)


if __name__ == "__main__":
    raise SystemExit(main())
