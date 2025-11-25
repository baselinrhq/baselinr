"""
Prompt engineering for LLM explanations.

Constructs prompts for different alert types (drift, anomaly, schema change)
with appropriate context and technical details.
"""

from typing import Any, Dict

# System prompt template for data quality analyst persona
SYSTEM_PROMPT = (
    "You are a data quality analyst explaining anomalies to "
    "data engineers and business users.\n\n"
    "Your goal is to:\n"
    "1. Clearly explain what happened in plain English\n"
    "2. Provide context about why this might have occurred\n"
    "3. Suggest potential next steps or areas to investigate\n"
    "4. Be concise (2-4 sentences maximum)\n"
    "5. Avoid jargon unless necessary\n\n"
    "Format your response as a clear, actionable explanation."
)


def construct_drift_prompt(alert_data: Dict[str, Any]) -> str:
    """
    Construct prompt for drift detection alerts.

    Args:
        alert_data: Dictionary containing drift alert details:
            - table: Table name
            - column: Column name
            - metric: Metric name
            - baseline_value: Baseline metric value
            - current_value: Current metric value
            - change_percent: Percentage change
            - change_absolute: Absolute change
            - drift_severity: Severity level (low, medium, high)
            - baseline_timestamp: Timestamp of baseline
            - current_timestamp: Timestamp of current value
            - metadata: Additional metadata (optional)

    Returns:
        Formatted prompt string
    """
    table = alert_data.get("table", "unknown")
    column = alert_data.get("column", "unknown")
    metric = alert_data.get("metric", "unknown")
    baseline_value = alert_data.get("baseline_value")
    current_value = alert_data.get("current_value")
    change_percent = alert_data.get("change_percent")
    change_absolute = alert_data.get("change_absolute")
    severity = alert_data.get("drift_severity", "unknown")
    baseline_timestamp = alert_data.get("baseline_timestamp")
    current_timestamp = alert_data.get("current_timestamp")
    metadata = alert_data.get("metadata", {})

    prompt = f"""A data drift alert was detected:

Table: {table}
Column: {column}
Alert Type: Statistical Drift
Metric: {metric}
Severity: {severity.upper()}

Current value: {current_value}
Baseline value: {baseline_value}"""

    if change_percent is not None:
        prompt += f"\nChange: {change_percent:+.2f}%"
    elif change_absolute is not None:
        prompt += f"\nAbsolute change: {change_absolute:+.2f}"

    if baseline_timestamp and current_timestamp:
        prompt += f"\n\nBaseline time: {baseline_timestamp}"
        prompt += f"\nCurrent time: {current_timestamp}"

    # Add additional context from metadata
    if metadata:
        test_info = metadata.get("test", metadata.get("test_name"))
        if test_info:
            prompt += f"\nTest: {test_info}"

        p_value = metadata.get("p_value")
        if p_value is not None:
            prompt += f"\np-value: {p_value:.4f}"

        # Add distribution stats if available
        if "baseline_stats" in metadata:
            stats = metadata["baseline_stats"]
            prompt += f"\n\nBaseline statistics: {stats}"

        if "current_stats" in metadata:
            stats = metadata["current_stats"]
            prompt += f"\nCurrent statistics: {stats}"

    prompt += "\n\nExplain this drift in 2-4 clear sentences for a data engineer."

    return prompt


def construct_anomaly_prompt(alert_data: Dict[str, Any]) -> str:
    """
    Construct prompt for anomaly detection alerts.

    Args:
        alert_data: Dictionary containing anomaly alert details:
            - table: Table name
            - column: Column name
            - metric: Metric name
            - expected_value: Expected metric value
            - actual_value: Actual metric value
            - deviation_score: Deviation score
            - severity: Severity level (low, medium, high)
            - anomaly_type: Type of anomaly
            - detection_method: Detection method used
            - metadata: Additional metadata (optional)

    Returns:
        Formatted prompt string
    """
    table = alert_data.get("table", "unknown")
    column = alert_data.get("column", "unknown")
    metric = alert_data.get("metric", "unknown")
    expected_value = alert_data.get("expected_value")
    actual_value = alert_data.get("actual_value")
    deviation_score = alert_data.get("deviation_score")
    severity = alert_data.get("severity", "unknown")
    anomaly_type = alert_data.get("anomaly_type", "unknown")
    detection_method = alert_data.get("detection_method", "unknown")
    metadata = alert_data.get("metadata", {})

    prompt = f"""An anomaly was detected:

Table: {table}
Column: {column}
Metric: {metric}
Anomaly Type: {anomaly_type}
Detection Method: {detection_method}
Severity: {severity.upper()}

Expected value: {expected_value}
Actual value: {actual_value}"""

    if deviation_score is not None:
        prompt += f"\nDeviation: {deviation_score:.2f} standard deviations from expected"

    # Add method-specific context
    if detection_method == "control_limits":
        lcl = metadata.get("lower_control_limit")
        ucl = metadata.get("upper_control_limit")
        if lcl is not None and ucl is not None:
            prompt += f"\nControl limits: [{lcl:.2f}, {ucl:.2f}]"

    elif detection_method in ["iqr", "mad"]:
        historical_count = metadata.get("historical_values_count")
        if historical_count:
            prompt += f"\nBased on {historical_count} historical values"

    elif detection_method == "ewma":
        ewma_value = metadata.get("ewma_value")
        if ewma_value is not None:
            prompt += f"\nEWMA value: {ewma_value:.2f}"

    prompt += "\n\nExplain this anomaly in 2-4 clear sentences for a data engineer."

    return prompt


def construct_schema_change_prompt(alert_data: Dict[str, Any]) -> str:
    """
    Construct prompt for schema change alerts.

    Args:
        alert_data: Dictionary containing schema change details:
            - table: Table name
            - change_type: Type of change (column_added, column_removed, etc.)
            - column: Column name (if applicable)
            - old_type: Old column type (if applicable)
            - new_type: New column type (if applicable)
            - change_severity: Severity level
            - metadata: Additional metadata (optional)

    Returns:
        Formatted prompt string
    """
    table = alert_data.get("table", "unknown")
    change_type = alert_data.get("change_type", "unknown")
    column = alert_data.get("column")
    old_type = alert_data.get("old_type")
    new_type = alert_data.get("new_type")
    severity = alert_data.get("change_severity", alert_data.get("severity", "unknown"))

    prompt = f"""A schema change was detected:

Table: {table}
Change Type: {change_type}
Severity: {severity.upper()}"""

    if column:
        prompt += f"\nColumn: {column}"

    if old_type and new_type:
        prompt += f"\nType change: {old_type} → {new_type}"
    elif old_type:
        prompt += f"\nOld type: {old_type}"
    elif new_type:
        prompt += f"\nNew type: {new_type}"

    # Map change types to descriptions
    change_descriptions = {
        "column_added": "A new column was added to the table",
        "column_removed": "A column was removed from the table",
        "column_renamed": "A column was renamed",
        "type_changed": "A column's data type was changed",
        "partition_changed": "Table partitioning was modified",
    }

    description = change_descriptions.get(change_type, "A schema change occurred")
    prompt += f"\n\n{description}."

    prompt += (
        "\n\nExplain the impact of this schema change in 2-4 clear sentences for a data engineer."
    )

    return prompt


def get_system_prompt() -> str:
    """
    Get the system prompt for LLM explanations.

    Returns:
        System prompt string
    """
    return SYSTEM_PROMPT
