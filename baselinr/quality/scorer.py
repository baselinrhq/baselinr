"""
Quality scoring engine for Baselinr.

Calculates comprehensive data quality scores by combining
validation results, drift events, profiling metrics, and anomaly detection.
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from sqlalchemy import text
from sqlalchemy.engine import Engine

from ..config.schema import QualityScoringConfig
from ..events import QualityScoreDegraded, QualityScoreThresholdBreached
from .models import ColumnQualityScore, DataQualityScore, ScoreStatus

logger = logging.getLogger(__name__)


class QualityScorer:
    """Calculates data quality scores for tables."""

    def __init__(
        self,
        engine: Engine,
        config: QualityScoringConfig,
        results_table: str = "baselinr_results",
        validation_table: str = "baselinr_validation_results",
        events_table: str = "baselinr_events",
        runs_table: str = "baselinr_runs",
    ):
        """
        Initialize quality scorer.

        Args:
            engine: SQLAlchemy engine for database connection
            config: Quality scoring configuration
            results_table: Name of the profiling results table
            validation_table: Name of the validation results table
            events_table: Name of the events table
            runs_table: Name of the runs table
        """
        self.engine = engine
        self.config = config
        self.results_table = results_table
        self.validation_table = validation_table
        self.events_table = events_table
        self.runs_table = runs_table

    def calculate_table_score(
        self,
        table_name: str,
        schema_name: Optional[str] = None,
        run_id: Optional[str] = None,
        period_days: int = 7,
    ) -> DataQualityScore:
        """
        Calculate quality score for a table.

        Args:
            table_name: Name of the table
            schema_name: Optional schema name
            run_id: Optional run ID to associate with the score
            period_days: Number of days to look back for data

        Returns:
            DataQualityScore object
        """
        period_end = datetime.utcnow()
        period_start = period_end - timedelta(days=period_days)

        # Calculate component scores
        completeness_score = self._calculate_completeness_score(
            table_name, schema_name, period_start, period_end
        )
        validity_score = self._calculate_validity_score(
            table_name, schema_name, period_start, period_end
        )
        consistency_score = self._calculate_consistency_score(
            table_name, schema_name, period_start, period_end
        )
        freshness_score = self._calculate_freshness_score(table_name, schema_name)
        uniqueness_score = self._calculate_uniqueness_score(
            table_name, schema_name, period_start, period_end
        )
        accuracy_score = self._calculate_accuracy_score(
            table_name, schema_name, period_start, period_end
        )

        # Calculate overall score using weighted average
        weights = self.config.weights
        overall_score = (
            completeness_score * weights.completeness
            + validity_score * weights.validity
            + consistency_score * weights.consistency
            + freshness_score * weights.freshness
            + uniqueness_score * weights.uniqueness
            + accuracy_score * weights.accuracy
        ) / 100.0

        # Determine status
        thresholds = self.config.thresholds
        if overall_score >= thresholds.healthy:
            status = ScoreStatus.HEALTHY.value
        elif overall_score >= thresholds.warning:
            status = ScoreStatus.WARNING.value
        else:
            status = ScoreStatus.CRITICAL.value

        # Count issues
        total_issues, critical_issues, warnings = self._count_issues(
            table_name, schema_name, period_start, period_end
        )

        return DataQualityScore(
            overall_score=round(overall_score, 2),
            completeness_score=round(completeness_score, 2),
            validity_score=round(validity_score, 2),
            consistency_score=round(consistency_score, 2),
            freshness_score=round(freshness_score, 2),
            uniqueness_score=round(uniqueness_score, 2),
            accuracy_score=round(accuracy_score, 2),
            status=status,
            total_issues=total_issues,
            critical_issues=critical_issues,
            warnings=warnings,
            table_name=table_name,
            schema_name=schema_name,
            run_id=run_id,
            calculated_at=period_end,
            period_start=period_start,
            period_end=period_end,
        )

    def _calculate_completeness_score(
        self,
        table_name: str,
        schema_name: Optional[str],
        period_start: datetime,
        period_end: datetime,
    ) -> float:
        """Calculate completeness score based on null ratios."""
        conditions = ["dataset_name = :table_name"]
        params: Dict[str, Any] = {"table_name": table_name}

        if schema_name:
            conditions.append("schema_name = :schema_name")
            params["schema_name"] = schema_name
        else:
            conditions.append("schema_name IS NULL")

        conditions.append("metric_name = 'null_ratio'")
        conditions.append("profiled_at >= :period_start")
        conditions.append("profiled_at <= :period_end")
        params["period_start"] = period_start
        params["period_end"] = period_end

        where_clause = " AND ".join(conditions)

        query = text(
            f"""
            SELECT AVG(CAST(metric_value AS FLOAT))
            FROM {self.results_table}
            WHERE {where_clause}
        """
        )

        try:
            with self.engine.connect() as conn:
                result = conn.execute(query, params).fetchone()
                if result and result[0] is not None:
                    avg_null_ratio = float(result[0])
                    # Convert null ratio (0-1) to completeness score (0-100)
                    # Lower null ratio = higher completeness
                    completeness_score = max(0.0, min(100.0, (1.0 - avg_null_ratio) * 100.0))
                    return completeness_score
        except Exception as e:
            logger.warning(f"Error calculating completeness score: {e}")

        # Default: assume good completeness if no data
        return 100.0

    def _calculate_validity_score(
        self,
        table_name: str,
        schema_name: Optional[str],
        period_start: datetime,
        period_end: datetime,
    ) -> float:
        """Calculate validity score based on validation rule pass rate."""
        conditions = ["table_name = :table_name"]
        params: Dict[str, Any] = {"table_name": table_name}

        if schema_name:
            conditions.append("schema_name = :schema_name")
            params["schema_name"] = schema_name
        else:
            conditions.append("schema_name IS NULL")

        conditions.append("validated_at >= :period_start")
        conditions.append("validated_at <= :period_end")
        params["period_start"] = period_start
        params["period_end"] = period_end

        where_clause = " AND ".join(conditions)

        query = text(
            f"""
            SELECT
                COUNT(*) as total_rules,
                SUM(CASE WHEN passed = TRUE THEN 1 ELSE 0 END) as passed_rules
            FROM {self.validation_table}
            WHERE {where_clause}
        """
        )

        try:
            with self.engine.connect() as conn:
                result = conn.execute(query, params).fetchone()
                if result and result[0] and result[0] > 0:
                    total_rules = int(result[0])
                    passed_rules = int(result[1]) if result[1] else 0
                    validity_score = (passed_rules / total_rules) * 100.0
                    return max(0.0, min(100.0, validity_score))
        except Exception as e:
            logger.warning(f"Error calculating validity score: {e}")

        # Default: assume perfect validity if no validation rules
        return 100.0

    def _calculate_consistency_score(
        self,
        table_name: str,
        schema_name: Optional[str],
        period_start: datetime,
        period_end: datetime,
    ) -> float:
        """Calculate consistency score based on drift events and schema stability."""
        conditions = ["table_name = :table_name"]
        params: Dict[str, Any] = {"table_name": table_name}

        conditions.append("event_type = 'drift_detected'")
        conditions.append("timestamp >= :period_start")
        conditions.append("timestamp <= :period_end")
        params["period_start"] = period_start
        params["period_end"] = period_end

        where_clause = " AND ".join(conditions)

        query = text(
            f"""
            SELECT drift_severity, COUNT(*) as count
            FROM {self.events_table}
            WHERE {where_clause}
            GROUP BY drift_severity
        """
        )

        # Severity weights
        severity_weights = {"high": 10.0, "medium": 5.0, "low": 2.0}

        drift_penalty = 0.0
        try:
            with self.engine.connect() as conn:
                results = conn.execute(query, params).fetchall()
                for row in results:
                    severity = str(row[0]).lower() if row[0] else "low"
                    count = int(row[1])
                    weight = severity_weights.get(severity, 2.0)
                    drift_penalty += weight * count
        except Exception as e:
            logger.warning(f"Error calculating consistency score: {e}")

        # Get schema stability from profiling results (column_stability_score)
        schema_stability = 1.0
        try:
            stability_query = text(
                f"""
                SELECT AVG(CAST(metric_value AS FLOAT))
                FROM {self.results_table}
                WHERE dataset_name = :table_name
                  AND metric_name = 'column_stability_score'
                  AND profiled_at >= :period_start
                  AND profiled_at <= :period_end
            """
            )
            with self.engine.connect() as conn:
                result = conn.execute(
                    stability_query,
                    {
                        "table_name": table_name,
                        "period_start": period_start,
                        "period_end": period_end,
                    },
                ).fetchone()
                if result and result[0] is not None:
                    schema_stability = float(result[0])
        except Exception as e:
            logger.debug(f"Could not get schema stability: {e}")

        # Calculate consistency: max(0, 100 - drift_penalty) * schema_stability
        consistency_score = max(0.0, min(100.0, (100.0 - drift_penalty) * schema_stability))
        return consistency_score

    def _calculate_freshness_score(self, table_name: str, schema_name: Optional[str]) -> float:
        """Calculate freshness score based on time since last profile."""
        conditions = ["dataset_name = :table_name"]
        params: Dict[str, Any] = {"table_name": table_name}

        if schema_name:
            conditions.append("schema_name = :schema_name")
            params["schema_name"] = schema_name
        else:
            conditions.append("schema_name IS NULL")

        where_clause = " AND ".join(conditions)

        query = text(
            f"""
            SELECT MAX(profiled_at) as last_profiled
            FROM {self.runs_table}
            WHERE {where_clause}
        """
        )

        try:
            with self.engine.connect() as conn:
                result = conn.execute(query, params).fetchone()
                if result and result[0]:
                    last_profiled = result[0]
                    if isinstance(last_profiled, str):
                        last_profiled = datetime.fromisoformat(last_profiled.replace("Z", "+00:00"))
                    elif not isinstance(last_profiled, datetime):
                        return 0.0

                    hours_since_update = (
                        datetime.utcnow() - last_profiled
                    ).total_seconds() / 3600.0

                    freshness = self.config.freshness
                    if hours_since_update <= freshness.excellent:
                        return 100.0
                    elif hours_since_update <= freshness.good:
                        return 80.0
                    elif hours_since_update <= freshness.acceptable:
                        return 60.0
                    else:
                        # Linear decay after acceptable threshold
                        decay_rate = 10.0 / 24.0  # 10 points per day
                        hours_over = hours_since_update - freshness.acceptable
                        score = 60.0 - (hours_over * decay_rate)
                        return max(0.0, score)
        except Exception as e:
            logger.warning(f"Error calculating freshness score: {e}")

        # Default: assume stale if no data
        return 0.0

    def _calculate_uniqueness_score(
        self,
        table_name: str,
        schema_name: Optional[str],
        period_start: datetime,
        period_end: datetime,
    ) -> float:
        """Calculate uniqueness score based on unique ratios."""
        conditions = ["dataset_name = :table_name"]
        params: Dict[str, Any] = {"table_name": table_name}

        if schema_name:
            conditions.append("schema_name = :schema_name")
            params["schema_name"] = schema_name
        else:
            conditions.append("schema_name IS NULL")

        conditions.append("metric_name = 'unique_ratio'")
        conditions.append("profiled_at >= :period_start")
        conditions.append("profiled_at <= :period_end")
        params["period_start"] = period_start
        params["period_end"] = period_end

        where_clause = " AND ".join(conditions)

        query = text(
            f"""
            SELECT AVG(CAST(metric_value AS FLOAT))
            FROM {self.results_table}
            WHERE {where_clause}
        """
        )

        try:
            with self.engine.connect() as conn:
                result = conn.execute(query, params).fetchone()
                if result and result[0] is not None:
                    avg_unique_ratio = float(result[0])
                    # Convert unique ratio (0-1) to uniqueness score (0-100)
                    uniqueness_score = avg_unique_ratio * 100.0
                    return max(0.0, min(100.0, uniqueness_score))
        except Exception as e:
            logger.warning(f"Error calculating uniqueness score: {e}")

        # Default: assume good uniqueness if no data
        return 100.0

    def _calculate_accuracy_score(
        self,
        table_name: str,
        schema_name: Optional[str],
        period_start: datetime,
        period_end: datetime,
    ) -> float:
        """Calculate accuracy score based on anomaly detection."""
        conditions = ["table_name = :table_name"]
        params: Dict[str, Any] = {"table_name": table_name}

        conditions.append("event_type = 'AnomalyDetected'")
        conditions.append("timestamp >= :period_start")
        conditions.append("timestamp <= :period_end")
        params["period_start"] = period_start
        params["period_end"] = period_end

        where_clause = " AND ".join(conditions)

        query = text(
            f"""
            SELECT COUNT(*) as anomaly_count
            FROM {self.events_table}
            WHERE {where_clause}
        """
        )

        anomaly_penalty = 0.0
        try:
            with self.engine.connect() as conn:
                result = conn.execute(query, params).fetchone()
                if result and result[0]:
                    anomaly_count = int(result[0])
                    # 5 points per anomaly, max 100 points penalty
                    anomaly_penalty = min(100.0, anomaly_count * 5.0)
        except Exception as e:
            logger.warning(f"Error calculating accuracy score: {e}")

        # Calculate accuracy: 100 - anomaly_penalty
        accuracy_score = max(0.0, 100.0 - anomaly_penalty)
        return accuracy_score

    def _count_issues(
        self,
        table_name: str,
        schema_name: Optional[str],
        period_start: datetime,
        period_end: datetime,
    ) -> tuple[int, int, int]:
        """
        Count total issues, critical issues, and warnings.

        Returns:
            Tuple of (total_issues, critical_issues, warnings)
        """
        total_issues = 0
        critical_issues = 0
        warnings = 0

        # Count validation failures
        try:
            validation_conditions = ["table_name = :table_name", "passed = FALSE"]
            validation_params: Dict[str, Any] = {"table_name": table_name}

            if schema_name:
                validation_conditions.append("schema_name = :schema_name")
                validation_params["schema_name"] = schema_name
            else:
                validation_conditions.append("schema_name IS NULL")

            validation_conditions.append("validated_at >= :period_start")
            validation_conditions.append("validated_at <= :period_end")
            validation_params["period_start"] = period_start
            validation_params["period_end"] = period_end

            validation_where_clause = " AND ".join(validation_conditions)

            query = text(
                f"""
                SELECT
                    COUNT(*) as total,
                    SUM(CASE WHEN severity = 'high' THEN 1 ELSE 0 END) as critical,
                    SUM(CASE WHEN severity IN ('medium', 'low') THEN 1 ELSE 0 END) as warning
                FROM {self.validation_table}
                WHERE {validation_where_clause}
            """
            )

            with self.engine.connect() as conn:
                result = conn.execute(query, validation_params).fetchone()
                if result:
                    total_issues += int(result[0]) if result[0] else 0
                    critical_issues += int(result[1]) if result[1] else 0
                    warnings += int(result[2]) if result[2] else 0
        except Exception as e:
            logger.debug(f"Error counting validation issues: {e}")

        # Count high-severity drift events
        try:
            drift_conditions = [
                "table_name = :table_name",
                "event_type = 'drift_detected'",
                "drift_severity = 'high'",
            ]
            drift_params: Dict[str, Any] = {"table_name": table_name}

            drift_conditions.append("timestamp >= :period_start")
            drift_conditions.append("timestamp <= :period_end")
            drift_params["period_start"] = period_start
            drift_params["period_end"] = period_end

            drift_where_clause = " AND ".join(drift_conditions)

            query = text(
                f"""
                SELECT COUNT(*) as count
                FROM {self.events_table}
                WHERE {drift_where_clause}
            """
            )

            with self.engine.connect() as conn:
                result = conn.execute(query, drift_params).fetchone()
                if result and result[0]:
                    critical_issues += int(result[0])
                    total_issues += int(result[0])
        except Exception as e:
            logger.debug(f"Error counting drift issues: {e}")

        return (total_issues, critical_issues, warnings)

    def compare_scores(
        self,
        current: DataQualityScore,
        previous: Optional[DataQualityScore],
    ) -> Dict[str, Any]:
        """
        Compare two scores and calculate trend.

        Args:
            current: Current quality score
            previous: Previous quality score (optional)

        Returns:
            Dictionary with:
            - trend: "improving", "degrading", or "stable"
            - percentage_change: float (positive for improvement)
            - component_changes: dict of component -> change
        """
        if previous is None:
            return {
                "trend": "stable",
                "percentage_change": 0.0,
                "component_changes": {},
            }

        # Calculate overall percentage change
        if previous.overall_score == 0:
            percentage_change = 100.0 if current.overall_score > 0 else 0.0
        else:
            percentage_change = (
                (current.overall_score - previous.overall_score) / previous.overall_score * 100.0
            )

        # Determine trend
        if percentage_change > 1.0:
            trend = "improving"
        elif percentage_change < -1.0:
            trend = "degrading"
        else:
            trend = "stable"

        # Calculate per-component changes
        component_changes = {
            "completeness": current.completeness_score - previous.completeness_score,
            "validity": current.validity_score - previous.validity_score,
            "consistency": current.consistency_score - previous.consistency_score,
            "freshness": current.freshness_score - previous.freshness_score,
            "uniqueness": current.uniqueness_score - previous.uniqueness_score,
            "accuracy": current.accuracy_score - previous.accuracy_score,
        }

        return {
            "trend": trend,
            "percentage_change": round(percentage_change, 2),
            "component_changes": component_changes,
        }

    def calculate_column_score(
        self,
        table_name: str,
        column_name: str,
        schema_name: Optional[str] = None,
        run_id: Optional[str] = None,
        period_days: int = 7,
    ) -> ColumnQualityScore:
        """
        Calculate quality score for a specific column.

        Args:
            table_name: Name of the table
            column_name: Name of the column
            schema_name: Optional schema name
            run_id: Optional run ID to associate with the score
            period_days: Number of days to look back for data

        Returns:
            ColumnQualityScore object
        """
        period_end = datetime.utcnow()
        period_start = period_end - timedelta(days=period_days)

        # Calculate component scores for the column
        completeness_score = self._calculate_column_completeness_score(
            table_name, column_name, schema_name, period_start, period_end
        )
        validity_score = self._calculate_column_validity_score(
            table_name, column_name, schema_name, period_start, period_end
        )
        consistency_score = self._calculate_column_consistency_score(
            table_name, column_name, schema_name, period_start, period_end
        )
        freshness_score = self._calculate_column_freshness_score(
            table_name, column_name, schema_name
        )
        uniqueness_score = self._calculate_column_uniqueness_score(
            table_name, column_name, schema_name, period_start, period_end
        )
        accuracy_score = self._calculate_column_accuracy_score(
            table_name, column_name, schema_name, period_start, period_end
        )

        # Calculate overall score using weighted average
        weights = self.config.weights
        overall_score = (
            completeness_score * weights.completeness
            + validity_score * weights.validity
            + consistency_score * weights.consistency
            + freshness_score * weights.freshness
            + uniqueness_score * weights.uniqueness
            + accuracy_score * weights.accuracy
        ) / 100.0

        # Determine status
        thresholds = self.config.thresholds
        if overall_score >= thresholds.healthy:
            status = ScoreStatus.HEALTHY.value
        elif overall_score >= thresholds.warning:
            status = ScoreStatus.WARNING.value
        else:
            status = ScoreStatus.CRITICAL.value

        return ColumnQualityScore(
            overall_score=round(overall_score, 2),
            completeness_score=round(completeness_score, 2),
            validity_score=round(validity_score, 2),
            consistency_score=round(consistency_score, 2),
            freshness_score=round(freshness_score, 2),
            uniqueness_score=round(uniqueness_score, 2),
            accuracy_score=round(accuracy_score, 2),
            status=status,
            table_name=table_name,
            schema_name=schema_name,
            column_name=column_name,
            run_id=run_id,
            calculated_at=period_end,
            period_start=period_start,
            period_end=period_end,
        )

    def _calculate_column_completeness_score(
        self,
        table_name: str,
        column_name: str,
        schema_name: Optional[str],
        period_start: datetime,
        period_end: datetime,
    ) -> float:
        """Calculate completeness score for a column based on null ratio."""
        conditions = [
            "dataset_name = :table_name",
            "column_name = :column_name",
            "metric_name = 'null_ratio'",
            "profiled_at >= :period_start",
            "profiled_at <= :period_end",
        ]
        params: Dict[str, Any] = {
            "table_name": table_name,
            "column_name": column_name,
            "period_start": period_start,
            "period_end": period_end,
        }

        if schema_name:
            conditions.append("schema_name = :schema_name")
            params["schema_name"] = schema_name
        else:
            conditions.append("schema_name IS NULL")

        where_clause = " AND ".join(conditions)

        query = text(
            f"""
            SELECT AVG(CAST(metric_value AS FLOAT))
            FROM {self.results_table}
            WHERE {where_clause}
        """
        )

        try:
            with self.engine.connect() as conn:
                result = conn.execute(query, params).fetchone()
                if result and result[0] is not None:
                    null_ratio = float(result[0])
                    completeness_score = max(0.0, min(100.0, (1.0 - null_ratio) * 100.0))
                    return completeness_score
        except Exception as e:
            logger.warning(f"Error calculating column completeness score: {e}")

        return 100.0

    def _calculate_column_validity_score(
        self,
        table_name: str,
        column_name: str,
        schema_name: Optional[str],
        period_start: datetime,
        period_end: datetime,
    ) -> float:
        """Calculate validity score for a column based on validation rule pass rate."""
        conditions = [
            "table_name = :table_name",
            "column_name = :column_name",
            "validated_at >= :period_start",
            "validated_at <= :period_end",
        ]
        params: Dict[str, Any] = {
            "table_name": table_name,
            "column_name": column_name,
            "period_start": period_start,
            "period_end": period_end,
        }

        if schema_name:
            conditions.append("schema_name = :schema_name")
            params["schema_name"] = schema_name
        else:
            conditions.append("schema_name IS NULL")

        where_clause = " AND ".join(conditions)

        query = text(
            f"""
            SELECT
                COUNT(*) as total_rules,
                SUM(CASE WHEN passed = TRUE THEN 1 ELSE 0 END) as passed_rules
            FROM {self.validation_table}
            WHERE {where_clause}
        """
        )

        try:
            with self.engine.connect() as conn:
                result = conn.execute(query, params).fetchone()
                if result and result[0] and result[0] > 0:
                    total_rules = int(result[0])
                    passed_rules = int(result[1]) if result[1] else 0
                    validity_score = (passed_rules / total_rules) * 100.0
                    return max(0.0, min(100.0, validity_score))
        except Exception as e:
            logger.warning(f"Error calculating column validity score: {e}")

        return 100.0

    def _calculate_column_consistency_score(
        self,
        table_name: str,
        column_name: str,
        schema_name: Optional[str],
        period_start: datetime,
        period_end: datetime,
    ) -> float:
        """Calculate consistency score for a column based on drift events."""
        conditions = [
            "table_name = :table_name",
            "column_name = :column_name",
            "event_type = 'drift_detected'",
            "timestamp >= :period_start",
            "timestamp <= :period_end",
        ]
        params: Dict[str, Any] = {
            "table_name": table_name,
            "column_name": column_name,
            "period_start": period_start,
            "period_end": period_end,
        }

        where_clause = " AND ".join(conditions)

        query = text(
            f"""
            SELECT drift_severity, COUNT(*) as count
            FROM {self.events_table}
            WHERE {where_clause}
            GROUP BY drift_severity
        """
        )

        severity_weights = {"high": 10.0, "medium": 5.0, "low": 2.0}
        drift_penalty = 0.0

        try:
            with self.engine.connect() as conn:
                results = conn.execute(query, params).fetchall()
                for row in results:
                    severity = str(row[0]).lower() if row[0] else "low"
                    count = int(row[1])
                    weight = severity_weights.get(severity, 2.0)
                    drift_penalty += weight * count
        except Exception as e:
            logger.warning(f"Error calculating column consistency score: {e}")

        # Get column stability from profiling results
        schema_stability = 1.0
        try:
            stability_query = text(
                f"""
                SELECT AVG(CAST(metric_value AS FLOAT))
                FROM {self.results_table}
                WHERE dataset_name = :table_name
                  AND column_name = :column_name
                  AND metric_name = 'column_stability_score'
                  AND profiled_at >= :period_start
                  AND profiled_at <= :period_end
            """
            )
            with self.engine.connect() as conn:
                result = conn.execute(
                    stability_query,
                    {
                        "table_name": table_name,
                        "column_name": column_name,
                        "period_start": period_start,
                        "period_end": period_end,
                    },
                ).fetchone()
                if result and result[0] is not None:
                    schema_stability = float(result[0])
        except Exception as e:
            logger.debug(f"Could not get column stability: {e}")

        consistency_score = max(0.0, min(100.0, (100.0 - drift_penalty) * schema_stability))
        return consistency_score

    def _calculate_column_freshness_score(
        self, table_name: str, column_name: str, schema_name: Optional[str]
    ) -> float:
        """Calculate freshness score for a column based on time since last profile."""
        # Column freshness is same as table freshness
        return self._calculate_freshness_score(table_name, schema_name)

    def _calculate_column_uniqueness_score(
        self,
        table_name: str,
        column_name: str,
        schema_name: Optional[str],
        period_start: datetime,
        period_end: datetime,
    ) -> float:
        """Calculate uniqueness score for a column based on unique ratio."""
        conditions = [
            "dataset_name = :table_name",
            "column_name = :column_name",
            "metric_name = 'unique_ratio'",
            "profiled_at >= :period_start",
            "profiled_at <= :period_end",
        ]
        params: Dict[str, Any] = {
            "table_name": table_name,
            "column_name": column_name,
            "period_start": period_start,
            "period_end": period_end,
        }

        if schema_name:
            conditions.append("schema_name = :schema_name")
            params["schema_name"] = schema_name
        else:
            conditions.append("schema_name IS NULL")

        where_clause = " AND ".join(conditions)

        query = text(
            f"""
            SELECT AVG(CAST(metric_value AS FLOAT))
            FROM {self.results_table}
            WHERE {where_clause}
        """
        )

        try:
            with self.engine.connect() as conn:
                result = conn.execute(query, params).fetchone()
                if result and result[0] is not None:
                    unique_ratio = float(result[0])
                    uniqueness_score = unique_ratio * 100.0
                    return max(0.0, min(100.0, uniqueness_score))
        except Exception as e:
            logger.warning(f"Error calculating column uniqueness score: {e}")

        return 100.0

    def _calculate_column_accuracy_score(
        self,
        table_name: str,
        column_name: str,
        schema_name: Optional[str],
        period_start: datetime,
        period_end: datetime,
    ) -> float:
        """Calculate accuracy score for a column based on anomaly detection."""
        conditions = [
            "table_name = :table_name",
            "column_name = :column_name",
            "event_type = 'AnomalyDetected'",
            "timestamp >= :period_start",
            "timestamp <= :period_end",
        ]
        params: Dict[str, Any] = {
            "table_name": table_name,
            "column_name": column_name,
            "period_start": period_start,
            "period_end": period_end,
        }

        where_clause = " AND ".join(conditions)

        query = text(
            f"""
            SELECT COUNT(*) as anomaly_count
            FROM {self.events_table}
            WHERE {where_clause}
        """
        )

        anomaly_penalty = 0.0
        try:
            with self.engine.connect() as conn:
                result = conn.execute(query, params).fetchone()
                if result and result[0]:
                    anomaly_count = int(result[0])
                    anomaly_penalty = min(100.0, anomaly_count * 5.0)
        except Exception as e:
            logger.warning(f"Error calculating column accuracy score: {e}")

        accuracy_score = max(0.0, 100.0 - anomaly_penalty)
        return accuracy_score

    def analyze_score_trend(
        self,
        scores: list[DataQualityScore],
        min_periods: int = 2,
    ) -> Dict[str, Any]:
        """
        Analyze trend in historical scores.

        Args:
            scores: List of historical DataQualityScore objects (ordered by calculated_at DESC)
            min_periods: Minimum number of periods required for trend analysis

        Returns:
            Dictionary with:
            - direction: "improving", "degrading", or "stable"
            - rate_of_change: float (percentage change per period)
            - confidence: float (0-1, based on consistency of trend)
            - periods_analyzed: int
            - overall_change: float (total percentage change)
        """
        if len(scores) < min_periods:
            return {
                "direction": "stable",
                "rate_of_change": 0.0,
                "confidence": 0.0,
                "periods_analyzed": len(scores),
                "overall_change": 0.0,
            }

        # Sort by calculated_at ascending (oldest first)
        sorted_scores = sorted(scores, key=lambda s: s.calculated_at)

        # Calculate overall change
        first_score = sorted_scores[0].overall_score
        last_score = sorted_scores[-1].overall_score

        if first_score == 0:
            overall_change = 100.0 if last_score > 0 else 0.0
        else:
            overall_change = ((last_score - first_score) / first_score) * 100.0

        # Calculate rate of change per period
        periods = len(sorted_scores) - 1
        rate_of_change = overall_change / periods if periods > 0 else 0.0

        # Determine direction
        if rate_of_change > 1.0:
            direction = "improving"
        elif rate_of_change < -1.0:
            direction = "degrading"
        else:
            direction = "stable"

        # Calculate confidence based on consistency
        # Check if trend is consistent across periods
        changes = []
        for i in range(1, len(sorted_scores)):
            prev_score = sorted_scores[i - 1].overall_score
            curr_score = sorted_scores[i].overall_score
            if prev_score == 0:
                change = 100.0 if curr_score > 0 else 0.0
            else:
                change = ((curr_score - prev_score) / prev_score) * 100.0
            changes.append(change)

        # Confidence is based on how many periods agree with the overall trend
        if len(changes) == 0:
            confidence = 0.0
        else:
            if direction == "improving":
                agreeing = sum(1 for c in changes if c > 0)
            elif direction == "degrading":
                agreeing = sum(1 for c in changes if c < 0)
            else:
                agreeing = sum(1 for c in changes if abs(c) <= 1.0)

            confidence = agreeing / len(changes)

        return {
            "direction": direction,
            "rate_of_change": round(rate_of_change, 2),
            "confidence": round(confidence, 2),
            "periods_analyzed": len(sorted_scores),
            "overall_change": round(overall_change, 2),
        }

    def check_score_thresholds(
        self, score: DataQualityScore, previous_score: Optional[DataQualityScore] = None
    ) -> list[QualityScoreThresholdBreached]:
        """
        Check if score breaches configured thresholds and return events.

        Args:
            score: Current quality score
            previous_score: Optional previous score to determine status change

        Returns:
            List of QualityScoreThresholdBreached events (empty if no breaches)
        """
        from datetime import datetime

        events = []
        thresholds = self.config.thresholds

        # Determine previous status
        previous_status = None
        if previous_score:
            if previous_score.overall_score >= thresholds.healthy:
                previous_status = "healthy"
            elif previous_score.overall_score >= thresholds.warning:
                previous_status = "warning"
            else:
                previous_status = "critical"

        # Check if score crossed critical threshold
        # Critical is when score < warning threshold (since critical threshold is usually 0)
        if score.overall_score < thresholds.warning:
            # Determine if this is a critical breach (score < warning) or warning breach
            # If score is also below critical threshold, it's critical
            # Otherwise, if it crossed from healthy to below warning, it's a warning breach
            if previous_score and previous_score.overall_score >= thresholds.warning:
                # Crossed from healthy/warning to below warning
                if score.overall_score < thresholds.critical:
                    threshold_type = "critical"
                    threshold_value = thresholds.critical
                else:
                    threshold_type = "warning"
                    threshold_value = thresholds.warning

                events.append(
                    QualityScoreThresholdBreached(
                        event_type="QualityScoreThresholdBreached",
                        timestamp=datetime.utcnow(),
                        table=score.table_name,
                        schema=score.schema_name,
                        current_score=score.overall_score,
                        threshold_type=threshold_type,
                        threshold_value=threshold_value,
                        previous_status=previous_status,
                        explanation=(
                            f"Quality score {score.overall_score:.1f} "
                            f"fell below {threshold_type} threshold "
                            f"({threshold_value:.1f})"
                        ),
                        metadata={},
                    )
                )

        return events

    def check_score_degradation(
        self, current: DataQualityScore, previous: Optional[DataQualityScore]
    ) -> Optional[QualityScoreDegraded]:
        """
        Check if score has degraded significantly and return event.

        Args:
            current: Current quality score
            previous: Previous quality score (optional)

        Returns:
            QualityScoreDegraded event if degradation detected, None otherwise
        """
        from datetime import datetime

        if previous is None:
            return None

        # Calculate score change
        score_change = current.overall_score - previous.overall_score

        # Check if score dropped significantly (more than 5 points)
        if score_change < -5.0:
            thresholds = self.config.thresholds

            # Determine threshold type based on current score
            if current.overall_score < thresholds.warning:
                if current.overall_score < thresholds.critical:
                    threshold_type = "critical"
                else:
                    threshold_type = "warning"
            else:
                threshold_type = "warning"  # Still a warning even if above threshold

            return QualityScoreDegraded(
                event_type="QualityScoreDegraded",
                timestamp=datetime.utcnow(),
                table=current.table_name,
                schema=current.schema_name,
                current_score=current.overall_score,
                previous_score=previous.overall_score,
                score_change=score_change,
                threshold_type=threshold_type,
                explanation=(
                    f"Quality score degraded from "
                    f"{previous.overall_score:.1f} to "
                    f"{current.overall_score:.1f} "
                    f"(change: {score_change:.1f})"
                ),
                metadata={},
            )

        return None
