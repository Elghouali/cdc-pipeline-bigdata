"""Verify Gold refresh invalidates all six upstream table metadata entries."""
import importlib.util
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

spec = importlib.util.spec_from_file_location(
    "gold_job", Path(__file__).resolve().parents[1] / "spark_jobs" / "gold_job.py"
)
gold = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gold)


class GoldRefreshTest(unittest.TestCase):
    def test_refreshes_silver_metadata_before_building_snapshots(self):
        from datetime import date

        spark = MagicMock()
        spark.sql.return_value.first.return_value = SimpleNamespace(
            day=date(2026, 11, 26)
        )
        expected = [
            "iceberg.analytics.silver_" + table
            for table in ("customers", "products", "orders", "order_items", "payments", "returns")
        ]
        seen = []

        def build(_spark):
            self.assertEqual(
                [call.args[0] for call in spark.catalog.refreshTable.call_args_list],
                expected,
            )
            seen.append(True)
            return MagicMock()

        with (
            patch.object(gold, "build_gold_customers", side_effect=build),
            patch.object(gold, "build_gold_orders", side_effect=build),
            patch.object(gold, "build_gold_sales_facts", side_effect=build),
            patch.object(gold, "build_gold_payments_summary", side_effect=build),
            patch.object(gold, "build_gold_returns_summary", side_effect=build),
            patch.object(gold, "refresh_gold_table") as write,
        ):
            gold.run_gold_refresh(spark, 7)
        self.assertEqual(len(seen), 5)
        self.assertEqual(write.call_count, 5)


if __name__ == "__main__":
    unittest.main()
