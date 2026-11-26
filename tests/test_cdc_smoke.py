"""Offline tests for the live CDC smoke harness (no Docker required)."""
import importlib.util
import unittest
from pathlib import Path
from unittest.mock import patch

spec = importlib.util.spec_from_file_location(
    "cdc_smoke", Path(__file__).resolve().parents[1] / "scripts" / "cdc_smoke.py"
)
smoke = importlib.util.module_from_spec(spec)
spec.loader.exec_module(smoke)


class SmokeTest(unittest.TestCase):
    def test_bronze_query_checks_operation_and_primary_key(self):
        query = smoke.bronze_sql(123, "d")
        self.assertIn("op = 'd'", query)
        self.assertIn("before_payload", query)
        self.assertIn("= 123", query)
        with self.assertRaises(ValueError):
            smoke.bronze_sql(123, "invalid")

    def test_silver_checks_uniqueness_and_deleted_state(self):
        self.assertIn("count(*) = 1", smoke.silver_sql(123, "Rabat"))
        self.assertIn("city = 'Rabat'", smoke.silver_sql(123, "Rabat"))
        self.assertIn("_is_deleted = true", smoke.silver_sql(123, deleted=True))

    def test_gold_uses_current_snapshot(self):
        self.assertIn("snapshot_date = current_date", smoke.gold_sql(123))
        self.assertIn("count_if(city = 'Rabat' AND total_orders = 0", smoke.gold_sql(123, "Rabat"))
        self.assertIn("total_spent = 0", smoke.gold_sql(123, "Rabat"))
        self.assertIn("avg_order_value = 0", smoke.gold_sql(123, "Rabat"))

    def test_wait_retries_until_expected_state(self):
        with patch.object(smoke, "trino_count", side_effect=[0, 1]) as query:
            result = smoke.wait_for("test", "SELECT 1", lambda n: n == 1, 2, 0.001)
        self.assertEqual(result["status"], "passed")
        self.assertEqual(query.call_count, 2)

    def test_wait_fails_when_state_never_observed(self):
        with patch.object(smoke, "trino_count", return_value=0):
            with self.assertRaises(TimeoutError):
                smoke.wait_for("test", "SELECT 1", lambda n: n == 1, 0.01, 0.001)


if __name__ == "__main__":
    unittest.main()
