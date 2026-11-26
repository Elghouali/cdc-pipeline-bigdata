# Reliability and recovery — local Compose

## Driver supervision

Start with `make spark-all`. Each driver runs in the master container under a Python supervisor with an exclusive per-layer flock. Duplicate submissions through this path exit without launching another driver. Failed children restart using exponential backoff, capped at 60 seconds, with a five-consecutive-failure budget (reset after ten minutes of healthy process lifetime). Status is available with `make spark-status`; logs append to /tmp/cdc-{layer}.log. A restart preserves Iceberg tables and checkpoints. A process can be alive but stalled, and a supervisor or whole master-container restart is not automatically recovered by this wrapper; rerun make spark-all after the master returns. Do not mix legacy manually submitted drivers with supervised drivers. Migrate from older deployments by stopping all legacy drivers before starting supervisors. Never remove checkpoint directories to fix an ordinary failure.

## Monitoring

GET /metrics reports bounded Spark master application counts and Debezium connector/task health. Prometheus alerts on missing/duplicate drivers and nonrunning connector/tasks. Kafka consumer-group lag is not Spark checkpoint lag. Active Spark applications with allocated cores are only a liveness proxy, not a freshness guarantee; a full canary/freshness SLO remains outstanding. The metrics endpoint exposes no raw business payloads.

## Reconciliation

Stop the traffic simulator and other source writers before running make reconcile. The tool compares source and Silver active primary key counts plus ordered-key digests for all six tables, and waits for bounded convergence. It detects missing, extra and duplicate active keys, not incorrect field values. Separate reads cannot prove consistency while concurrent writes occur. This local check materializes keys in SQL; large production datasets need partitioned reconciliation and stronger consistency controls. No repairs are made automatically.

## Recovery evidence and backup

CI kills the Bronze child process group after the initial customer lifecycle, requires a new child under the same supervisor, then runs the nonzero six-entity business fixture and quiescent key reconciliation. This is driver crash recovery, not a proven crash exactly at an Iceberg commit/checkpoint boundary. It does not prove Kafka broker, object-store or master recovery.

For disaster recovery, quiesce writers; coordinate PostgreSQL logical/physical backup (including WAL and replication requirements), Kafka topics and offsets, Hive catalog, object warehouse and Spark checkpoints. Store encrypted backups outside the host, record versions and restore into an isolated environment. Do not claim a standalone database dump backs up the entire pipeline. Automated consistent backup/restore drill and safe Iceberg retention/compaction policy remain separate work.

## Extended recovery checks

The Gold driver writes a timestamp to the shared runtime volume only after all five writes finish. The API mounts that volume read-only and exports the timestamp; Prometheus alerts after 15 minutes without success. This measures refresh completion, not end-to-end event age. Idle source tables do not by themselves trigger a Bronze/Silver stale alert. CI restarts the entire Spark master container (preserving volumes), waits for three workers, resubmits via `make spark-all`, then verifies the business fixture and reconciliation. Restart is operator-orchestrated, not automatic master failover.

`make backup-source` creates a private local PostgreSQL custom-format dump. `make backup-verify` additionally restores to a randomly named temporary database on the same server, compares ordered full-row digests for all six source entities, and drops only that newly created database. Run with source writers quiescent. CI uses a temporary directory and does not publish the dump. These are source-only backups: Kafka, offsets, Hive, object storage, and checkpoints are not included. Store real backups encrypted off-host; verify role and replication restoration separately.

`make maintenance-report` inventories Iceberg data files and snapshots; Gold tables with at least five files below 32 MiB are review candidates, not automatic compaction triggers. Use the report to plan maintenance. In a separate test environment with Gold writer stopped and spare Spark capacity, evaluate Iceberg `CALL iceberg.system.rewrite_data_files(table => 'analytics.gold_customers')` (see https://iceberg.apache.org/docs/1.5.2/spark-procedures/). Verify row-level equivalence before applying it to other Gold tables. Do not compact Bronze or expire snapshots while Silver might need those snapshots. Do not run orphan-file deletion against a shared warehouse/checkpoint location. Snapshot expiration, off-host full-stack backup, and automated failover remain explicitly unverified.
