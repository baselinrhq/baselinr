"""
Pattern matcher for RCA.

Learns from historical RCA results to identify recurring patterns
and improve root cause identification over time.
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy import text
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)


class PatternMatcher:
    """
    Matches current anomalies to historical patterns.

    Learns from past RCA results that were confirmed or manually
    annotated to improve future root cause detection.
    """

    def __init__(
        self,
        engine: Engine,
        min_pattern_occurrences: int = 3,
        historical_window_days: int = 90,
    ):
        """
        Initialize pattern matcher.

        Args:
            engine: SQLAlchemy engine for querying
            min_pattern_occurrences: Minimum occurrences to consider a pattern
            historical_window_days: How far back to look for patterns
        """
        self.engine = engine
        self.min_pattern_occurrences = min_pattern_occurrences
        self.historical_window_days = historical_window_days

    def find_similar_incidents(
        self,
        table_name: str,
        column_name: Optional[str],
        metric_name: Optional[str],
        anomaly_type: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Find similar historical incidents.

        Args:
            table_name: Table with anomaly
            column_name: Column with anomaly
            metric_name: Metric that is anomalous
            anomaly_type: Type of anomaly (optional)

        Returns:
            List of similar incidents with their RCA results
        """
        # Query historical RCA results for similar anomalies
        query_parts = [
            """
            SELECT r.anomaly_id, r.table_name, r.column_name, r.metric_name,
                   r.analyzed_at, r.probable_causes, r.impact_analysis, r.metadata
            FROM baselinr_rca_results r
            WHERE r.table_name = :table_name
            AND r.analyzed_at >= :start_time
        """
        ]

        params: Dict[str, Any] = {
            "table_name": table_name,
            "start_time": datetime.utcnow() - timedelta(days=self.historical_window_days),
        }

        if column_name:
            query_parts.append("AND r.column_name = :column_name")
            params["column_name"] = column_name

        if metric_name:
            query_parts.append("AND r.metric_name = :metric_name")
            params["metric_name"] = metric_name

        query_parts.append("ORDER BY r.analyzed_at DESC LIMIT 50")

        query = text(" ".join(query_parts))

        similar_incidents = []

        try:
            with self.engine.connect() as conn:
                result = conn.execute(query, params)
                rows = result.fetchall()

                for row in rows:
                    probable_causes = json.loads(row[5]) if row[5] else []
                    impact_analysis = json.loads(row[6]) if row[6] else {}
                    metadata = json.loads(row[7]) if row[7] else {}

                    similar_incidents.append(
                        {
                            "anomaly_id": row[0],
                            "table_name": row[1],
                            "column_name": row[2],
                            "metric_name": row[3],
                            "analyzed_at": row[4],
                            "probable_causes": probable_causes,
                            "impact_analysis": impact_analysis,
                            "metadata": metadata,
                        }
                    )

        except Exception as e:
            logger.error(f"Error finding similar incidents: {e}")

        return similar_incidents

    def identify_recurring_patterns(
        self,
        table_name: str,
        column_name: Optional[str] = None,
        metric_name: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Identify recurring patterns in historical RCA results.

        Args:
            table_name: Table to analyze
            column_name: Optional column filter
            metric_name: Optional metric filter

        Returns:
            List of patterns with their frequency and typical causes
        """
        similar_incidents = self.find_similar_incidents(table_name, column_name, metric_name)

        if len(similar_incidents) < self.min_pattern_occurrences:
            logger.debug(
                f"Not enough historical data for pattern matching "
                f"(found {len(similar_incidents)}, need {self.min_pattern_occurrences})"
            )
            return []

        # Group by cause types and extract patterns
        cause_patterns: Dict[str, List[Dict[str, Any]]] = {}

        for incident in similar_incidents:
            causes = incident.get("probable_causes", [])

            # Get top cause (highest confidence)
            if causes:
                top_cause = max(causes, key=lambda c: c.get("confidence_score", 0))
                cause_type = top_cause.get("cause_type")

                if cause_type:
                    if cause_type not in cause_patterns:
                        cause_patterns[cause_type] = []

                    cause_patterns[cause_type].append(
                        {
                            "incident": incident,
                            "cause": top_cause,
                        }
                    )

        # Build pattern summaries
        patterns = []

        for cause_type, occurrences in cause_patterns.items():
            if len(occurrences) >= self.min_pattern_occurrences:
                # Calculate average confidence
                avg_confidence = sum(
                    occ["cause"].get("confidence_score", 0) for occ in occurrences
                ) / len(occurrences)

                # Extract common evidence
                evidence_summary = self._summarize_evidence(
                    [occ["cause"].get("evidence", {}) for occ in occurrences]
                )

                pattern = {
                    "cause_type": cause_type,
                    "occurrence_count": len(occurrences),
                    "avg_confidence": avg_confidence,
                    "first_seen": min(occ["incident"]["analyzed_at"] for occ in occurrences),
                    "last_seen": max(occ["incident"]["analyzed_at"] for occ in occurrences),
                    "evidence_summary": evidence_summary,
                    "sample_causes": [occ["cause"] for occ in occurrences[:3]],  # Top 3 examples
                }

                patterns.append(pattern)

        # Sort by occurrence count
        patterns.sort(key=lambda p: p["occurrence_count"], reverse=True)

        return patterns

    def boost_confidence_from_patterns(
        self,
        causes: List[Dict[str, Any]],
        table_name: str,
        column_name: Optional[str],
        metric_name: Optional[str],
    ) -> List[Dict[str, Any]]:
        """
        Boost confidence scores based on historical patterns.

        Args:
            causes: List of probable causes
            table_name: Table with anomaly
            column_name: Column with anomaly
            metric_name: Metric that is anomalous

        Returns:
            Updated causes with pattern-based confidence boosts
        """
        patterns = self.identify_recurring_patterns(table_name, column_name, metric_name)

        if not patterns:
            return causes

        # Build pattern lookup
        pattern_boost = {
            pattern["cause_type"]: min(0.3, pattern["occurrence_count"] * 0.05)
            for pattern in patterns
        }

        # Apply boosts
        updated_causes = []
        for cause in causes:
            cause_type = cause.get("cause_type")
            boost = pattern_boost.get(cause_type, 0.0)

            if boost > 0:
                original_confidence = cause.get("confidence_score", 0.0)
                boosted_confidence = min(1.0, original_confidence + boost)

                # Update cause
                updated_cause = cause.copy()
                updated_cause["confidence_score"] = boosted_confidence

                # Add evidence of pattern
                if "evidence" not in updated_cause:
                    updated_cause["evidence"] = {}

                updated_cause["evidence"]["historical_pattern"] = {
                    "found": True,
                    "occurrence_count": next(
                        (p["occurrence_count"] for p in patterns if p["cause_type"] == cause_type),
                        0,
                    ),
                    "confidence_boost": boost,
                }

                updated_causes.append(updated_cause)
            else:
                updated_causes.append(cause)

        return updated_causes

    def get_pattern_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about learned patterns.

        Returns:
            Dictionary with pattern statistics
        """
        query = text(
            """
            SELECT COUNT(*) as total_rca_results,
                   COUNT(DISTINCT table_name) as unique_tables,
                   COUNT(DISTINCT DATE(analyzed_at)) as days_with_data
            FROM baselinr_rca_results
            WHERE analyzed_at >= :start_time
        """
        )

        stats = {
            "total_rca_results": 0,
            "unique_tables": 0,
            "days_with_data": 0,
            "window_days": self.historical_window_days,
        }

        try:
            with self.engine.connect() as conn:
                result = conn.execute(
                    query,
                    {
                        "start_time": datetime.utcnow()
                        - timedelta(days=self.historical_window_days),
                    },
                )
                row = result.fetchone()

                if row:
                    stats["total_rca_results"] = row[0] or 0
                    stats["unique_tables"] = row[1] or 0
                    stats["days_with_data"] = row[2] or 0

        except Exception as e:
            logger.error(f"Error getting pattern statistics: {e}")

        return stats

    def _summarize_evidence(self, evidence_list: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Summarize common evidence across multiple incidents.

        Args:
            evidence_list: List of evidence dictionaries

        Returns:
            Summary of common evidence
        """
        if not evidence_list:
            return {}

        summary: Dict[str, Any] = {}

        # Find common keys
        common_keys = set(evidence_list[0].keys()) if evidence_list else set()
        for evidence in evidence_list[1:]:
            common_keys = common_keys.intersection(evidence.keys())

        # Calculate averages for numeric values
        for key in common_keys:
            values = []
            for evidence in evidence_list:
                value = evidence.get(key)
                if isinstance(value, (int, float)):
                    values.append(value)

            if values:
                summary[key] = {
                    "avg": sum(values) / len(values),
                    "min": min(values),
                    "max": max(values),
                    "count": len(values),
                }

        return summary

    def learn_from_feedback(
        self,
        anomaly_id: str,
        actual_cause: str,
        actual_cause_type: str,
        feedback_metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Learn from user feedback about actual root cause.

        This allows the system to improve over time as users confirm
        or correct RCA results.

        Args:
            anomaly_id: ID of the anomaly
            actual_cause: Description of actual cause
            actual_cause_type: Type of actual cause
            feedback_metadata: Additional feedback metadata
        """
        # Update RCA result with feedback
        query = text(
            """
            UPDATE baselinr_rca_results
            SET metadata = :metadata
            WHERE anomaly_id = :anomaly_id
        """
        )

        try:
            # Load existing metadata
            select_query = text(
                """
                SELECT metadata FROM baselinr_rca_results
                WHERE anomaly_id = :anomaly_id
            """
            )

            with self.engine.connect() as conn:
                result = conn.execute(select_query, {"anomaly_id": anomaly_id})
                row = result.fetchone()

                if row:
                    existing_metadata = json.loads(row[0]) if row[0] else {}

                    # Add feedback
                    existing_metadata["user_feedback"] = {
                        "actual_cause": actual_cause,
                        "actual_cause_type": actual_cause_type,
                        "feedback_timestamp": datetime.utcnow().isoformat(),
                        "additional_metadata": feedback_metadata or {},
                    }

                    # Update
                    conn.execute(
                        query,
                        {
                            "anomaly_id": anomaly_id,
                            "metadata": json.dumps(existing_metadata),
                        },
                    )
                    conn.commit()

                    logger.info(f"Recorded feedback for anomaly {anomaly_id}")

        except Exception as e:
            logger.error(f"Error recording feedback: {e}")
