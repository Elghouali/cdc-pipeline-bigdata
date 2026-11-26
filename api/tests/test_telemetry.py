"""Prometheus status metrics contain fixed labels and reflect failed tasks."""

from telemetry import render_metrics


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
