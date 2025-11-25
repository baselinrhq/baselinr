"""Tests for prompt construction."""

from baselinr.llm.prompts import (
    construct_anomaly_prompt,
    construct_drift_prompt,
    construct_schema_change_prompt,
    get_system_prompt,
)


def test_get_system_prompt():
    """Test system prompt retrieval."""
    prompt = get_system_prompt()
    assert isinstance(prompt, str)
    assert len(prompt) > 0
    assert "data quality" in prompt.lower() or "analyst" in prompt.lower()


def test_construct_drift_prompt():
    """Test drift prompt construction."""
    alert_data = {
        "table": "orders",
        "column": "order_amount",
        "metric": "mean",
        "baseline_value": 98.20,
        "current_value": 127.50,
        "change_percent": 30.0,
        "drift_severity": "high",
    }

    prompt = construct_drift_prompt(alert_data)
    assert "orders" in prompt
    assert "order_amount" in prompt
    assert "mean" in prompt
    assert "30" in prompt or "30.0" in prompt


def test_construct_anomaly_prompt():
    """Test anomaly prompt construction."""
    alert_data = {
        "table": "orders",
        "column": "order_amount",
        "metric": "mean",
        "expected_value": 100.0,
        "actual_value": 150.0,
        "deviation_score": 2.5,
        "severity": "high",
        "anomaly_type": "control_limit_breach",
        "detection_method": "control_limits",
    }

    prompt = construct_anomaly_prompt(alert_data)
    assert "orders" in prompt
    assert "order_amount" in prompt
    assert "anomaly" in prompt.lower()


def test_construct_schema_change_prompt():
    """Test schema change prompt construction."""
    alert_data = {
        "table": "orders",
        "change_type": "column_added",
        "column": "new_column",
        "change_severity": "medium",
    }

    prompt = construct_schema_change_prompt(alert_data)
    assert "orders" in prompt
    assert "schema change" in prompt.lower()
    assert "new_column" in prompt

