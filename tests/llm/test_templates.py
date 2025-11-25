"""Tests for template-based explanations."""

from baselinr.anomaly.detector import AnomalyResult
from baselinr.anomaly.anomaly_types import AnomalyType
from baselinr.drift.detector import ColumnDrift
from baselinr.llm.templates import (
    generate_anomaly_explanation,
    generate_drift_explanation,
    generate_schema_change_explanation,
)


def test_generate_drift_explanation():
    """Test drift explanation generation."""
    drift = ColumnDrift(
        column_name="order_amount",
        metric_name="mean",
        baseline_value=98.20,
        current_value=127.50,
        change_percent=30.0,
        drift_detected=True,
        drift_severity="high",
    )

    explanation = generate_drift_explanation(drift)
    assert "order_amount" in explanation
    assert "30.00" in explanation or "30" in explanation
    assert "high" in explanation.lower() or "significant" in explanation.lower()


def test_generate_anomaly_explanation():
    """Test anomaly explanation generation."""
    anomaly = AnomalyResult(
        anomaly_type=AnomalyType.CONTROL_LIMIT_BREACH,
        table_name="orders",
        schema_name=None,
        column_name="order_amount",
        metric_name="mean",
        expected_value=100.0,
        actual_value=150.0,
        deviation_score=2.5,
        severity="high",
        detection_method="control_limits",
    )

    explanation = generate_anomaly_explanation(anomaly)
    assert "orders" in explanation
    assert "order_amount" in explanation
    assert "high" in explanation.lower() or "significant" in explanation.lower()


def test_generate_schema_change_explanation():
    """Test schema change explanation generation."""
    explanation = generate_schema_change_explanation(
        change="Column added: new_column",
        table="orders",
        change_type="column_added",
        column="new_column",
    )

    assert "orders" in explanation
    assert "new_column" in explanation
    assert "added" in explanation.lower()

