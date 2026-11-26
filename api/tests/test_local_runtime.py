"""Local-pod telemetry and credential URL regression tests."""

from telemetry import render_local_metrics

from config import _database_url


def test_database_url_encodes_password(monkeypatch):
    monkeypatch.setenv("API_DB_PASSWORD", "fixture" + "@:/")
    assert _database_url().startswith("postgresql://cdc_api:fixture%40%3A%2F@")


def test_local_metrics_are_not_standalone_master_metrics():
    apps = {"bronze": [{"name": "cdc-bronze-ingestion"}]}
    connector = {"connector": {"state": "RUNNING"}, "tasks": [{"state": "RUNNING"}]}
    result = render_local_metrics(apps, connector, 123.0)
    assert 'cdc_spark_driver_active{layer="bronze"} 1' in result
    assert 'cdc_spark_driver_active{layer="silver"} 0' in result
    assert "cdc_spark_master_reachable" not in result
    assert "cdc_connector_healthy 1" in result
    assert "cdc_gold_last_success_timestamp_seconds 123.0" in result
