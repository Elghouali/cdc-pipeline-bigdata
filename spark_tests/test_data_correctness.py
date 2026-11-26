"""Local Spark checks for Bronze replay and quarantine, Silver typed validation."""
import unittest
from decimal import Decimal

from pyspark.sql import SparkSession

from spark_jobs.bronze_job import classify_events, unseen_events
from spark_jobs.silver_job import extract_columns, validate_rows


class DataCorrectnessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.spark = (
            SparkSession.builder.master("local[2]")
            .appName("data-correctness-tests")
            .config("spark.ui.enabled", "false")
            .config("spark.sql.shuffle.partitions", "2")
            .getOrCreate()
        )
        cls.spark.sparkContext.setLogLevel("ERROR")

    @classmethod
    def tearDownClass(cls):
        cls.spark.stop()

    def test_replay_filter(self):
        schema = "kafka_topic STRING, kafka_partition INT, kafka_offset LONG"
        existing = self.spark.createDataFrame([("t", 0, 1)], schema)
        incoming = self.spark.createDataFrame(
            [("t", 0, 1), ("t", 0, 2), ("t", 0, 2), ("t", 1, 1)], schema
        )
        self.assertEqual(
            {(r.kafka_partition, r.kafka_offset) for r in unseen_events(incoming, existing).collect()},
            {(0, 2), (1, 1)},
        )

    def test_quarantine(self):
        schema = "op STRING, raw_payload STRING, source_table STRING, kafka_key STRING, before_payload STRING, after_payload STRING"
        df = self.spark.createDataFrame(
            [
                ("c", "{}", "customers", '{"id":1}', None, '{"id":1}'),
                ("x", "{}", "customers", '{"id":2}', None, '{"id":2}'),
                ("d", "{}", "customers", '{"id":3}', '{"id":3}', None),
                ("c", "{}", "customers", '{"id":4}', None, '{"id":5}'),
            ], schema
        )
        result = {r.kafka_key: r.rejection_reason for r in classify_events(df, "customers").collect()}
        self.assertIsNone(result['{"id":1}'])
        self.assertEqual(result['{"id":2}'], "invalid_operation")
        self.assertIsNone(result['{"id":3}'])
        self.assertEqual(result['{"id":4}'], "invalid_primary_key")

    def test_decimal_and_required_fields(self):
        schema = "op STRING, before_payload STRING, after_payload STRING, source_ts_ms LONG, kafka_partition INT, kafka_offset LONG"
        valid = self.spark.createDataFrame(
            [("c", None, '{"id":1,"order_id":2,"payment_date":0,"method":"wallet","amount":"0.10","status":"completed"}', 1, 0, 1)],
            schema,
        )
        parsed = extract_columns(valid, "payments")
        validate_rows(parsed, "payments")
        self.assertEqual(parsed.first().amount, Decimal("0.10"))
        bad = self.spark.createDataFrame(
            [("c", None, '{"id":1}', 1, 0, 1)], schema
        )
        with self.assertRaisesRegex(ValueError, "Invalid typed CDC"):
            validate_rows(extract_columns(bad, "payments"), "payments")

    def test_key_only_delete(self):
        schema = "op STRING, before_payload STRING, after_payload STRING, source_ts_ms LONG, kafka_partition INT, kafka_offset LONG"
        df = self.spark.createDataFrame(
            [("d", '{"id":1}', None, 1, 0, 1)], schema
        )
        validate_rows(extract_columns(df, "customers"), "customers")
