#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
#  simulate_changes.sh
#  Continuously emits INSERT / UPDATE / DELETE events on the ecommerce DB
#  to exercise the CDC pipeline with realistic live traffic.
#
#  Usage:  ./scripts/simulate_changes.sh [interval_seconds]
#  Default interval: 5 seconds between rounds
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

INTERVAL=${1:-5}
PGUSER=${POSTGRES_USER:-postgres}
PGPASSWORD=${POSTGRES_PASSWORD:-postgres}
PGDATABASE=${PGDATABASE:-ecommerce}
CONTAINER=${POSTGRES_CONTAINER:-cdc-postgres}

# Use a bash array so word-splitting never breaks when variables contain spaces.
PG=(docker exec -e "PGPASSWORD=${PGPASSWORD}" "${CONTAINER}"
    psql -U "${PGUSER}" -d "${PGDATABASE}" -v ON_ERROR_STOP=1 -q)
ITER=0

log() { echo "[$(date '+%H:%M:%S')] $*"; }

log "CDC simulator starting — interval=${INTERVAL}s  target=docker://${CONTAINER}/${PGDATABASE}"

while true; do
  ITER=$((ITER + 1))
  log "── Round $ITER ─────────────────────────────────────────"

  # ── 1. New customer ──────────────────────────────────────────────────────────
  "${PG[@]}" -c "
    INSERT INTO customers (name, email, city, segment, signup_date)
    VALUES (
      'SimClient_${ITER}',
      'sim_${ITER}_' || extract(epoch from now())::bigint || '@test.ma',
      (ARRAY['Casablanca','Rabat','Fes','Marrakech','Agadir','Tanger'])[floor(random()*6+1)],
      (ARRAY['B2B','B2C','Premium','Standard'])[floor(random()*4+1)],
      CURRENT_DATE
    );"
  log "  INSERT customer sim_${ITER}"

  # ── 2. Update a random customer city ────────────────────────────────────────
  "${PG[@]}" -c "
    UPDATE customers
    SET    city = (ARRAY['Casablanca','Rabat','Fes','Oujda','Meknes'])[floor(random()*5+1)]
    WHERE  id = (SELECT id FROM customers ORDER BY random() LIMIT 1);"
  log "  UPDATE customer city"

  # ── 3. New product ───────────────────────────────────────────────────────────
  "${PG[@]}" -c "
    INSERT INTO products (name, category, brand, price, stock_qty)
    VALUES (
      'SimProd_${ITER}',
      (ARRAY['Electronics','Clothing','Food','Home','Sports'])[floor(random()*5+1)],
      'SimBrand',
      round((random() * 4900 + 99)::numeric, 2),
      (floor(random()*200)+5)::int
    );"
  log "  INSERT product SimProd_${ITER}"

  # ── 4. Restock a random product ──────────────────────────────────────────────
  "${PG[@]}" -c "
    UPDATE products
    SET    stock_qty = stock_qty + (floor(random()*50)+1)::int
    WHERE  id = (SELECT id FROM products ORDER BY random() LIMIT 1);"
  log "  UPDATE product stock"

  # ── 5. New order ─────────────────────────────────────────────────────────────
  NEW_ORDER=$("${PG[@]}" -tAc "
    INSERT INTO orders (order_date, customer_id, status, channel)
    VALUES (
      CURRENT_DATE,
      (SELECT id FROM customers ORDER BY random() LIMIT 1),
      'pending',
      (ARRAY['web','mobile','in-store','marketplace'])[floor(random()*4+1)]
    )
    RETURNING id;")
  NEW_ORDER=$(echo "$NEW_ORDER" | tr -d '[:space:]')
  log "  INSERT order id=$NEW_ORDER"

  # ── 6. Add 2 items to the new order ──────────────────────────────────────────
  "${PG[@]}" -c "
    INSERT INTO order_items (order_id, product_id, quantity, unit_price)
    SELECT ${NEW_ORDER}, id, (floor(random()*3)+1)::int, price
    FROM   products ORDER BY random() LIMIT 2;"
  log "  INSERT 2 order_items for order $NEW_ORDER"

  # ── 7. Confirm the order ──────────────────────────────────────────────────────
  "${PG[@]}" -c "UPDATE orders SET status='confirmed' WHERE id=${NEW_ORDER};"
  log "  UPDATE order $NEW_ORDER pending->confirmed"

  # ── 8. Payment for the new order ─────────────────────────────────────────────
  AMOUNT=$("${PG[@]}" -tAc "
    SELECT COALESCE(SUM(quantity::numeric * unit_price), 0)
    FROM   order_items WHERE order_id=${NEW_ORDER};" | tr -d '[:space:]')
  if [[ -z "$AMOUNT" ]]; then
    log "  WARN: Could not compute payment amount for order $NEW_ORDER — skipping payment"
  else
    "${PG[@]}" -c "
      INSERT INTO payments (order_id, payment_date, method, amount, status)
      VALUES (
        ${NEW_ORDER}, CURRENT_DATE,
        (ARRAY['credit_card','debit_card','cash_on_delivery','bank_transfer','wallet'])[floor(random()*5+1)],
        ${AMOUNT}, 'completed'
      );"
    log "  INSERT payment amount=${AMOUNT}"
  fi

  # ── 9. Advance 3 existing orders in the pipeline ─────────────────────────────
  "${PG[@]}" -c "
    UPDATE orders
    SET    status = CASE status WHEN 'confirmed' THEN 'shipped'
                                WHEN 'shipped'   THEN 'delivered'
                                ELSE status END
    WHERE  id IN (
      SELECT id FROM orders WHERE status IN ('confirmed','shipped')
      ORDER BY random() LIMIT 3
    );"
  log "  UPDATE up to 3 orders (confirmed->shipped or shipped->delivered)"

  # ── 10. Every 4th round: cancel a pending order ───────────────────────────────
  if (( ITER % 4 == 0 )); then
    "${PG[@]}" -c "
      UPDATE orders SET status='cancelled'
      WHERE  id=(SELECT id FROM orders WHERE status='pending' ORDER BY random() LIMIT 1);" \
      2>/dev/null || true
    log "  UPDATE 1 pending order -> cancelled"
  fi

  # ── 11. Every 7th round: create a return ─────────────────────────────────────
  if (( ITER % 7 == 0 )); then
    RETURN_ORD=$("${PG[@]}" -tAc "
      SELECT o.id FROM orders o
      LEFT JOIN returns r ON r.order_id=o.id
      WHERE  o.status='delivered' AND r.id IS NULL
      ORDER  BY random() LIMIT 1;" | tr -d '[:space:]')
    if [[ -n "$RETURN_ORD" ]]; then
      "${PG[@]}" -c "
        INSERT INTO returns (order_id, return_date, reason, status)
        VALUES (${RETURN_ORD}, CURRENT_DATE,
          (ARRAY['defective','wrong_item','not_as_described','changed_mind','other'])[floor(random()*5+1)],
          'requested');"
      "${PG[@]}" -c "UPDATE orders SET status='returned' WHERE id=${RETURN_ORD};"
      log "  INSERT return + UPDATE order $RETURN_ORD -> returned"
    fi
  fi

  # ── 12. Every 10th round: delete items from a cancelled order ─────────────────
  if (( ITER % 10 == 0 )); then
    "${PG[@]}" -c "
      DELETE FROM order_items
      WHERE  order_id=(SELECT id FROM orders WHERE status='cancelled' ORDER BY random() LIMIT 1);" \
      2>/dev/null || true
    log "  DELETE order_items of a cancelled order"
  fi

  log "  Sleeping ${INTERVAL}s …"
  sleep "$INTERVAL"
done
