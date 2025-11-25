"""
Template-based fallback explanations for alerts.

Provides deterministic, template-based explanations when LLM is unavailable
or disabled. These templates use technical metrics to generate clear explanations.
"""

from typing import Any, Optional


def generate_drift_explanation(drift: Any) -> str:
    """
    Generate template-based explanation for drift detection.

    Args:
        drift: ColumnDrift object with drift details

    Returns:
        Human-readable explanation string
    """
    # Try to get table name from drift object or metadata, fallback to generic
    table = (
        getattr(drift, "table_name", None)
        or getattr(drift, "table", None)
        or (
            drift.metadata.get("table_name")
            if hasattr(drift, "metadata") and drift.metadata
            else None
        )
        or "the table"
    )
    column = drift.column_name
    metric = drift.metric_name
    baseline = drift.baseline_value
    current = drift.current_value
    severity = drift.drift_severity

    # Format values appropriately
    if isinstance(baseline, (int, float)) and isinstance(current, (int, float)):
        baseline_str = f"{baseline:.2f}"
        current_str = f"{current:.2f}"
    else:
        baseline_str = str(baseline)
        current_str = str(current)

    # Build explanation
    explanation = f"Drift detected in {table}.{column}: {metric} changed"

    if drift.change_percent is not None:
        change_pct = drift.change_percent
        direction = "increased" if change_pct > 0 else "decreased"
        explanation += (
            f" by {abs(change_pct):.2f}% ({direction} from {baseline_str} to {current_str})"
        )
    elif drift.change_absolute is not None:
        change_abs = drift.change_absolute
        direction = "increased" if change_abs > 0 else "decreased"
        explanation += (
            f" by {abs(change_abs):.2f} ({direction} from {baseline_str} to {current_str})"
        )
    else:
        explanation += f" from {baseline_str} to {current_str}"

    # Add severity context
    if severity == "high":
        explanation += ". This is a significant change that may indicate a data quality issue, "
        explanation += "upstream pipeline change, or business event. Investigation recommended."
    elif severity == "medium":
        explanation += ". This change exceeds normal variation and may warrant investigation."
    else:
        explanation += ". This change is within expected variation but should be monitored."

    return explanation


def generate_anomaly_explanation(anomaly: Any) -> str:
    """
    Generate template-based explanation for anomaly detection.

    Args:
        anomaly: AnomalyResult object with anomaly details

    Returns:
        Human-readable explanation string
    """
    table = anomaly.table_name
    column = anomaly.column_name
    metric = anomaly.metric_name
    expected = anomaly.expected_value
    actual = anomaly.actual_value
    severity = anomaly.severity
    anomaly_type = (
        anomaly.anomaly_type.value
        if hasattr(anomaly.anomaly_type, "value")
        else str(anomaly.anomaly_type)
    )
    method = anomaly.detection_method

    # Format values
    if isinstance(expected, (int, float)) and isinstance(actual, (int, float)):
        expected_str = f"{expected:.2f}"
        actual_str = f"{actual:.2f}"
    else:
        expected_str = str(expected) if expected is not None else "N/A"
        actual_str = str(actual)

    # Build explanation
    explanation = f"Anomaly detected in {table}.{column}: {metric} value of {actual_str}"

    if expected is not None:
        if isinstance(expected, (int, float)) and isinstance(actual, (int, float)):
            deviation = abs(actual - expected)
            explanation += f" deviates from expected value of {expected_str} by {deviation:.2f}"
        else:
            explanation += f" differs from expected value of {expected_str}"

    # Add method-specific context
    if method == "control_limits":
        explanation += " (outside control limits)"
    elif method == "iqr":
        explanation += " (outside interquartile range)"
    elif method == "mad":
        explanation += " (outside median absolute deviation range)"
    elif method == "ewma":
        explanation += " (outside exponentially weighted moving average range)"
    elif method == "trend_seasonality":
        explanation += " (unexpected trend or seasonal pattern)"
    elif method == "regime_shift":
        explanation += " (regime shift detected)"

    # Add severity and type context
    if severity == "high":
        explanation += (
            f". This is a {anomaly_type} anomaly of high severity "
            "that requires immediate attention."
        )
    elif severity == "medium":
        explanation += (
            f". This {anomaly_type} anomaly is of medium severity and should be investigated."
        )
    else:
        explanation += f". This {anomaly_type} anomaly is of low severity but should be monitored."

    return explanation


def generate_schema_change_explanation(
    change: str,
    table: Optional[str] = None,
    change_type: Optional[str] = None,
    column: Optional[str] = None,
) -> str:
    """
    Generate template-based explanation for schema changes.

    Args:
        change: Change description string
        table: Table name (optional)
        change_type: Type of change (optional)
        column: Column name (optional)

    Returns:
        Human-readable explanation string
    """
    table_name = table or "the table"

    # Try to parse change string if it's in format "Column added: column_name"
    if ":" in change:
        parts = change.split(":", 1)
        if len(parts) == 2:
            change_desc = parts[0].strip()
            col_info = parts[1].strip()
        else:
            change_desc = change
            col_info = column or ""
    else:
        change_desc = change
        col_info = column or ""

    # Build explanation
    if "added" in change_desc.lower():
        explanation = f"A new column {col_info} was added to {table_name}."
        explanation += " This may require updates to downstream processes and data consumers."
    elif "removed" in change_desc.lower():
        explanation = f"Column {col_info} was removed from {table_name}."
        explanation += " This is a breaking change that may impact downstream processes."
    elif "changed" in change_desc.lower() or "type" in change_desc.lower():
        explanation = f"A column type change was detected in {table_name}."
        if col_info:
            explanation += f" Column: {col_info}"
        explanation += " This may require data type conversions in downstream processes."
    else:
        explanation = f"Schema change detected in {table_name}: {change_desc}"
        if col_info:
            explanation += f" ({col_info})"
        explanation += ". Review impact on downstream processes."

    return explanation
