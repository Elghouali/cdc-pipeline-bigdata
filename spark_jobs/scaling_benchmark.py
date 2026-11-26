"""Run identical deterministic CPU work on one and two real Spark workers."""

import argparse
import json
import socket
import time

from pyspark.sql import SparkSession


def cpu_partition(items):
    host = socket.gethostname()
    result = 0
    for partition in items:
        value = partition + 1
        for index in range(500_000):
            value = (value * 1_664_525 + index + 1_013_904_223) & 0xFFFFFFFF
        result += value
    yield host, result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workers", type=int, choices=(1, 2), required=True)
    args = parser.parse_args()
    spark = SparkSession.builder.appName("cdc-distributed-scaling-probe").getOrCreate()
    try:
        sc = spark.sparkContext
        deadline = time.monotonic() + 120
        while time.monotonic() < deadline:
            # Includes the driver. Each worker has exactly one executor core.
            if sc._jsc.sc().getExecutorMemoryStatus().size() >= args.workers + 1:
                break
            time.sleep(2)
        else:
            raise TimeoutError("Expected remote executors did not register")
        started = time.monotonic()
        rows = sc.parallelize(range(32), 32).mapPartitions(cpu_partition).collect()
        elapsed = time.monotonic() - started
        hosts = sorted({host for host, _ in rows})
        if len(hosts) != args.workers or socket.gethostname() in hosts:
            raise RuntimeError(f"Unexpected executor placement: {hosts}")
        print(
            "SCALING_RESULT "
            + json.dumps(
                {
                    "workers": args.workers,
                    "executor_hosts": hosts,
                    "partitions": len(rows),
                    "checksum": sum(value for _, value in rows),
                    "seconds": round(elapsed, 3),
                }
            ),
            flush=True,
        )
    finally:
        spark.stop()


if __name__ == "__main__":
    main()
