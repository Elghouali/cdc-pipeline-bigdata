# Data correctness contract and upgrade

## Delivery

Bronze now uses failOnDataLoss=true and a left anti-join on (topic, partition, offset) before append. Both Bronze and quarantine are append-only, so Silver can read append snapshots. This protects replay after a committed write under a **single active writer per table and unchanged topic identity**; it does not guarantee exactly-once for a recreated topic, concurrent writers or pre-existing duplicate history. The anti-join may become expensive; benchmark it before scaling. Quarantine records malformed envelopes, unexpected tables, invalid operation codes, null payloads and missing/mismatched integer primary keys, including their raw event; the API identity is denied access. Quarantine retention and remediation need explicit operator procedures. Invalid typed Silver rows stop the stream without committing that batch, rather than silently dropping records; a key-only delete is valid. Existing Bronze data is not rewritten.

## Decimal migration

Debezium emits numeric values as strings; Silver uses source precision DECIMAL(10,2) for prices and DECIMAL(12,2) for payments. Gold monetary outputs use DECIMAL(28,2), rounding averages to cents. The jobs refuse to reuse incompatible existing DOUBLE columns. For existing deployments, stop writers, back up PostgreSQL, Kafka, catalog, warehouse and checkpoints, and test a separate rebuild with fresh Silver/Gold tables and independent checkpoints from retained Bronze history. Verify history completeness and reconcile monetary values with the source; historical double encoding cannot recover precision already lost. Do not clear volumes, offsets, or checkpoints automatically. New clean CI stacks need no migration. Gold prior snapshots are not retroactively corrected by this code.

## Business definitions

Customer spend sums only completed payments, excluding pending, failed and refunded statuses (refund status is a replacement state, not a separate negative ledger entry). Average order value divides that amount by all nondeleted orders. Gold orders have one row per order; the displayed payment descriptor prefers completed payments, then latest payment date and ID. Only approved/completed returns set has_return. Sales fact counts are distinct within each product category and not additive across categories; orphan order items are excluded. Gross revenue is ordered item value; net revenue is shipped/delivered item value, not cash settlement. Return summary's legacy return_month field now means order-month cohort: distinct delivered/returned orders form the denominator, and distinct orders per reason/status form the numerator; only approved/completed statuses have a nonzero rate. Overlapping reasons/statuses are not additive. The five Gold outputs are still separately committed, not a cross-table atomic snapshot.

## Evidence

Local Spark tests exercise replay filtering, malformed envelope classification, typed decimals and key-only deletes. Integration requires exactly one event per customer operation, checks all six entities, nonzero monetary totals and one-row order grain with multiple payments and return status changes. It checks quarantine access denial, not a live malformed Kafka event or a crash between sink commit and checkpoint. Full recovery/failure-injection and source reconciliation remain to be implemented.
