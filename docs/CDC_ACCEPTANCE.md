# CDC acceptance testing and latency evidence

## Why this exists

The API tests are not proof of CDC delivery. This acceptance harness writes a unique test customer to PostgreSQL and verifies real INSERT, UPDATE and DELETE events in Bronze and the corresponding unique row in Silver, including the soft-delete flag. Optional Gold checks validate the current daily snapshot. It exits nonzero on timeout, unexpected state or failed cleanup.

## Run locally

Use a disposable development stack (not a live or shared environment). Do not run the random simulator concurrently: it may attach an order to the fixture or alter it. Start the stack using `make up`, wait for healthy dependencies, run `make connector-register`, and start the Spark jobs with `make spark-all`. Do not start a second set of Spark jobs on an existing stack. Ensure the Trino CLI is available in the Trino container and the Spark jobs have created their tables.

```bash
python -m unittest discover -s tests -v
python scripts/cdc_smoke.py --output artifacts/cdc-smoke.json
# Optional: also verify Gold refreshes (allow longer per check)
python scripts/cdc_smoke.py --gold --output artifacts/cdc-smoke-gold.json
```

The smoke harness uses Python 3.10+ and Docker Compose; no third-party Python dependencies. It generates a unique synthetic email and removes only that source row on exit. Bronze history and Silver tombstones intentionally remain. Review failed output and service logs before retrying. Never publish sensitive logs or production data.

## Evidence and limits

The JSON report records pass/fail, observed counts and elapsed polling times. Stage observation includes polling, query overhead and, for UPDATE/DELETE, the source command; INSERT stage timing begins after the insert has returned. Gold observation includes earlier Bronze/Silver checks. These timings are not precise end-to-end latency and must not be described as a throughput benchmark. Gold uses the current date in Trino; run away from midnight and align Spark/Trino time zones.

| Evidence | Acceptance criterion |
| --- | --- |
| Bronze | At least one event for each operation and the unique customer ID |
| Silver | Exactly one matching row, correct city and active/delete state |
| Gold (optional) | Current snapshot has the correct city, then no row after deletion |
| Source cleanup | Fixture removed; failure is reported |

Still required before production claims: full replay/idempotency and stale-event tests across micro-batches; Kafka partition/offset ordering policy; all-entity reconciliation; controlled throughput tests; failure recovery; security review. Verified Bronze/Silver baseline and the exact recorded observation times are linked in the [README](../README.md). Gold CI now starts a third worker and refreshes on a 30-second interval for acceptance testing, instead of the default 300 seconds. Gold customer verification includes the expected city, zero orders/spend/average order value and absence after deletion. Each table's daily partition is replaced explicitly, including empty snapshots; cross-table atomicity is not guaranteed. The three customer operations do not validate every business aggregate or all entities.

Gold refreshes disable the Iceberg catalog cache for the Gold application and explicitly refresh the six Silver input tables before building fresh DataFrames. This addresses possible stale metadata across independent Spark processes. A failed Gold assertion records only the synthetic fixture's Silver and Gold fields before source cleanup, to distinguish missing rows from incorrect aggregates. The freshness correction requires a new live run to confirm.
