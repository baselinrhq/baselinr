"""
Context enhancement for Baselinr chat.

Enriches tool responses with additional context and historical information.
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)


@dataclass
class ContextEnhancer:
    """Enhance tool responses with additional context."""

    engine: Engine
    config: Dict[str, Any]

    def enhance_drift_event(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Add context to drift event."""
        enhanced = event.copy()

        # Add historical comparison if possible
        if event.get("table_name") and event.get("column_name") and event.get("metric_name"):
            try:
                historical = self._get_historical_comparison(
                    table=event["table_name"],
                    column=event["column_name"],
                    metric=event["metric_name"],
                )
                if historical:
                    enhanced["historical_context"] = historical
            except Exception as e:
                logger.debug(f"Could not get historical context: {e}")

        # Add related events
        if event.get("table_name"):
            try:
                related = self._find_related_events(event)
                if related:
                    enhanced["related_events"] = related
            except Exception as e:
                logger.debug(f"Could not get related events: {e}")

        return enhanced

    def enhance_anomaly(self, anomaly: Dict[str, Any]) -> Dict[str, Any]:
        """Add context to anomaly."""
        enhanced = anomaly.copy()

        # Add severity assessment
        enhanced["severity_assessment"] = self._assess_anomaly_severity(anomaly)

        # Add remediation suggestions
        enhanced["suggested_actions"] = self._suggest_remediation(anomaly)

        return enhanced

    def enhance_table_profile(self, profile: Dict[str, Any]) -> Dict[str, Any]:
        """Add context to table profile."""
        enhanced = profile.copy()

        # Add health summary
        enhanced["health_summary"] = self._calculate_table_health(profile)

        # Add column risk assessment
        if profile.get("columns"):
            enhanced["column_risk_assessment"] = self._assess_column_risks(profile["columns"])

        return enhanced

    def _get_historical_comparison(
        self, table: str, column: str, metric: str, days: int = 30
    ) -> Optional[Dict[str, Any]]:
        """Get historical comparison for a metric."""
        from sqlalchemy import text

        results_table = self.config.get("results_table", "baselinr_results")
        start_date = datetime.utcnow() - timedelta(days=days)

        query = text(
            f"""
            SELECT metric_value, profiled_at
            FROM {results_table}
            WHERE dataset_name = :table
            AND column_name = :column
            AND metric_name = :metric
            AND profiled_at > :start_date
            ORDER BY profiled_at ASC
        """
        )

        try:
            with self.engine.connect() as conn:
                results = conn.execute(
                    query,
                    {
                        "table": table,
                        "column": column,
                        "metric": metric,
                        "start_date": start_date,
                    },
                ).fetchall()

            if not results:
                return None

            values = []
            for row in results:
                try:
                    values.append(float(row[0]))
                except (ValueError, TypeError):
                    continue

            if not values:
                return None

            import statistics

            return {
                "days_analyzed": days,
                "data_points": len(values),
                "historical_min": min(values),
                "historical_max": max(values),
                "historical_mean": statistics.mean(values),
                "historical_stddev": statistics.stdev(values) if len(values) > 1 else 0,
            }
        except Exception as e:
            logger.debug(f"Error getting historical comparison: {e}")
            return None

    def _find_related_events(
        self, event: Dict[str, Any], window_hours: int = 24
    ) -> List[Dict[str, Any]]:
        """Find events related to the given event."""
        from sqlalchemy import text

        events_table = self.config.get("events_table", "baselinr_events")
        table_name = event.get("table_name")

        if not table_name:
            return []

        # Look for events in the same time window
        event_time = event.get("timestamp")
        if isinstance(event_time, str):
            event_time = datetime.fromisoformat(event_time.replace("Z", "+00:00"))

        if not event_time:
            event_time = datetime.utcnow()

        start_time = event_time - timedelta(hours=window_hours)
        end_time = event_time + timedelta(hours=window_hours)

        query = text(
            f"""
            SELECT event_id, event_type, table_name, column_name,
                   metric_name, drift_severity, timestamp
            FROM {events_table}
            WHERE timestamp BETWEEN :start_time AND :end_time
            AND event_id != :exclude_id
            ORDER BY timestamp DESC
            LIMIT 10
        """
        )

        try:
            with self.engine.connect() as conn:
                results = conn.execute(
                    query,
                    {
                        "start_time": start_time,
                        "end_time": end_time,
                        "exclude_id": event.get("event_id", ""),
                    },
                ).fetchall()

            related = []
            for row in results:
                timestamp = row[6]
                if isinstance(timestamp, datetime):
                    timestamp = timestamp.isoformat()

                related.append(
                    {
                        "event_id": row[0],
                        "event_type": row[1],
                        "table_name": row[2],
                        "column_name": row[3],
                        "metric_name": row[4],
                        "severity": row[5],
                        "timestamp": timestamp,
                    }
                )

            return related
        except Exception as e:
            logger.debug(f"Error finding related events: {e}")
            return []

    def _assess_anomaly_severity(self, anomaly: Dict[str, Any]) -> Dict[str, Any]:
        """Assess the severity of an anomaly."""
        severity = anomaly.get("drift_severity", "").lower()
        change_percent = abs(anomaly.get("change_percent", 0))

        if severity == "high" or change_percent > 50:
            level = "critical"
            description = "Significant deviation requiring immediate attention"
            urgency = "high"
        elif severity == "medium" or change_percent > 20:
            level = "warning"
            description = "Notable change that should be investigated"
            urgency = "medium"
        else:
            level = "info"
            description = "Minor change within acceptable bounds"
            urgency = "low"

        return {
            "level": level,
            "description": description,
            "urgency": urgency,
            "change_percent": change_percent,
        }

    def _suggest_remediation(self, anomaly: Dict[str, Any]) -> List[str]:
        """Suggest remediation actions for an anomaly."""
        suggestions = []
        metric = anomaly.get("metric_name", "").lower()
        change_pct = anomaly.get("change_percent", 0)

        if "null" in metric:
            if change_pct > 0:
                suggestions.append("Check for upstream data quality issues")
                suggestions.append("Verify data pipeline integrity")
                suggestions.append("Review recent schema changes")
            else:
                suggestions.append("Verify data cleaning logic")
                suggestions.append("Check for duplicate removal processes")

        elif "distinct" in metric or "unique" in metric:
            suggestions.append("Check for duplicate records")
            suggestions.append("Review data deduplication processes")
            suggestions.append("Verify primary key integrity")

        elif "mean" in metric or "avg" in metric:
            suggestions.append("Check for outliers in source data")
            suggestions.append("Review data transformation logic")
            suggestions.append("Verify business rule changes")

        elif "count" in metric:
            if change_pct > 0:
                suggestions.append("Check for data duplication")
                suggestions.append("Verify data ingestion processes")
            else:
                suggestions.append("Check for data loss")
                suggestions.append("Verify filtering logic")
                suggestions.append("Review data retention policies")

        if not suggestions:
            suggestions.append("Review recent changes to data pipeline")
            suggestions.append("Check upstream data sources")
            suggestions.append("Consult with data owners")

        return suggestions

    def _calculate_table_health(self, profile: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate overall table health score."""
        columns = profile.get("columns", [])
        if not columns:
            return {"status": "unknown", "score": 0, "issues": ["No column data available"]}

        issues = []
        warnings = []

        total_null_ratio = 0.0
        columns_with_high_nulls = 0
        columns_with_low_distinct = 0

        for col in columns:
            metrics = col.get("metrics", {})

            # Check null ratio
            null_ratio = metrics.get("null_ratio")
            if null_ratio is not None:
                try:
                    null_ratio = float(null_ratio)
                    total_null_ratio += null_ratio
                    if null_ratio > 0.5:
                        issues.append(f"High null rate ({null_ratio:.1%}) in {col['column_name']}")
                        columns_with_high_nulls += 1
                    elif null_ratio > 0.2:
                        warnings.append(
                            f"Elevated null rate ({null_ratio:.1%}) in {col['column_name']}"
                        )
                except (ValueError, TypeError):
                    pass

            # Check unique ratio
            unique_ratio = metrics.get("unique_ratio")
            if unique_ratio is not None:
                try:
                    unique_ratio = float(unique_ratio)
                    if unique_ratio < 0.01 and unique_ratio > 0:
                        warnings.append(
                            f"Low uniqueness ({unique_ratio:.2%}) in {col['column_name']}"
                        )
                        columns_with_low_distinct += 1
                except (ValueError, TypeError):
                    pass

        # Calculate health score
        avg_null_ratio = total_null_ratio / len(columns) if columns else 0
        issue_penalty = len(issues) * 10
        warning_penalty = len(warnings) * 3

        score = max(0, min(100, 100 - issue_penalty - warning_penalty - (avg_null_ratio * 50)))

        if score >= 80:
            status = "healthy"
        elif score >= 60:
            status = "warning"
        else:
            status = "critical"

        return {
            "status": status,
            "score": round(score, 1),
            "issues": issues,
            "warnings": warnings,
            "column_count": len(columns),
            "columns_with_high_nulls": columns_with_high_nulls,
            "average_null_ratio": round(avg_null_ratio, 4),
        }

    def _assess_column_risks(self, columns: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Assess risk level for each column."""
        risks = []

        for col in columns:
            metrics = col.get("metrics", {})
            column_name = col.get("column_name", "unknown")
            risk_level = "low"
            risk_factors = []

            # Check null ratio
            null_ratio = metrics.get("null_ratio")
            if null_ratio is not None:
                try:
                    null_ratio = float(null_ratio)
                    if null_ratio > 0.5:
                        risk_level = "high"
                        risk_factors.append(f"Very high null rate: {null_ratio:.1%}")
                    elif null_ratio > 0.2:
                        risk_level = "medium" if risk_level != "high" else risk_level
                        risk_factors.append(f"High null rate: {null_ratio:.1%}")
                except (ValueError, TypeError):
                    pass

            # Check stddev (for numeric columns)
            stddev = metrics.get("stddev")
            mean = metrics.get("mean")
            if stddev is not None and mean is not None:
                try:
                    stddev = float(stddev)
                    mean = float(mean)
                    cv = stddev / abs(mean) if mean != 0 else 0
                    if cv > 2:
                        risk_level = "medium" if risk_level == "low" else risk_level
                        risk_factors.append(f"High variability (CV: {cv:.2f})")
                except (ValueError, TypeError):
                    pass

            if risk_factors:
                risks.append(
                    {
                        "column": column_name,
                        "risk_level": risk_level,
                        "factors": risk_factors,
                    }
                )

        # Sort by risk level
        risk_order = {"high": 0, "medium": 1, "low": 2}
        risks.sort(key=lambda x: risk_order.get(x["risk_level"], 3))

        return risks[:10]  # Return top 10 risky columns


def get_conversation_context(session, recent_messages: int = 5) -> str:
    """
    Build context summary from recent conversation.

    Args:
        session: Chat session
        recent_messages: Number of recent messages to summarize

    Returns:
        Context summary string
    """
    messages = session.get_history(last_n=recent_messages)
    if not messages:
        return ""

    tables_mentioned = set()
    columns_mentioned = set()

    for msg in messages:
        if msg.role == "user":
            content = msg.content.lower()
            # Extract table mentions
            for word in content.split():
                if "table" in word or "." in word:
                    tables_mentioned.add(word.strip(".,?!"))

        if msg.tool_results:
            for result in msg.tool_results:
                output = result.get("output", "")
                if isinstance(output, str):
                    try:
                        import json

                        data = json.loads(output)
                        if isinstance(data, dict):
                            if data.get("table_name"):
                                tables_mentioned.add(data["table_name"])
                            if data.get("column_name"):
                                columns_mentioned.add(data["column_name"])
                    except (json.JSONDecodeError, ValueError):
                        pass

    context_parts = []
    if tables_mentioned:
        context_parts.append(f"Tables discussed: {', '.join(list(tables_mentioned)[:5])}")
    if columns_mentioned:
        context_parts.append(f"Columns discussed: {', '.join(list(columns_mentioned)[:5])}")

    return "; ".join(context_parts)
