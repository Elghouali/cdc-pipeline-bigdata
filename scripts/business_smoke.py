#!/usr/bin/env python3
"""Nonzero business fixture through all six source entities; isolated CI only."""
import uuid

from cdc_smoke import postgres, wait_for

email = f"business-smoke-{uuid.uuid4().hex}@example.invalid"
customer = product = order = None


def expect(label, query, expected=1):
    wait_for(label, query, lambda n: n == expected, 600, 5)


def main():
    global customer, product, order
    try:
        customer = int(postgres(
            "INSERT INTO customers(name,email,city,segment) "
            f"VALUES ('Business smoke','{email}','Rabat','B2C') RETURNING id"
        ))
        product = int(postgres(
            "INSERT INTO products(name,category,brand,price,stock_qty) "
            "VALUES ('Business smoke','Test','Test',0.10,10) RETURNING id"
        ))
        order = int(postgres(
            "INSERT INTO orders(customer_id,status,channel) "
            f"VALUES ({customer},'delivered','web') RETURNING id"
        ))
        item = int(postgres(
            "INSERT INTO order_items(order_id,product_id,quantity,unit_price) "
            f"VALUES ({order},{product},3,0.10) RETURNING id"
        ))
        payment = int(postgres(
            "INSERT INTO payments(order_id,method,amount,status) "
            f"VALUES ({order},'wallet',0.30,'completed') RETURNING id"
        ))
        postgres(
            "INSERT INTO payments(order_id,method,amount,status) "
            f"VALUES ({order},'wallet',99.99,'failed'),({order},'wallet',20.00,'pending')"
        )
        ret = int(postgres(
            "INSERT INTO returns(order_id,reason,status) "
            f"VALUES ({order},'other','rejected') RETURNING id"
        ))
        for table, pk in (
            ("customers", customer), ("products", product), ("orders", order),
            ("order_items", item), ("payments", payment), ("returns", ret),
        ):
            expect(
                f"business:silver:{table}",
                f"SELECT count(*) FROM silver_{table} WHERE id={pk} AND NOT _is_deleted",
            )
        expect("business:decimal", f"SELECT count(*) FROM silver_payments WHERE id={payment} AND amount=DECIMAL '0.30'")
        expect("business:customer_spend", f"SELECT count(*) FROM gold_customers WHERE customer_id={customer} AND snapshot_date=current_date AND total_orders=1 AND total_spent=DECIMAL '0.30' AND avg_order_value=DECIMAL '0.30'")
        expect("business:order_grain", f"SELECT CASE WHEN count(*)=1 AND count_if(order_total=DECIMAL '0.30' AND item_count=3 AND payment_status='completed' AND NOT has_return)=1 THEN 1 ELSE 0 END FROM gold_orders WHERE order_id={order} AND snapshot_date=current_date")
        postgres(f"UPDATE returns SET status='approved' WHERE id={ret}")
        expect("business:approved_return", f"SELECT count(*) FROM gold_orders WHERE order_id={order} AND snapshot_date=current_date AND has_return")
    finally:
        if order is not None:
            postgres(f"DELETE FROM orders WHERE id={order}")
        if product is not None:
            postgres(f"DELETE FROM products WHERE id={product}")
        postgres(f"DELETE FROM customers WHERE email='{email}'")


if __name__ == "__main__":
    main()
