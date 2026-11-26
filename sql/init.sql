-- ─────────────────────────────────────────────────────────────────────────────
--  init.sql  —  E-commerce source schema
--
--  Notes:
--  • wal_level=logical is set via the postgres container command in
--    docker-compose.yml — no need to SET it here.
--  • A dedicated replication user for Debezium is created at the bottom.
--  • Tables are created in the public schema so Debezium's default
--    topic naming (cdc.public.<table>) works without extra config.
-- ─────────────────────────────────────────────────────────────────────────────

-- ── customers ─────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS customers (
    id          SERIAL          PRIMARY KEY,
    name        VARCHAR(120)    NOT NULL,
    email       VARCHAR(200)    UNIQUE NOT NULL,
    city        VARCHAR(80)     NOT NULL,
    segment     VARCHAR(30)     NOT NULL CHECK (segment IN ('B2B','B2C','Premium','Standard')),
    signup_date DATE            NOT NULL DEFAULT CURRENT_DATE
);

-- ── products ──────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS products (
    id          SERIAL          PRIMARY KEY,
    name        VARCHAR(200)    NOT NULL,
    category    VARCHAR(80)     NOT NULL,
    brand       VARCHAR(100)    NOT NULL,
    price       NUMERIC(10,2)   NOT NULL CHECK (price >= 0),
    stock_qty   INT             NOT NULL DEFAULT 0 CHECK (stock_qty >= 0)
);

-- ── orders ────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS orders (
    id          SERIAL          PRIMARY KEY,
    order_date  DATE            NOT NULL DEFAULT CURRENT_DATE,
    customer_id INT             NOT NULL REFERENCES customers(id) ON DELETE RESTRICT,
    status      VARCHAR(30)     NOT NULL
                    CHECK (status IN ('pending','confirmed','shipped','delivered','cancelled','returned')),
    channel     VARCHAR(30)     NOT NULL
                    CHECK (channel IN ('web','mobile','in-store','marketplace'))
);

-- ── order_items ───────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS order_items (
    id          SERIAL          PRIMARY KEY,
    order_id    INT             NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    product_id  INT             NOT NULL REFERENCES products(id) ON DELETE RESTRICT,
    quantity    INT             NOT NULL CHECK (quantity > 0),
    unit_price  NUMERIC(10,2)   NOT NULL CHECK (unit_price >= 0)
);

-- ── payments ──────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS payments (
    id              SERIAL          PRIMARY KEY,
    order_id        INT             NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    payment_date    DATE            NOT NULL DEFAULT CURRENT_DATE,
    method          VARCHAR(40)     NOT NULL
                        CHECK (method IN ('credit_card','debit_card','cash_on_delivery','bank_transfer','wallet')),
    amount          NUMERIC(12,2)   NOT NULL CHECK (amount >= 0),
    status          VARCHAR(20)     NOT NULL
                        CHECK (status IN ('pending','completed','failed','refunded'))
);

-- ── returns ───────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS returns (
    id          SERIAL          PRIMARY KEY,
    order_id    INT             NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    return_date DATE            NOT NULL DEFAULT CURRENT_DATE,
    reason      VARCHAR(80)     NOT NULL
                    CHECK (reason IN ('defective','wrong_item','not_as_described','changed_mind','other')),
    status      VARCHAR(20)     NOT NULL
                    CHECK (status IN ('requested','approved','rejected','completed'))
);

-- ─────────────────────────────────────────────────────────────────────────────
--  Indexes on foreign-key columns
--  PostgreSQL never auto-creates indexes for FK columns; without them every
--  join and ON DELETE CASCADE lookup becomes a sequential scan.
-- ─────────────────────────────────────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_orders_customer_id      ON orders(customer_id);
CREATE INDEX IF NOT EXISTS idx_order_items_order_id    ON order_items(order_id);
CREATE INDEX IF NOT EXISTS idx_order_items_product_id  ON order_items(product_id);
CREATE INDEX IF NOT EXISTS idx_payments_order_id       ON payments(order_id);
CREATE INDEX IF NOT EXISTS idx_returns_order_id        ON returns(order_id);

-- ─────────────────────────────────────────────────────────────────────────────
--  Debezium replication user
--  wal_level=logical is already applied via docker-compose.yml command arg.
-- ─────────────────────────────────────────────────────────────────────────────
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'debezium') THEN
        CREATE USER debezium WITH REPLICATION LOGIN;
    END IF;
END
$$;

GRANT USAGE  ON SCHEMA public TO debezium;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO debezium;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO debezium;

-- Logical replication publication (pgoutput plugin) for all six tables
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT FROM pg_publication WHERE pubname = 'debezium_pub'
    ) THEN
        CREATE PUBLICATION debezium_pub
            FOR TABLE customers, products, orders, order_items, payments, returns;
    END IF;
END
$$;
