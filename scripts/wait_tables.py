#!/usr/bin/env python3
"""Wait for all six layer tables instead of sleeping blindly."""
import argparse

from cdc_smoke import wait_for

TABLES = ("customers", "products", "orders", "order_items", "payments", "returns")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("layer", choices=("bronze", "silver"))
    args = parser.parse_args()
    names = [
        f"{args.layer}_{table}" + ("_cdc" if args.layer == "bronze" else "")
        for table in TABLES
    ]
    literals = ", ".join(f"'{name}'" for name in names)
    wait_for(
        f"ready:{args.layer}",
        "SELECT count(*) FROM information_schema.tables WHERE table_schema='analytics' "
        f"AND table_name IN ({literals})",
        lambda n: n == len(names),
        300,
        5,
    )


if __name__ == "__main__":
    main()
