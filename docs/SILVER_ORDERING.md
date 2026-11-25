# Silver event ordering and replay safety

## Contract

Each entity has its own Kafka topic. With stable topic partitioning, a primary key always maps to one partition; the offset is its authoritative order, not the source timestamp. Equal timestamps, clock anomalies and a repeated micro-batch cannot make an older offset newer.

Silver persists the last Kafka partition and offset with every row. The merge updates only strictly newer offsets, retains the offset for soft deletes and inserts a tombstone even when the delete is the first observed event. This prevents a later replay of an older create from resurrecting the key. A mismatched partition or missing watermark is an error rather than an arbitrary ordering decision. The contract assumes topics are not recreated and offsets are not reset or reused. Do not increase partitions or change key serialization without an explicit migration.

## Existing deployments

This is a schema change. CREATE TABLE IF NOT EXISTS cannot migrate the old tables, and simply adding nullable columns would not recover the original offsets. The Silver startup now fails clearly if those columns are absent. Do not delete real data or checkpoints automatically.

For a disposable local demo, back up any useful data and follow the existing documented reset/start procedure to recreate the stack with the new schema. For a persistent deployment, pause Silver and Gold, retain Bronze and source offsets, build replacement Silver tables by replaying retained Bronze history, reconcile counts and active/deleted rows, then perform a reviewed cutover with new Silver checkpoints. Validate Bronze retention and topic identity before doing so. No automatic production migration is included.

## Test evidence

Run the dedicated Spark-local suite with Java 17 and PySpark 3.5.5:

```bash
python -m pip install pyspark==3.5.5
python -m unittest discover -s spark_tests -v
```

The tests exercise local Spark deduplication and validate the generated merge guards. They do not execute Iceberg MERGE or simulate a real Kafka restart. Full cross-micro-batch replay, Iceberg schema migration, multi-entity reconciliation and recovery tests remain required. The CDC lifecycle harness in [CDC_ACCEPTANCE.md](CDC_ACCEPTANCE.md) checks live inserts, updates and deletes when the full stack is available.
