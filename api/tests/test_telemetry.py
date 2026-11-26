"""Prometheus status metrics contain fixed labels and reflect failed tasks."""

from telemetry import gold_refresh_timestamp, render_metrics


def test_metrics_report_active_and_missing_layers():
    master = {
        "activeapps": [
            {"name": "cdc-bronze-ingestion", "state": "RUNNING", "cores": 2},
            {"name": "cdc-silver-transform", "state": "WAITING", "cores": 0},
        ]
    }
    connector = {
        "connector": {"state": "RUNNING"},
        "tasks": [{"state": "FAILED"}],
    }
    result = render_metrics(master, connector)
    assert 'cdc_spark_driver_active{layer="bronze"} 1' in result
    assert 'cdc_spark_driver_active{layer="silver"} 0' in result
    assert 'cdc_spark_driver_active{layer="gold"} 0' in result
    assert "cdc_connector_healthy 0" in result


def test_metrics_report_connector_running():
    connector = {
        "connector": {"state": "RUNNING"},
        "tasks": [{"state": "RUNNING"}],
    }
    result = render_metrics({}, connector)
    assert "cdc_spark_master_reachable 0" in result
    assert "cdc_connector_healthy 1" in result


def test_gold_refresh_timestamp(tmp_path):
    path = tmp_path / "gold-refresh"
    assert gold_refresh_timestamp(path) == 0.0
    path.write_text("nan")
    assert gold_refresh_timestamp(path) == 0.0
    path.write_text("12345.5")
    assert gold_refresh_timestamp(path) == 12345.5
    assert "cdc_gold_last_success_timestamp_seconds 12345.5" in render_metrics(
        {}, {}, gold_refresh_timestamp(path)
    )
