"""Spark-local regressions for Silver key ordering (no Kafka or Iceberg needed)."""
import unittest

from pyspark.sql import SparkSession

from spark_jobs.silver_job import dedup, merge_statement


class SilverOrderingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.spark = (
            SparkSession.builder.master("local[2]")
            .appName("silver-ordering-test")
            .config("spark.ui.enabled", "false")
            .config("spark.sql.shuffle.partitions", "2")
            .getOrCreate()
        )
        cls.spark.sparkContext.setLogLevel("ERROR")

    @classmethod
    def tearDownClass(cls):
        cls.spark.stop()

    def frame(self, rows):
        return self.spark.createDataFrame(
            rows, "id INT, _kafka_partition INT, _kafka_offset LONG, _source_ts_ms LONG, _op STRING"
        )

    def test_offset_wins_even_with_equal_or_reversed_timestamps(self):
        df = self.frame([(1, 0, 3, 100, "c"), (1, 0, 4, 100, "u"),
                         (1, 0, 5, 90, "d"), (2, 1, 1, 101, "c")])
        result = {row.id: (row._kafka_offset, row._op) for row in dedup(df, "id").collect()}
        self.assertEqual(result, {1: (5, "d"), 2: (1, "c")})

    def test_duplicate_replay_collapses(self):
        df = self.frame([(1, 0, 8, 100, "u"), (1, 0, 8, 100, "u")])
        self.assertEqual(dedup(df, "id").count(), 1)

    def test_partition_change_fails_closed(self):
        df = self.frame([(1, 0, 8, 100, "u"), (1, 1, 9, 101, "d")])
        with self.assertRaisesRegex(ValueError, "moved between"):
            dedup(df, "id")

    def test_null_offset_fails_closed(self):
        df = self.frame([(1, 0, None, 100, "u")])
        with self.assertRaisesRegex(ValueError, "missing valid"):
            dedup(df, "id")

    def test_merge_guards_replays_and_retains_delete_watermarks(self):
        sql = merge_statement("customers", "_test")
        self.assertIn("s._kafka_offset > t._kafka_offset", sql)
        self.assertIn("t._kafka_offset = s._kafka_offset", sql)
        self.assertIn("t._kafka_partition <> s._kafka_partition", sql)
        self.assertIn("WHEN NOT MATCHED THEN", sql)
        self.assertNotIn("WHEN NOT MATCHED AND", sql)


if __name__ == "__main__":
    unittest.main()
